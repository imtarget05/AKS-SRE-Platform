"""Approval-gated execution of allowlisted recovery commands across domains.

Domain command registry maps (command_type, owner_service, scope_id) to a
DomainCommand.  The pilot ships three domains: OpsBridge FlashSale
(order_failure -> REPLAY_STUCK_OUTBOX), QuanLyKho (voucher_check ->
REPLAY_STUCK_VOUCHER), and AKS SRE Platform (incident ->
ACKNOWLEDGE_INCIDENT).  Each domain keeps its own HMAC key, approver roles,
executor roles, and target endpoint pattern.
"""

import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException

from adapters.ops_adapter import OpsBridgeReadAdapter
from adapters.quan_adapter import QuanLyKhoReadAdapter
from adapters.platform_adapter import PlatformIncidentAdapter
from core.storage import StorageManager
from schemas.action_intent import ActionIntent, ApproveActionRequest, ExecutionReceipt


@dataclass(frozen=True)
class DomainCommand:
    command_type: str
    owner_service: str
    scope_id: str
    target_endpoint_pattern: str   # "{entity_ref}" is substituted at runtime
    hmac_key_env: str
    approver_roles: frozenset
    executor_roles: frozenset
    case_type: str


DOMAIN_COMMANDS: dict[str, DomainCommand] = {
    "opsbridge": DomainCommand(
        command_type="REPLAY_STUCK_OUTBOX",
        owner_service="opsbridge-flashsale",
        scope_id="ops-cluster-01",
        target_endpoint_pattern="/internal/agent/outbox/{entity_ref}/requeue",
        hmac_key_env="OPSBRIDGE_AGENT_HMAC_KEY",
        approver_roles=frozenset({"SRELead", "SecurityOfficer"}),
        executor_roles=frozenset({"SRE", "SRELead"}),
        case_type="order_failure",
    ),
    "quanlykho": DomainCommand(
        command_type="REPLAY_STUCK_VOUCHER",
        owner_service="quanlykho",
        scope_id="*",
        target_endpoint_pattern="/internal/agent/voucher/{entity_ref}/replay",
        hmac_key_env="QUANLYKHO_AGENT_HMAC_KEY",
        approver_roles=frozenset({"SRELead", "SecurityOfficer", "Checker"}),
        executor_roles=frozenset({"SRE", "SRELead"}),
        case_type="voucher_check",
    ),
    "platform": DomainCommand(
        command_type="ACKNOWLEDGE_INCIDENT",
        owner_service="aks-sre-platform",
        scope_id="cluster-kind-01",
        target_endpoint_pattern="/internal/agent/incident/{entity_ref}/ack",
        hmac_key_env="PLATFORM_AGENT_HMAC_KEY",
        approver_roles=frozenset({"SRELead", "SecurityOfficer"}),
        executor_roles=frozenset({"SRE", "SRELead"}),
        case_type="incident",
    ),
}


def _lookup_domain(command_type: str, owner_service: str, scope_id: str) -> DomainCommand:
    for domain in DOMAIN_COMMANDS.values():
        if (domain.command_type == command_type
                and domain.owner_service == owner_service
                and (domain.scope_id == "*" or domain.scope_id == scope_id)):
            return domain
    raise HTTPException(
        400,
        f"Recovery command '{command_type}' for owner '{owner_service}' "
        f"at scope '{scope_id}' is not allowlisted",
    )


class ActionExecutor:
    """The owner database remains authoritative for both recovery and its audit."""

    def __init__(
        self,
        storage: Optional[StorageManager] = None,
        ops_adapter: Optional[OpsBridgeReadAdapter] = None,
        quan_adapter: Optional[QuanLyKhoReadAdapter] = None,
        platform_adapter: Optional[PlatformIncidentAdapter] = None,
    ):
        self.storage = storage or StorageManager()
        # Base URLs per domain, each from its own env var with a cluster-local
        # default.  The executor never mints owner JWTs; each domain authenticates
        # with its own dedicated HMAC command key.
        self.base_urls = {
            "opsbridge": (ops_adapter.base_url if ops_adapter else os.getenv(
                "FLASH_SALE_ORDER_API_URL", "http://order-api.flashsale.svc.cluster.local:80"
            )).rstrip("/"),
            "quanlykho": os.getenv(
                "QUANLYKHO_SERVICE_URL", "http://bankops-api.quanlykho.svc.cluster.local:8000"
            ).rstrip("/"),
            "platform": os.getenv(
                "PROMETHEUS_URL", "http://kps-kube-prometheus-stack-prometheus.monitoring.svc.cluster.local:9090"
            ).rstrip("/"),
        }
        self.timeouts = {
            "opsbridge": float(os.getenv("FLASH_SALE_HTTP_TIMEOUT", "5.0")),
            "quanlykho": float(os.getenv("QUANLYKHO_HTTP_TIMEOUT", "5.0")),
            "platform": float(os.getenv("PLATFORM_HTTP_TIMEOUT", "5.0")),
        }

    def create_intent(
        self,
        run_id: str,
        requester_id: str,
        command_type: str,
        owner_service: str,
        scope_id: str,
        entity_ref: str,
        idempotency_key: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> ActionIntent:
        domain = _lookup_domain(command_type, owner_service, scope_id)

        try:
            uuid.UUID(entity_ref)
        except ValueError as exc:
            raise HTTPException(400, "entity_ref must be a valid UUID") from exc
        if not 8 <= len(idempotency_key) <= 128:
            raise HTTPException(400, "Invalid idempotency key length")
        params = parameters or {}
        if set(params) != {"expected_version"}:
            raise HTTPException(400, "An exact expected_version is required")
        try:
            expected = datetime.fromisoformat(params["expected_version"])
            if expected.tzinfo is None:
                raise ValueError("timezone required")
        except (TypeError, ValueError) as exc:
            raise HTTPException(400, "Invalid expected_version") from exc
        expected = expected.astimezone(timezone.utc).isoformat()

        run = self.storage.get_run(run_id)
        if not run or run["user_id"] != requester_id or run["scope_id"] != scope_id:
            raise HTTPException(403, "Action must belong to the caller's scoped investigation")
        if run["case_type"] != domain.case_type:
            raise HTTPException(400, f"Action requires a {domain.case_type} investigation")
        evidence = self.storage.get_evidences_for_run(run_id)
        if not self._evidence_matches(evidence, domain, entity_ref, expected):
            raise HTTPException(
                409,
                f"Investigation has no current evidence for this exact {domain.owner_service} event",
            )

        existing = self.storage.get_intent_by_idempotency_key(idempotency_key)
        if existing:
            if (
                existing.run_id == run_id
                and existing.requested_by == requester_id
                and existing.entity_ref == entity_ref
                and existing.parameters == {"expected_version": expected}
            ):
                return existing
            raise HTTPException(409, "Idempotency key belongs to a different action")

        intent = ActionIntent(
            intent_id=f"intent-{uuid.uuid4().hex[:12]}",
            run_id=run_id,
            requested_by=requester_id,
            command_type=domain.command_type,
            owner_service=domain.owner_service,
            target_endpoint=domain.target_endpoint_pattern.format(entity_ref=entity_ref),
            scope_id=domain.scope_id,
            entity_ref=entity_ref,
            parameters={"expected_version": expected},
            idempotency_key=idempotency_key,
            risk_level="MEDIUM",
        )
        self.storage.save_intent(intent)
        return intent

    @staticmethod
    def _evidence_matches(
        evidence: List[Any], domain: DomainCommand, entity_ref: str, expected: str
    ) -> bool:
        expected_dt = datetime.fromisoformat(expected)
        for envelope in evidence:
            if (
                envelope.source_service != domain.owner_service
                or (domain.scope_id != "*" and envelope.scope_id != domain.scope_id)
                or envelope.is_expired()
                or not envelope.verify_integrity()
            ):
                continue
            facts = envelope.facts or {}
            # OpsBridge: evidence carries a "messages" list with messageId+deadLetteredAt
            for event in facts.get("messages", []):
                if not isinstance(event, dict):
                    continue
                try:
                    event_id = str(uuid.UUID(str(event.get("messageId", ""))))
                    event_version = datetime.fromisoformat(
                        str(event.get("deadLetteredAt"))
                    ).astimezone(timezone.utc)
                except (ValueError, TypeError):
                    continue
                if event_id == entity_ref and event_version == expected_dt:
                    return True
            # QuanLyKho / Platform: evidence carries entity_ref + record_version directly
            if facts.get("entity_ref") == entity_ref and str(facts.get("record_version", "")) == expected:
                return True
        return False

    def approve_intent(
        self,
        intent_id: str,
        approver_id: str,
        approver_role: str,
        approver_scopes: List[str],
        req: ApproveActionRequest,
    ) -> ActionIntent:
        intent = self.storage.get_intent(intent_id)
        if not intent:
            raise HTTPException(404, "Action intent not found")
        if intent.scope_id not in approver_scopes and "*" not in approver_scopes:
            raise HTTPException(403, "Approver scope does not cover action")
        domain = _lookup_domain(intent.command_type, intent.owner_service, intent.scope_id)
        if approver_role not in domain.approver_roles or approver_id == intent.requested_by:
            raise HTTPException(403, "Independent approval is required")
        if intent.is_expired():
            self.storage.update_intent_state(intent_id, "EXPIRED")
            raise HTTPException(409, "Action intent expired")
        if intent.state != "AWAITING_APPROVAL":
            raise HTTPException(409, "Action intent already decided")
        if req.intent_hash != intent.intent_hash or req.decision not in {"APPROVED", "REJECTED"}:
            raise HTTPException(400, "Decision or reviewed intent hash is invalid")
        if not req.reason.strip():
            raise HTTPException(400, "Approval reason is required")

        self.storage.record_action_approval(
            intent_id, req.decision, approver_id, approver_role, req.reason, intent.intent_hash
        )
        intent.state = "APPROVED" if req.decision == "APPROVED" else "REJECTED"
        self.storage.update_intent_state(intent_id, intent.state)
        return intent

    def execute_intent(
        self,
        intent_id: str,
        caller_id: str,
        caller_role: str,
        caller_scopes: List[str],
    ) -> ExecutionReceipt:
        intent = self.storage.get_intent(intent_id)
        if not intent:
            raise HTTPException(404, "Action intent not found")
        domain = _lookup_domain(intent.command_type, intent.owner_service, intent.scope_id)
        if caller_role not in domain.executor_roles or (
            intent.scope_id not in caller_scopes and "*" not in caller_scopes
        ):
            raise HTTPException(403, "Executor role or scope is not allowed")
        prior = self.storage.get_execution_receipt(intent_id)
        if prior:
            return prior
        if intent.is_expired():
            self.storage.update_intent_state(intent_id, "EXPIRED")
            raise HTTPException(409, "Action intent expired")
        approval = self.storage.get_action_approval(intent_id)
        if not approval or approval["decision"] != "APPROVED" or approval["intent_hash"] != intent.intent_hash:
            raise HTTPException(403, "Matching human approval is required")
        was_unknown = intent.state == "UNKNOWN"
        if not self.storage.claim_intent_execution(intent_id):
            raise HTTPException(409, "Action is not approved or is already executing")
        try:
            receipt = self._execute_by_domain(domain, intent, approval, caller_id, was_unknown)
            self.storage.save_execution_receipt(receipt)
            self.storage.update_intent_state(intent_id, "SUCCEEDED")
            return receipt
        except (httpx.RequestError, TimeoutError) as exc:
            # The owner may have committed before the response was lost. A retry
            # uses the same durable idempotency key and receives its owner receipt.
            self.storage.update_intent_state(intent_id, "UNKNOWN")
            raise HTTPException(503, "Owner outcome unknown; retry the same intent") from exc
        except HTTPException as exc:
            self.storage.update_intent_state(intent_id, "UNKNOWN" if exc.status_code >= 500 else "FAILED")
            raise
        except Exception as exc:
            self.storage.update_intent_state(intent_id, "UNKNOWN")
            raise HTTPException(503, "Owner outcome unknown; retry the same intent") from exc

    def _execute_by_domain(
        self,
        domain: DomainCommand,
        intent: ActionIntent,
        approval: Dict[str, Any],
        caller_id: str,
        was_unknown: bool,
    ) -> ExecutionReceipt:
        if domain.command_type == "REPLAY_STUCK_OUTBOX":
            return self._execute_requeue(intent, approval, caller_id, was_unknown)
        if domain.command_type == "REPLAY_STUCK_VOUCHER":
            return self._execute_voucher_replay(intent, approval, caller_id, was_unknown)
        if domain.command_type == "ACKNOWLEDGE_INCIDENT":
            return self._execute_incident_ack(intent, approval, caller_id, was_unknown)
        raise HTTPException(501, f"No execution handler for {domain.command_type}")

    def _execute_requeue(
        self, intent: ActionIntent, approval: Dict[str, Any], caller_id: str,
        was_unknown: bool,
    ) -> ExecutionReceipt:
        message_id = intent.entity_ref
        expected = datetime.fromisoformat(intent.parameters["expected_version"])
        body = json.dumps(
            {
                "intentId": intent.intent_id,
                "intentHash": intent.intent_hash,
                "idempotencyKey": intent.idempotency_key,
                "approvedBy": approval["approver_id"],
                "expectedDeadLetteredAt": expected.isoformat(),
            },
            separators=(",", ":"),
        ).encode("utf-8")
        with httpx.Client(timeout=self.timeouts["opsbridge"]) as client:
            before = self._owner_get(client, message_id, "opsbridge")
            if before.get("messageId", "").lower() != message_id.lower():
                raise HTTPException(502, "Owner returned the wrong event")
            observed_version = before.get("deadLetteredAt")
            if observed_version is None:
                if not was_unknown:
                    raise HTTPException(409, "Event is no longer dead-lettered")
            else:
                try:
                    observed = datetime.fromisoformat(observed_version).astimezone(timezone.utc)
                except (TypeError, ValueError) as exc:
                    raise HTTPException(502, "Owner returned an invalid event version") from exc
                if observed != expected:
                    raise HTTPException(409, "Event version changed after approval")
            path = intent.target_endpoint
            response = client.post(
                f"{self.base_urls['opsbridge']}{path}",
                headers={
                    **self._signed_headers("POST", path, body, "opsbridge"),
                    "Content-Type": "application/json",
                },
                content=body,
            )
            if response.status_code == 409:
                raise HTTPException(409, "Owner event state or idempotency key changed")
            response.raise_for_status()
            owner_result = response.json()
            if (owner_result.get("status") not in {"requeued", "already_applied"}
                    or owner_result.get("idempotencyKey") != intent.idempotency_key
                    or owner_result.get("messageId", "").lower() != message_id.lower()):
                raise HTTPException(502, "Owner did not confirm a scoped recovery")
            after = self._owner_get(client, message_id, "opsbridge")
            if after.get("messageId", "").lower() != message_id.lower() or after.get("deadLetteredAt") is not None:
                raise HTTPException(503, "Owner post-state could not be verified")

        return ExecutionReceipt(
            receipt_id=f"rcpt-{uuid.uuid4().hex[:12]}",
            intent_id=intent.intent_id,
            owner_command_id=owner_result["idempotencyKey"],
            idempotency_key=intent.idempotency_key,
            executed_by=caller_id,
            approved_by=approval["approver_id"],
            owner_status_code=response.status_code,
            before_state=before,
            after_state=after,
            verified=True,
            audit_ref=f"opsbridge-outbox-recovery:{intent.idempotency_key}",
            result_summary=f"Recovered only outbox event {message_id}",
        )

    def _execute_voucher_replay(
        self, intent: ActionIntent, approval: Dict[str, Any], caller_id: str,
        was_unknown: bool,
    ) -> ExecutionReceipt:
        entity_ref = intent.entity_ref
        expected = datetime.fromisoformat(intent.parameters["expected_version"])
        body = json.dumps(
            {
                "intentId": intent.intent_id,
                "intentHash": intent.intent_hash,
                "idempotencyKey": intent.idempotency_key,
                "approvedBy": approval["approver_id"],
                "expectedVersion": expected.isoformat(),
            },
            separators=(",", ":"),
        ).encode("utf-8")
        with httpx.Client(timeout=self.timeouts["quanlykho"]) as client:
            before = self._owner_get(client, entity_ref, "quanlykho")
            if before.get("entity_ref", "").lower() != entity_ref.lower():
                raise HTTPException(502, "Owner returned the wrong voucher")
            path = intent.target_endpoint
            response = client.post(
                f"{self.base_urls['quanlykho']}{path}",
                headers={
                    **self._signed_headers("POST", path, body, "quanlykho"),
                    "Content-Type": "application/json",
                },
                content=body,
            )
            if response.status_code == 409:
                raise HTTPException(409, "Owner voucher state or idempotency key changed")
            response.raise_for_status()
            owner_result = response.json()
            if (
                owner_result.get("status") not in {"replayed", "already_applied"}
                or owner_result.get("idempotencyKey") != intent.idempotency_key
            ):
                raise HTTPException(502, "Owner did not confirm a scoped voucher replay")

        return ExecutionReceipt(
            receipt_id=f"rcpt-{uuid.uuid4().hex[:12]}",
            intent_id=intent.intent_id,
            owner_command_id=owner_result.get("idempotencyKey", intent.idempotency_key),
            idempotency_key=intent.idempotency_key,
            executed_by=caller_id,
            approved_by=approval["approver_id"],
            owner_status_code=response.status_code,
            before_state=before,
            after_state=owner_result,
            verified=True,
            audit_ref=f"quanlykho-voucher-replay:{intent.idempotency_key}",
            result_summary=f"Replayed only voucher {entity_ref}",
        )

    def _execute_incident_ack(
        self, intent: ActionIntent, approval: Dict[str, Any], caller_id: str,
        was_unknown: bool,
    ) -> ExecutionReceipt:
        alert_fp = intent.entity_ref
        expected = datetime.fromisoformat(intent.parameters["expected_version"])
        body = json.dumps(
            {
                "intentId": intent.intent_id,
                "intentHash": intent.intent_hash,
                "idempotencyKey": intent.idempotency_key,
                "approvedBy": approval["approver_id"],
                "expectedVersion": expected.isoformat(),
            },
            separators=(",", ":"),
        ).encode("utf-8")
        with httpx.Client(timeout=self.timeouts["platform"]) as client:
            path = intent.target_endpoint
            response = client.post(
                f"{self.base_urls['platform']}{path}",
                headers={
                    **self._signed_headers("POST", path, body, "platform"),
                    "Content-Type": "application/json",
                },
                content=body,
            )
            if response.status_code == 409:
                raise HTTPException(409, "Owner incident state or idempotency key changed")
            response.raise_for_status()
            owner_result = response.json()
            if (
                owner_result.get("status") not in {"acknowledged", "already_applied"}
                or owner_result.get("idempotencyKey") != intent.idempotency_key
            ):
                raise HTTPException(502, "Owner did not confirm a scoped incident ack")

        return ExecutionReceipt(
            receipt_id=f"rcpt-{uuid.uuid4().hex[:12]}",
            intent_id=intent.intent_id,
            owner_command_id=owner_result.get("idempotencyKey", intent.idempotency_key),
            idempotency_key=intent.idempotency_key,
            executed_by=caller_id,
            approved_by=approval["approver_id"],
            owner_status_code=response.status_code,
            before_state={"alert_fingerprint": alert_fp, "expected_version": expected.isoformat()},
            after_state=owner_result,
            verified=True,
            audit_ref=f"aks-platform-incident-ack:{intent.idempotency_key}",
            result_summary=f"Acknowledged only incident {alert_fp}",
        )

    @staticmethod
    def _signed_headers(method: str, path: str, body: bytes, domain_key: str = "opsbridge") -> dict[str, str]:
        env_var = DOMAIN_COMMANDS[domain_key].hmac_key_env
        key = os.getenv(env_var, "")
        if len(key.encode("utf-8")) < 32:
            raise HTTPException(503, f"Agent recovery credential for {domain_key} is not configured")
        timestamp = str(int(time.time()))
        body_hash = hashlib.sha256(body).hexdigest()
        payload = f"{method}\n{path}\n{timestamp}\n{body_hash}".encode("utf-8")
        signature = hmac.new(key.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        return {"X-Agent-Timestamp": timestamp, "X-Agent-Signature": signature}

    def _owner_get(
        self, client: httpx.Client, entity_ref: str, domain_key: str = "opsbridge"
    ) -> dict[str, Any]:
        if domain_key == "opsbridge":
            path = f"/internal/agent/outbox/{entity_ref}"
        elif domain_key == "quanlykho":
            path = f"/internal/agent/voucher/{entity_ref}"
        else:
            path = f"/internal/agent/incident/{entity_ref}"
        response = client.get(
            f"{self.base_urls[domain_key]}{path}",
            headers=self._signed_headers("GET", path, b"", domain_key),
        )
        response.raise_for_status()
        return response.json()

"""Approval-gated execution of one allowlisted OpsBridge recovery command."""

import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException

from adapters.ops_adapter import OpsBridgeReadAdapter
from core.storage import StorageManager
from schemas.action_intent import ActionIntent, ApproveActionRequest, ExecutionReceipt


COMMAND = "REPLAY_STUCK_OUTBOX"
OWNER = "opsbridge-flashsale"
SCOPE = "ops-cluster-01"
APPROVER_ROLES = {"SRELead", "SecurityOfficer"}
EXECUTOR_ROLES = {"SRE", "SRELead"}


class ActionExecutor:
    """The owner database remains authoritative for both recovery and its audit."""

    def __init__(
        self,
        storage: Optional[StorageManager] = None,
        ops_adapter: Optional[OpsBridgeReadAdapter] = None,
    ):
        self.storage = storage or StorageManager()
        # The executor does not mint an owner JWT. The owner authenticates a
        # dedicated HMAC command key, kept separate from all user signing keys.
        self.base_url = (ops_adapter.base_url if ops_adapter else os.getenv(
            "FLASH_SALE_ORDER_API_URL", "http://order-api.flashsale.svc.cluster.local:80"
        )).rstrip("/")
        self.timeout = ops_adapter.timeout if ops_adapter else float(os.getenv("FLASH_SALE_HTTP_TIMEOUT", "5.0"))

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
        if command_type != COMMAND or owner_service != OWNER or scope_id != SCOPE:
            raise HTTPException(400, "Recovery command, owner, or scope is not allowlisted")
        try:
            message_id = str(uuid.UUID(entity_ref))
        except ValueError as exc:
            raise HTTPException(400, "entity_ref must be one outbox message UUID") from exc
        if not 8 <= len(idempotency_key) <= 128:
            raise HTTPException(400, "Invalid idempotency key length")
        params = parameters or {}
        if set(params) != {"expected_dead_lettered_at"}:
            raise HTTPException(400, "An exact dead-letter version is required")
        try:
            expected = datetime.fromisoformat(params["expected_dead_lettered_at"])
            if expected.tzinfo is None:
                raise ValueError("timezone required")
        except (TypeError, ValueError) as exc:
            raise HTTPException(400, "Invalid dead-letter version") from exc
        expected = expected.astimezone(timezone.utc).isoformat()

        run = self.storage.get_run(run_id)
        if not run or run["user_id"] != requester_id or run["scope_id"] != scope_id:
            raise HTTPException(403, "Action must belong to the caller's scoped investigation")
        if run["case_type"] != "order_failure":
            raise HTTPException(400, "Recovery requires an order failure investigation")
        evidence = self.storage.get_evidences_for_run(run_id)
        def matches_event(envelope):
            if (envelope.source_service != OWNER or envelope.scope_id != scope_id
                    or envelope.is_expired() or not envelope.verify_integrity()):
                return False
            for event in envelope.facts.get("messages", []):
                if not isinstance(event, dict):
                    continue
                try:
                    event_id = str(uuid.UUID(str(event.get("messageId", ""))))
                    event_version = datetime.fromisoformat(str(event.get("deadLetteredAt"))).astimezone(timezone.utc)
                except (ValueError, TypeError):
                    continue
                if event_id == message_id and event_version == datetime.fromisoformat(expected):
                    return True
            return False
        if not any(matches_event(item) for item in evidence):
            raise HTTPException(409, "Investigation has no current evidence for this exact dead-lettered event")

        existing = self.storage.get_intent_by_idempotency_key(idempotency_key)
        if existing:
            if (
                existing.run_id == run_id
                and existing.requested_by == requester_id
                and existing.entity_ref == message_id
                and existing.parameters == {"expected_dead_lettered_at": expected}
            ):
                return existing
            raise HTTPException(409, "Idempotency key belongs to a different action")

        intent = ActionIntent(
            intent_id=f"intent-{uuid.uuid4().hex[:12]}",
            run_id=run_id,
            requested_by=requester_id,
            command_type=COMMAND,
            owner_service=OWNER,
            target_endpoint=f"/internal/agent/outbox/{message_id}/requeue",
            scope_id=scope_id,
            entity_ref=message_id,
            parameters={"expected_dead_lettered_at": expected},
            idempotency_key=idempotency_key,
            risk_level="MEDIUM",
        )
        self.storage.save_intent(intent)
        return intent

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
        if approver_role not in APPROVER_ROLES or approver_id == intent.requested_by:
            raise HTTPException(403, "Independent SRE approval is required")
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
        if caller_role not in EXECUTOR_ROLES or (
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
            receipt = self._execute_requeue(intent, approval, caller_id, was_unknown)
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

    @staticmethod
    def _signed_headers(method: str, path: str, body: bytes) -> dict[str, str]:
        key = os.getenv("OPSBRIDGE_AGENT_HMAC_KEY", "")
        if len(key.encode("utf-8")) < 32:
            raise HTTPException(503, "Agent recovery credential is not configured")
        timestamp = str(int(time.time()))
        body_hash = hashlib.sha256(body).hexdigest()
        payload = f"{method}\n{path}\n{timestamp}\n{body_hash}".encode("utf-8")
        signature = hmac.new(key.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        return {"X-Agent-Timestamp": timestamp, "X-Agent-Signature": signature}

    def _owner_get(self, client: httpx.Client, message_id: str) -> dict[str, Any]:
        path = f"/internal/agent/outbox/{message_id}"
        response = client.get(
            f"{self.base_url}{path}",
            headers=self._signed_headers("GET", path, b""),
        )
        response.raise_for_status()
        return response.json()

    def _execute_requeue(
        self, intent: ActionIntent, approval: Dict[str, Any], caller_id: str,
        was_unknown: bool,
    ) -> ExecutionReceipt:
        message_id = intent.entity_ref
        expected = datetime.fromisoformat(intent.parameters["expected_dead_lettered_at"])
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
        with httpx.Client(timeout=self.timeout) as client:
            before = self._owner_get(client, message_id)
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
                f"{self.base_url}{path}",
                headers={
                    **self._signed_headers("POST", path, body),
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
            after = self._owner_get(client, message_id)
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

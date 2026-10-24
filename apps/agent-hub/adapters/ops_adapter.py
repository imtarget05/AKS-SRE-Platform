import os
import hashlib
import hmac
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, List
import httpx
from schemas.evidence_envelope import EvidenceEnvelope


class OpsBridgeReadAdapter:
    """
    Read-only adapter for OpsBridge FlashSale orders, inventory, and outbox.
    Invariants:
    - Zero write operations (never requeues, never cancels order).
    - Returns standardized EvidenceEnvelope grounded in real service endpoints.
    - Endpoints:
        GET /api/outbox/stuck
        GET /api/outbox/pending
        GET /api/orders/{idempotencyKey}
        GET /api/saga/{idempotencyKey}
    """
    def __init__(
        self,
        base_url: Optional[str] = None,
        read_token: Optional[str] = None
    ):
        self.base_url = base_url or os.getenv("FLASH_SALE_ORDER_API_URL", "http://order-api.flashsale.svc.cluster.local:80")
        # A token issued by the owner is supplied through the secret store.
        # Agent Hub must never possess the owner's JWT signing key.
        self.read_token = read_token or os.getenv("FLASH_SALE_READ_BEARER_TOKEN")
        self.timeout = float(os.getenv("FLASH_SALE_HTTP_TIMEOUT", "5.0"))

    def _read_headers(self) -> Dict[str, str]:
        if not self.read_token:
            raise PermissionError("OpsBridge read credential is not configured")
        return {"Authorization": f"Bearer {self.read_token}"}

    @staticmethod
    def _owner_headers(path: str) -> Dict[str, str]:
        key = os.getenv("OPSBRIDGE_AGENT_HMAC_KEY", "")
        if len(key.encode("utf-8")) < 32:
            raise PermissionError("OpsBridge agent credential is not configured")
        timestamp = str(int(time.time()))
        body_hash = hashlib.sha256(b"").hexdigest()
        payload = f"GET\n{path}\n{timestamp}\n{body_hash}".encode("utf-8")
        signature = hmac.new(key.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        return {"X-Agent-Timestamp": timestamp, "X-Agent-Signature": signature}

    def fetch_order_timeline(
        self,
        order_id: str,
        scope_id: str = "ops-cluster-01",
        synthetic_payload: Optional[Dict[str, Any]] = None
    ) -> EvidenceEnvelope:
        if scope_id != "ops-cluster-01":
            raise PermissionError("Cross-scope OpsBridge read denied")
        endpoint_url = f"{self.base_url}/api/orders/{order_id}"
        saga_url = f"{self.base_url}/api/saga/{order_id}"

        if synthetic_payload is not None:
            facts = synthetic_payload
            source_sha = "b507464"
            record_version = facts.get("record_version", 1)
        else:
            try:
                headers = self._read_headers()
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(endpoint_url, headers=headers)
                    if resp.status_code == 404:
                        facts = {
                            "order_id": order_id,
                            "order_status": "NOT_FOUND",
                            "record_version": 1
                        }
                    else:
                        resp.raise_for_status()
                        order_data = resp.json()

                        # Try reading saga details
                        saga_data = None
                        try:
                            resp_saga = client.get(saga_url, headers=headers)
                            if resp_saga.status_code == 200:
                                saga_data = resp_saga.json()
                        except Exception:
                            pass

                        facts = {
                            "order_id": order_id,
                            "order_status": order_data.get("status", "UNKNOWN"),
                            "product_id": order_data.get("productId"),
                            "quantity": order_data.get("quantity"),
                            "saga": saga_data,
                            "record_version": 1
                        }
                    source_sha = "b507464"
                    record_version = 1
            except httpx.HTTPError as exc:
                raise ConnectionError(f"Failed to fetch order facts from Order API at {endpoint_url}: {exc}")

        return EvidenceEnvelope(
            case_type="order_failure",
            entity_ref=order_id,
            source_service="opsbridge-flashsale",
            source_sha=source_sha,
            scope_id=scope_id,
            record_version=record_version,
            observed_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            facts=facts,
            source_refs=[endpoint_url],
            classification="INTERNAL_CONFIDENTIAL",
            redaction_level="NONE"
        )

    def fetch_stuck_outbox(
        self,
        scope_id: str = "ops-cluster-01",
        synthetic_payload: Optional[Dict[str, Any]] = None
    ) -> EvidenceEnvelope:
        if scope_id != "ops-cluster-01":
            raise PermissionError("Cross-scope OpsBridge read denied")
        stuck_path = "/internal/agent/outbox/stuck"
        pending_path = "/internal/agent/outbox/pending"
        endpoint_url = f"{self.base_url}{stuck_path}"
        pending_url = f"{self.base_url}{pending_path}"

        if synthetic_payload is not None:
            facts = synthetic_payload
            source_sha = "b507464"
            record_version = facts.get("record_version", 1)
        else:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp_stuck = client.get(endpoint_url, headers=self._owner_headers(stuck_path))
                    resp_stuck.raise_for_status()
                    stuck_data = resp_stuck.json()

                    resp_pending = client.get(pending_url, headers=self._owner_headers(pending_path))
                    resp_pending.raise_for_status()
                    pending_data = resp_pending.json()

                    stuck_count = stuck_data.get("count", 0)
                    pending_count = pending_data.get("count", 0)

                    if stuck_count > 0:
                        facts = {
                            "outbox_status": "PENDING",
                            "stuck_count": stuck_count,
                            "dead_lettered": stuck_data.get("deadLettered", 0),
                            "backing_off": stuck_data.get("backingOff", 0),
                            "record_version": 0,
                            "messages": stuck_data.get("messages", [])
                        }
                    else:
                        facts = {
                            "outbox_status": "HEALTHY",
                            "stuck_count": 0,
                            "pending_count": pending_count,
                            "record_version": 0
                        }
                    source_sha = resp_stuck.headers.get("X-Service-SHA", "UNAVAILABLE")
                    record_version = 0
            except httpx.HTTPError as exc:
                raise ConnectionError(f"Failed to fetch outbox facts from Order API at {endpoint_url}: {exc}")

        return EvidenceEnvelope(
            case_type="order_failure",
            entity_ref="outbox-stuck-events",
            source_service="opsbridge-flashsale",
            source_sha=source_sha,
            scope_id=scope_id,
            record_version=record_version,
            observed_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            facts=facts,
            source_refs=[endpoint_url, pending_url],
            classification="INTERNAL_CONFIDENTIAL",
            redaction_level="NONE"
        )

import os
import json
import time
import base64
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
import httpx
from schemas.evidence_envelope import EvidenceEnvelope


class QuanLyKhoReadAdapter:
    """
    Read-only adapter for QuanLyKho inventory vouchers, stocktake, and FEFO.
    Invariants:
    - Strictly scoped to caller branch_id.
    - Zero write operations (never approves, never posts adjustments).
    - Returns standardized EvidenceEnvelope.
    - Advisory assessment via POST /api/v1/ai/assess-request.
    """
    def __init__(
        self,
        base_url: Optional[str] = None,
        signing_key: Optional[str] = None
    ):
        self.base_url = base_url or os.getenv("QUANLYKHO_SERVICE_URL", "http://bankops-api.quanlykho.svc.cluster.local:8000")
        self.signing_key = signing_key or os.getenv("QUANLYKHO_JWT_KEY", "k8s-platform-bankops-jwt-signing-key-production-grade-at-least-32-bytes-long")
        self.timeout = float(os.getenv("QUANLYKHO_HTTP_TIMEOUT", "5.0"))

    def _b64url(self, data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    def _generate_internal_token(self, user_id: Optional[str] = None) -> str:
        header = self._b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode("utf-8"))
        now = int(time.time())
        payload = self._b64url(json.dumps({
            "sub": user_id or "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "type": "access",
            "iat": now,
            "exp": now + 3600
        }).encode("utf-8"))
        sig = self._b64url(hmac.new(self.signing_key.encode("utf-8"), f"{header}.{payload}".encode("utf-8"), hashlib.sha256).digest())
        return f"{header}.{payload}.{sig}"

    def fetch_canonical_voucher(
        self,
        voucher_id: str,
        caller_branch_scope: str,
        target_branch_id: Optional[str] = None,
        synthetic_payload: Optional[Dict[str, Any]] = None,
        auth_token: Optional[str] = None
    ) -> EvidenceEnvelope:
        target_branch = target_branch_id or caller_branch_scope

        # Invariant: Cross-branch access denied at adapter level
        if caller_branch_scope != "*" and target_branch != "*" and caller_branch_scope != target_branch:
            raise PermissionError(
                f"Cross-branch access denied: Caller is scoped to '{caller_branch_scope}' but requested '{target_branch}'"
            )

        endpoint_url = f"{self.base_url}/api/v1/ai/assess-request"

        if synthetic_payload is not None:
            facts = synthetic_payload
            source_sha = "1bb494a"
            record_version = facts.get("record_version", 1)
        else:
            try:
                token = auth_token or self._generate_internal_token()
                headers = {"Authorization": f"Bearer {token}"}
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(
                        endpoint_url,
                        json={"request_id": voucher_id, "kind": "inventory"},
                        headers=headers
                    )
                    if resp.status_code == 404:
                        error_detail = ""
                        try:
                            error_detail = resp.json().get("error", {}).get("message", "")
                        except Exception:
                            error_detail = resp.text
                        if "phạm vi" in error_detail or "cấp quyền" in error_detail:
                            raise PermissionError(f"Cross-branch access denied: {error_detail}")
                        facts = {
                            "voucher_id": voucher_id,
                            "status": "NOT_FOUND",
                            "record_version": 1
                        }
                    else:
                        resp.raise_for_status()
                        raw_data = resp.json()
                        facts = {
                            "voucher_id": voucher_id,
                            "status": "FOUND",
                            "risk_level": raw_data.get("risk_level"),
                            "risk_score": raw_data.get("risk_score"),
                            "summary": raw_data.get("summary"),
                            "flagged_rules": raw_data.get("flagged_rules", []),
                            "recommendations": raw_data.get("recommendations", []),
                            "canonical_bound": raw_data.get("canonical_bound", True),
                            "canonical_version": raw_data.get("request_version", 1),
                            "record_version": raw_data.get("request_version", 1),
                            "assessed_by": raw_data.get("assessed_by"),
                            "fefo_violation": False
                        }
                    source_sha = "1bb494a"
                    record_version = facts.get("record_version", 1)
            except httpx.HTTPError as exc:
                raise ConnectionError(f"Failed to fetch canonical facts from QuanLyKho at {endpoint_url}: {exc}")

        return EvidenceEnvelope(
            case_type="voucher_check",
            entity_ref=voucher_id,
            source_service="quanlykho",
            source_sha=source_sha,
            scope_id=target_branch,
            record_version=record_version,
            observed_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            facts=facts,
            source_refs=[endpoint_url],
            classification="INTERNAL_CONFIDENTIAL",
            redaction_level="NONE"
        )

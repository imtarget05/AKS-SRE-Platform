import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, List
import httpx
from schemas.evidence_envelope import EvidenceEnvelope


class RetailReadAdapter:
    """
    Read-only adapter for Retail Finance reconciliation and settled transactions.
    Invariants:
    - Strictly scoped to caller_outlet_scope.
    - Real HTTP GET requests with authentication (ROLE_OPS or POS_STAFF) to Retail service.
    - Scoped feed endpoint: GET /api/v1/transactions/settled-scoped?outletCode={code}&from={from}&to={to}&limit={limit}&page={page}
    - Auto-paginated retrieval across all transaction windows.
    - Zero write operations (never posts to ledger).
    """
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        self.base_url = base_url or "http://bankops-api.quanlykho.svc.cluster.local:8080"
        self.token = token or os.getenv("RETAIL_API_TOKEN")
        self.username = os.getenv("RETAIL_SERVICE_USER", "ops")
        self.password = os.getenv("RETAIL_SERVICE_PASSWORD", "ChangeMe123!")
        self.timeout = float(os.getenv("RETAIL_HTTP_TIMEOUT", "5.0"))

    def _get_token(self, client: httpx.Client) -> str:
        if self.token:
            return self.token
        login_url = f"{self.base_url}/api/v1/auth/login"
        resp = client.post(
            login_url,
            json={"username": self.username, "password": self.password}
        )
        resp.raise_for_status()
        data = resp.json()
        self.token = data.get("accessToken") or data.get("token")
        return self.token

    def _as_instant(self, dt: datetime) -> str:
        """Render a datetime as ISO-8601 Instant ending with Z (e.g. 2026-10-24T00:00:00Z)."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def fetch_discrepancy_evidence(
        self,
        batch_id: str,
        caller_outlet_scope: str,
        target_outlet_id: Optional[str] = None,
        synthetic_payload: Optional[Dict[str, Any]] = None,
        window_start: Optional[datetime] = None,
        window_end: Optional[datetime] = None,
        expected_tx_refs: Optional[List[str]] = None,
        expected_amounts: Optional[Dict[str, float]] = None
    ) -> EvidenceEnvelope:
        target_outlet = target_outlet_id or caller_outlet_scope

        # Invariant 1: Caller outlet scope check
        if caller_outlet_scope != "*" and caller_outlet_scope != target_outlet:
            raise PermissionError(
                f"Cross-scope access denied: Caller is authorized only for outlet '{caller_outlet_scope}', attempted access to '{target_outlet}'"
            )

        now = datetime.now(timezone.utc)
        start_time = window_start or (now - timedelta(days=1))
        end_time = window_end or now

        if target_outlet == "*":
            endpoint_url = f"{self.base_url}/api/v1/transactions/settled"
            use_scoped = False
        else:
            endpoint_url = f"{self.base_url}/api/v1/transactions/settled-scoped"
            use_scoped = True

        # If synthetic_payload is provided in test mode
        if synthetic_payload is not None:
            facts = synthetic_payload
            source_sha = "433447f"
            record_version = facts.get("record_version", 1)
        else:
            # Real HTTP GET to canonical Retail service with full auto-pagination
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    auth_token = self._get_token(client)
                    headers = {
                        "Authorization": f"Bearer {auth_token}"
                    }
                    all_txns = []
                    page = 0
                    limit = 200
                    source_sha = "433447f"
                    record_version = 1

                    while True:
                        params = {
                            "from": self._as_instant(start_time),
                            "to": self._as_instant(end_time),
                            "limit": limit,
                            "page": page
                        }
                        if use_scoped:
                            params["outletCode"] = target_outlet

                        resp = client.get(endpoint_url, params=params, headers=headers)
                        if resp.status_code == 403:
                            raise PermissionError(f"Retail service denied access for role or outlet '{caller_outlet_scope}'")
                        resp.raise_for_status()
                        page_data = resp.json()

                        if "X-Service-SHA" in resp.headers:
                            source_sha = resp.headers["X-Service-SHA"]
                        if "X-Record-Version" in resp.headers:
                            record_version = int(resp.headers["X-Record-Version"])

                        if not isinstance(page_data, list) or len(page_data) == 0:
                            break
                        all_txns.extend(page_data)
                        if len(page_data) < limit:
                            break
                        page += 1
                        if page > 50:  # Boundary safety
                            break

                    if caller_outlet_scope != "*":
                        scoped_txns = [t for t in all_txns if t.get("outletCode") == caller_outlet_scope]
                    else:
                        scoped_txns = all_txns

                    settled_count = len(scoped_txns)
                    discrepancy_type = "NONE"
                    diff_amount = 0.0

                    # Reconcile against expected partner records if provided
                    if expected_tx_refs:
                        settled_refs = {t.get("txnRef") for t in scoped_txns}
                        missing_refs = [r for r in expected_tx_refs if r not in settled_refs]
                        if missing_refs:
                            discrepancy_type = "MISSING_LEDGER"
                        elif expected_amounts:
                            for t in scoped_txns:
                                ref = t.get("txnRef")
                                if ref in expected_amounts:
                                    actual_amt = float(t.get("amount", 0.0))
                                    exp_amt = float(expected_amounts[ref])
                                    if abs(actual_amt - exp_amt) > 0.01:
                                        discrepancy_type = "AMOUNT_MISMATCH"
                                        diff_amount = abs(actual_amt - exp_amt)
                                        break

                    facts = {
                        "batch_id": batch_id,
                        "outlet_id": caller_outlet_scope,
                        "settled_count": settled_count,
                        "discrepancy_type": discrepancy_type,
                        "diff_amount": diff_amount,
                        "transactions": scoped_txns
                    }
            except httpx.HTTPError as exc:
                raise ConnectionError(f"Failed to fetch canonical facts from Retail Finance at {endpoint_url}: {exc}")

        return EvidenceEnvelope(
            case_type="recon",
            entity_ref=batch_id,
            source_service="retail-finance",
            source_sha=source_sha,
            scope_id=caller_outlet_scope,
            record_version=record_version,
            observed_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            facts=facts,
            source_refs=[endpoint_url],
            classification="INTERNAL_CONFIDENTIAL",
            redaction_level="PARTIAL"
        )

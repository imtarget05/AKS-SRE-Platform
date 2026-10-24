import os
import sys
import pytest
from datetime import datetime, timezone, timedelta
import httpx

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from core.storage import StorageManager
from adapters.retail_adapter import RetailReadAdapter
from adapters.ops_adapter import OpsBridgeReadAdapter
from adapters.quan_adapter import QuanLyKhoReadAdapter
from adapters.platform_adapter import PlatformIncidentAdapter
from schemas.evidence_envelope import EvidenceEnvelope


def test_retail_adapter_scope_isolation():
    adapter = RetailReadAdapter()

    # Valid query within authorized scope with synthetic payload
    ev = adapter.fetch_discrepancy_evidence(
        batch_id="b-101",
        caller_outlet_scope="outlet-hn-01",
        synthetic_payload={"settled_count": 1, "record_version": 2}
    )
    assert ev.scope_id == "outlet-hn-01"
    assert ev.record_version == 2
    assert ev.verify_integrity() is True

    # Cross-scope access attempt must raise PermissionError
    with pytest.raises(PermissionError) as exc_info:
        adapter.fetch_discrepancy_evidence(
            batch_id="b-101",
            caller_outlet_scope="outlet-hn-01",
            target_outlet_id="outlet-sg-02"
        )
    assert "Cross-scope access denied" in str(exc_info.value)


def test_retail_adapter_canonical_contract_and_scoping(monkeypatch):
    """
    Test real HTTP GET interaction against Java core canonical contract:
    1. Endpoint: GET /api/v1/transactions/settled
    2. Parameters: from, to, limit, page
    3. Auth: Authorization: Bearer <token>
    4. Isolation: Only transactions matching caller_outlet_scope are returned.
    5. Empty feed is clean (discrepancy_type == 'NONE'), not false-positive MISSING_LEDGER.
    """
    captured_requests = []

    def mock_handler(request: httpx.Request):
        captured_requests.append(request)
        auth = request.headers.get("Authorization")
        if not auth or "Bearer" not in auth:
            return httpx.Response(401, json={"detail": "Unauthorized"})

        # Verify Java canonical query parameters
        assert "from" in request.url.params
        assert "to" in request.url.params
        assert "limit" in request.url.params
        assert "page" in request.url.params

        if "forbidden-token" in auth:
            return httpx.Response(403, json={"detail": "Forbidden: Requires ROLE_OPS"})

        # Multi-outlet response from core ledger feed
        return httpx.Response(
            200,
            headers={"X-Service-SHA": "433447f88", "X-Record-Version": "5"},
            json=[
                {"txnRef": "TX-HN-1", "outletCode": "outlet-hn-01", "amount": 100000.0, "status": "SETTLED"},
                {"txnRef": "TX-SG-1", "outletCode": "outlet-sg-02", "amount": 250000.0, "status": "SETTLED"},
                {"txnRef": "TX-HN-2", "outletCode": "outlet-hn-01", "amount": 50000.0, "status": "SETTLED"}
            ]
        )

    transport = httpx.MockTransport(mock_handler)
    real_client_cls = httpx.Client

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", client_factory)

    adapter = RetailReadAdapter(base_url="http://retail-service.local:8080", token="valid-ops-token")

    # 1. Scoped read for outlet-hn-01: must filter out outlet-sg-02!
    ev = adapter.fetch_discrepancy_evidence(
        batch_id="b-101",
        caller_outlet_scope="outlet-hn-01"
    )
    assert ev.source_sha == "433447f88"
    assert ev.record_version == 5
    assert ev.facts["settled_count"] == 2
    assert all(t["outletCode"] == "outlet-hn-01" for t in ev.facts["transactions"])
    assert ev.facts["discrepancy_type"] == "NONE"  # No expected partner records, so clean!
    assert ev.verify_integrity() is True

    # 2. Reconcile with expected partner records: missing transaction detected
    ev_recon = adapter.fetch_discrepancy_evidence(
        batch_id="b-102",
        caller_outlet_scope="outlet-hn-01",
        expected_tx_refs=["TX-HN-1", "TX-HN-MISSING"]
    )
    assert ev_recon.facts["discrepancy_type"] == "MISSING_LEDGER"

    # 3. Forbidden role response (403)
    adapter_forbidden = RetailReadAdapter(base_url="http://retail-service.local:8080", token="forbidden-token")
    with pytest.raises(PermissionError) as exc_info:
        adapter_forbidden.fetch_discrepancy_evidence(
            batch_id="b-103",
            caller_outlet_scope="outlet-hn-01"
        )
    assert "Retail service denied access" in str(exc_info.value)


def test_ops_adapter_real_http_calls_and_evidence(monkeypatch):
    """
    Test real HTTP communication against Order.Api canonical endpoints:
    1. GET /api/outbox/stuck and /api/outbox/pending
    2. GET /api/orders/{id}
    """
    monkeypatch.setenv("OPSBRIDGE_AGENT_HMAC_KEY", "test-only-agent-recovery-hmac-key-at-least-32-bytes")
    def mock_handler(request: httpx.Request):
        auth = request.headers.get("Authorization")
        if request.url.path.startswith("/internal/agent/outbox"):
            assert request.headers.get("X-Agent-Signature")
        else:
            assert auth and "Bearer" in auth

        path = request.url.path
        if path == "/internal/agent/outbox/stuck":
            return httpx.Response(200, json={
                "count": 2,
                "deadLettered": 1,
                "backingOff": 1,
                "messages": [{"messageId": "msg-01", "eventType": "OrderPlacedEvent"}]
            })
        elif path == "/internal/agent/outbox/pending":
            return httpx.Response(200, json={
                "count": 1,
                "stuckCount": 2,
                "messages": [{"messageId": "msg-02"}]
            })
        elif "/api/orders/ord-live-01" in path:
            return httpx.Response(200, json={
                "idempotencyKey": "ord-live-01",
                "status": "completed",
                "orderId": 101,
                "productId": 1,
                "quantity": 2
            })
        elif "/api/saga/ord-live-01" in path:
            return httpx.Response(200, json={
                "idempotencyKey": "ord-live-01",
                "state": "Completed"
            })
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    real_client_cls = httpx.Client

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", client_factory)

    adapter = OpsBridgeReadAdapter(base_url="http://order-api.local", read_token="issued-by-owner-for-test")

    # 1. Stuck outbox investigation
    ev_outbox = adapter.fetch_stuck_outbox(scope_id="ops-cluster-01")
    assert ev_outbox.facts["outbox_status"] == "PENDING"
    assert ev_outbox.facts["stuck_count"] == 2
    assert ev_outbox.verify_integrity() is True

    # 2. Real order timeline
    ev_order = adapter.fetch_order_timeline(order_id="ord-live-01", scope_id="ops-cluster-01")
    assert ev_order.facts["order_status"] == "completed"
    assert ev_order.facts["product_id"] == 1
    assert ev_order.verify_integrity() is True


def test_quan_adapter_branch_isolation(monkeypatch):
    def mock_handler(request: httpx.Request):
        auth = request.headers.get("Authorization")
        assert auth and "Bearer" in auth
        return httpx.Response(200, json={
            "request_id": "v-01",
            "risk_level": "medium",
            "risk_score": 50,
            "summary": "Verified voucher",
            "canonical_bound": True,
            "request_version": 1
        })

    transport = httpx.MockTransport(mock_handler)
    real_client_cls = httpx.Client

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", client_factory)

    adapter = QuanLyKhoReadAdapter(base_url="http://bankops.local:8000")
    ev = adapter.fetch_canonical_voucher(
        voucher_id="v-01",
        caller_branch_scope="branch-caugiay"
    )
    assert ev.scope_id == "branch-caugiay"
    assert ev.facts["canonical_bound"] is True
    assert ev.verify_integrity() is True

    with pytest.raises(PermissionError) as exc_info:
        adapter.fetch_canonical_voucher(
            voucher_id="v-01",
            caller_branch_scope="branch-caugiay",
            target_branch_id="branch-quan1"
        )
    assert "Cross-branch access denied" in str(exc_info.value)


def test_platform_adapter_evidence(monkeypatch):
    def mock_handler(request: httpx.Request):
        return httpx.Response(200, json={
            "status": "success",
            "data": {
                "alerts": [{
                    "labels": {"alertname": "fp-test-01", "service": "platform-core", "severity": "warning"},
                    "annotations": {"summary": "High CPU alert", "runbook_url": "https://runbooks.local/cpu"},
                    "state": "firing",
                    "activeAt": "2026-10-24T00:00:00Z"
                }]
            }
        })

    transport = httpx.MockTransport(mock_handler)
    real_client_cls = httpx.Client

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", client_factory)

    adapter = PlatformIncidentAdapter(base_url="http://prometheus.local:9090")
    ev = adapter.fetch_active_alert(alert_fingerprint="fp-test-01")
    assert ev.case_type == "incident"
    assert ev.source_service == "aks-sre-platform"
    assert ev.facts["alertname"] == "fp-test-01"
    assert ev.verify_integrity() is True


def test_storage_lifecycle_and_idempotency(tmp_path):
    db_file = str(tmp_path / "test_hub_idemp.db")
    storage = StorageManager(db_path=db_file)

    # Save initial run with idempotency_key
    storage.save_run(
        run_id="run-t1",
        idempotency_key="idemp-key-01",
        case_type="recon",
        entity_ref="TX-1",
        scope_id="outlet-hn-01",
        user_id="auditor-01",
        state="received"
    )
    run = storage.get_run("run-t1")
    assert run["state"] == "received"
    assert run["idempotency_key"] == "idemp-key-01"

    # Query by idempotency key
    run_by_key = storage.get_run_by_idempotency_key("idemp-key-01")
    assert run_by_key is not None
    assert run_by_key["run_id"] == "run-t1"

    # Non-existent idempotency key
    assert storage.get_run_by_idempotency_key("non-existent") is None

    # Record decision
    storage.record_human_decision("run-t1", "ACCEPT", "auditor-01", "Verified with bank")
    updated_run = storage.get_run("run-t1")
    assert updated_run["state"] == "closed"

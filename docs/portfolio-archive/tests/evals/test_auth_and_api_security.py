import os
import sys
import pytest
from fastapi.testclient import TestClient

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
AGENT_HUB_DIR = os.path.join(REPO_ROOT, "services/agent-hub")
if AGENT_HUB_DIR not in sys.path:
    sys.path.insert(0, AGENT_HUB_DIR)

from app.main import app
from app.auth import create_signed_token
from core.run_manager import RunManager
from core.storage import StorageManager


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db = str(tmp_path / "api_sec_hub.db")
    monkeypatch.setenv("AGENT_HUB_DB_PATH", test_db)
    monkeypatch.setenv("ENVIRONMENT", "test")
    # Clean isolation: bind fresh StorageManager and RunManager to app.state
    app.state.run_manager = RunManager(storage=StorageManager(db_path=test_db))
    return TestClient(app)


@pytest.fixture
def token_auditor_hn():
    return create_signed_token(
        user_id="auditor-hn-01",
        role="Auditor",
        allowed_scopes=["outlet-hn-01"]
    )


@pytest.fixture
def token_auditor_sg():
    return create_signed_token(
        user_id="auditor-sg-02",
        role="Auditor",
        allowed_scopes=["outlet-sg-02"]
    )


@pytest.fixture
def token_sre_lead():
    return create_signed_token(
        user_id="sre-lead-01",
        role="SRELead",
        allowed_scopes=["*"]
    )


def test_missing_auth_header_rejected_401(client):
    resp_get = client.get("/api/v1/investigations/run-fake-01")
    assert resp_get.status_code == 401
    assert "Missing or malformed" in resp_get.json()["detail"]

    resp_start = client.post("/api/v1/investigations/start", json={
        "case_type": "recon",
        "entity_ref": "TX-1",
        "scope_id": "outlet-hn-01"
    })
    assert resp_start.status_code == 401

    resp_decision = client.post("/api/v1/investigations/run-fake-01/decision", json={
        "decision": "ACCEPT_HYPOTHESIS",
        "reason": "Test"
    })
    assert resp_decision.status_code == 401


def test_forged_jwt_signature_rejected_401(client):
    # Token signed with forged/untrusted secret key
    forged_token = create_signed_token(
        user_id="attacker-01",
        role="Admin",
        allowed_scopes=["*"],
        secret_key="attacker-tampered-secret-key-12345678"
    )
    resp = client.get("/api/v1/investigations/run-fake-01", headers={
        "Authorization": f"Bearer {forged_token}"
    })
    assert resp.status_code == 401
    assert "signature mismatch" in resp.json()["detail"].lower()


def test_expired_jwt_rejected_401(client):
    expired_token = create_signed_token(
        user_id="auditor-hn-01",
        role="Auditor",
        allowed_scopes=["outlet-hn-01"],
        ttl_seconds=-30
    )
    resp = client.get("/api/v1/investigations/run-fake-01", headers={
        "Authorization": f"Bearer {expired_token}"
    })
    assert resp.status_code == 401
    assert "token expired" in resp.json()["detail"].lower()


def test_untrusted_issuer_rejected_401(client):
    bad_issuer_token = create_signed_token(
        user_id="auditor-hn-01",
        role="Auditor",
        allowed_scopes=["outlet-hn-01"],
        issuer="rogue-idp"
    )
    resp = client.get("/api/v1/investigations/run-fake-01", headers={
        "Authorization": f"Bearer {bad_issuer_token}"
    })
    assert resp.status_code == 401
    assert "untrusted issuer" in resp.json()["detail"].lower()


def test_scope_authorization_enforced_403(client, token_auditor_hn):
    # token_auditor_hn is only allowed for outlet-hn-01. Attempting outlet-sg-02 MUST return 403.
    resp = client.post("/api/v1/investigations/start", headers={
        "Authorization": f"Bearer {token_auditor_hn}"
    }, json={
        "case_type": "recon",
        "entity_ref": "TX-SG-99",
        "scope_id": "outlet-sg-02"
    })
    assert resp.status_code == 403
    assert "is not authorized to access scope 'outlet-sg-02'" in resp.json()["detail"]


def test_authorized_scope_succeeds(client, token_auditor_hn):
    resp = client.post("/api/v1/investigations/start", headers={
        "Authorization": f"Bearer {token_auditor_hn}"
    }, json={
        "case_type": "recon",
        "entity_ref": "TX-HN-01",
        "scope_id": "outlet-hn-01",
        "synthetic_payload": {"settled_count": 0, "discrepancy_type": "MISSING_LEDGER"}
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data
    assert data["severity"] == "HIGH"


def test_idempotency_deduplication_same_scope(client, token_sre_lead):
    headers = {
        "Authorization": f"Bearer {token_sre_lead}",
        "X-Idempotency-Key": "idemp-unique-test-999"
    }
    payload = {
        "case_type": "order_failure",
        "entity_ref": "ord-8801",
        "scope_id": "ops-cluster-01",
        "synthetic_payload": {"outbox_status": "PENDING", "age_seconds": 120, "retry_count": 4}
    }

    # First call
    r1 = client.post("/api/v1/investigations/start", headers=headers, json=payload)
    assert r1.status_code == 200
    run_id_1 = r1.json()["run_id"]

    # Replay call with same Idempotency-Key
    r2 = client.post("/api/v1/investigations/start", headers=headers, json=payload)
    assert r2.status_code == 200
    run_id_2 = r2.json()["run_id"]

    # Invariant: Idempotent replay must return the exact same run_id!
    assert run_id_1 == run_id_2


def test_idempotency_cross_scope_conflict_rejected_409(client, token_auditor_hn, token_auditor_sg):
    """
    P0 Invariant: User B in SG attempting to use User A's HN idempotency key
    MUST be rejected with HTTP 409 Conflict, NEVER return User A's proposal.
    """
    # 1. Auditor HN starts investigation with idempotency key
    r1 = client.post("/api/v1/investigations/start", headers={
        "Authorization": f"Bearer {token_auditor_hn}",
        "X-Idempotency-Key": "idemp-cross-scope-key-01"
    }, json={
        "case_type": "recon",
        "entity_ref": "TX-HN-101",
        "scope_id": "outlet-hn-01",
        "synthetic_payload": {"settled_count": 1, "diff_amount": 0.0, "discrepancy_type": "NONE"}
    })
    assert r1.status_code == 200

    # 2. Auditor SG attempts to reuse the same idempotency key for outlet-sg-02
    r2 = client.post("/api/v1/investigations/start", headers={
        "Authorization": f"Bearer {token_auditor_sg}",
        "X-Idempotency-Key": "idemp-cross-scope-key-01"
    }, json={
        "case_type": "recon",
        "entity_ref": "TX-SG-202",
        "scope_id": "outlet-sg-02",
        "synthetic_payload": {"settled_count": 1, "diff_amount": 0.0, "discrepancy_type": "NONE"}
    })
    assert r2.status_code == 409
    assert "Cross-scope reuse is forbidden" in r2.json()["detail"]


def test_idempotency_payload_mismatch_conflict_409(client, token_auditor_hn):
    """
    P0 Invariant: Same caller attempting to reuse an idempotency key
    with different entity_ref / parameters MUST be rejected with HTTP 409 Conflict.
    """
    headers = {
        "Authorization": f"Bearer {token_auditor_hn}",
        "X-Idempotency-Key": "idemp-param-mismatch-key"
    }
    # First call
    r1 = client.post("/api/v1/investigations/start", headers=headers, json={
        "case_type": "recon",
        "entity_ref": "TX-HN-101",
        "scope_id": "outlet-hn-01",
        "synthetic_payload": {"settled_count": 1, "diff_amount": 0.0, "discrepancy_type": "NONE"}
    })
    assert r1.status_code == 200

    # Second call with different entity_ref
    r2 = client.post("/api/v1/investigations/start", headers=headers, json={
        "case_type": "recon",
        "entity_ref": "TX-HN-999",
        "scope_id": "outlet-hn-01",
        "synthetic_payload": {"settled_count": 1, "diff_amount": 0.0, "discrepancy_type": "NONE"}
    })
    assert r2.status_code == 409
    assert "previously used for" in r2.json()["detail"]


def test_synthetic_payload_rejected_in_production(client, monkeypatch):
    prod_secret = "prod-secret-key-super-secure-32-chars-ok"
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("AGENT_HUB_JWT_SECRET", prod_secret)
    prod_token = create_signed_token(
        user_id="auditor-hn-01",
        role="Auditor",
        allowed_scopes=["outlet-hn-01"],
        secret_key=prod_secret
    )
    resp = client.post("/api/v1/investigations/start", headers={
        "Authorization": f"Bearer {prod_token}"
    }, json={
        "case_type": "recon",
        "entity_ref": "TX-HN-01",
        "scope_id": "outlet-hn-01",
        "synthetic_payload": {"fake": "data"}
    })
    assert resp.status_code == 400
    assert "synthetic_payload' is rejected in non-test environment" in resp.json()["detail"]


def test_decision_enforces_authoritative_reviewer_from_token(client, token_auditor_hn):
    # Start a run with Auditor token
    start_resp = client.post("/api/v1/investigations/start", headers={
        "Authorization": f"Bearer {token_auditor_hn}"
    }, json={
        "case_type": "recon",
        "entity_ref": "TX-HN-02",
        "scope_id": "outlet-hn-01",
        "synthetic_payload": {"settled_count": 1, "diff_amount": 0.0, "discrepancy_type": "NONE"}
    })
    assert start_resp.status_code == 200
    run_id = start_resp.json()["run_id"]

    # Post decision with Auditor token
    dec_resp = client.post(f"/api/v1/investigations/{run_id}/decision", headers={
        "Authorization": f"Bearer {token_auditor_hn}"
    }, json={
        "decision": "ACCEPT_HYPOTHESIS",
        "reason": "Verified bank statement"
    })
    assert dec_resp.status_code == 200
    assert dec_resp.json()["status"] == "closed"
    assert dec_resp.json()["run"]["reviewer_id"] == "auditor-hn-01"


def test_jwt_none_algorithm_rejected_401(client):
    """
    P0 Invariant: Header alg='none' must be strictly rejected with HTTP 401.
    """
    none_alg_token = create_signed_token(
        user_id="attacker-none",
        role="Admin",
        allowed_scopes=["*"],
        custom_header={"alg": "none", "typ": "JWT"}
    )
    resp = client.get("/api/v1/investigations/run-fake-01", headers={
        "Authorization": f"Bearer {none_alg_token}"
    })
    assert resp.status_code == 401
    assert "algorithm" in resp.json()["detail"].lower()


def test_jwt_nbf_future_rejected_401(client):
    """
    P0 Invariant: Token with future 'nbf' claim must be rejected with HTTP 401.
    """
    future_token = create_signed_token(
        user_id="auditor-hn-01",
        role="Auditor",
        allowed_scopes=["outlet-hn-01"],
        nbf_offset=300  # 5 minutes in future
    )
    resp = client.get("/api/v1/investigations/run-fake-01", headers={
        "Authorization": f"Bearer {future_token}"
    })
    assert resp.status_code == 401
    assert "not yet valid" in resp.json()["detail"].lower()


def test_auth_fails_closed_in_production_without_secret(monkeypatch):
    """
    P0 Invariant: Outside test/local, unset AGENT_HUB_JWT_SECRET must raise RuntimeError (fail-closed).
    """
    from app.auth import get_jwt_secret
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("AGENT_HUB_JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError) as exc_info:
        get_jwt_secret()
    assert "AGENT_HUB_JWT_SECRET must be explicitly set" in str(exc_info.value)


def test_duplicate_decision_rejected_409(client, token_auditor_hn):
    """
    P0 Invariant: A closed run must reject a second decision with HTTP 409 Conflict.
    """
    start_resp = client.post("/api/v1/investigations/start", headers={
        "Authorization": f"Bearer {token_auditor_hn}"
    }, json={
        "case_type": "recon",
        "entity_ref": "TX-HN-DEC-01",
        "scope_id": "outlet-hn-01",
        "synthetic_payload": {"settled_count": 1, "diff_amount": 0.0, "discrepancy_type": "NONE"}
    })
    assert start_resp.status_code == 200
    run_id = start_resp.json()["run_id"]

    # First decision -> Success 200
    r1 = client.post(f"/api/v1/investigations/{run_id}/decision", headers={
        "Authorization": f"Bearer {token_auditor_hn}"
    }, json={
        "decision": "ACCEPT_HYPOTHESIS",
        "reason": "First approved decision"
    })
    assert r1.status_code == 200
    assert r1.json()["status"] == "closed"

    # Second decision -> 409 Conflict
    r2 = client.post(f"/api/v1/investigations/{run_id}/decision", headers={
        "Authorization": f"Bearer {token_auditor_hn}"
    }, json={
        "decision": "REJECT_HYPOTHESIS",
        "reason": "Tampering duplicate decision"
    })
    assert r2.status_code == 409
    assert "already closed" in r2.json()["detail"].lower() or "already recorded" in r2.json()["detail"].lower()


def test_client_cannot_spoof_reviewer_id(client, token_auditor_hn):
    """
    P0 Invariant: If client passes 'reviewer_id' in body, it is completely ignored,
    and reviewer_id is bound strictly to the token's user_id.
    """
    start_resp = client.post("/api/v1/investigations/start", headers={
        "Authorization": f"Bearer {token_auditor_hn}"
    }, json={
        "case_type": "recon",
        "entity_ref": "TX-HN-SPOOF-01",
        "scope_id": "outlet-hn-01",
        "synthetic_payload": {"settled_count": 1, "diff_amount": 0.0, "discrepancy_type": "NONE"}
    })
    assert start_resp.status_code == 200
    run_id = start_resp.json()["run_id"]

    dec_resp = client.post(f"/api/v1/investigations/{run_id}/decision", headers={
        "Authorization": f"Bearer {token_auditor_hn}"
    }, json={
        "decision": "ACCEPT_HYPOTHESIS",
        "reason": "Legitimate check",
        "reviewer_id": "forged-super-admin-root"
    })
    assert dec_resp.status_code == 200
    assert dec_resp.json()["run"]["reviewer_id"] == "auditor-hn-01"
    assert dec_resp.json()["run"]["reviewer_id"] != "forged-super-admin-root"


def test_storage_evidence_hash_collision_does_not_overwrite(tmp_path):
    """
    P0 Invariant: EvidenceEnvelope immutability. ON CONFLICT DO NOTHING preserves original record.
    """
    from datetime import datetime, timezone, timedelta
    from schemas.evidence_envelope import EvidenceEnvelope

    db_path = str(tmp_path / "immutability_test.db")
    storage = StorageManager(db_path=db_path)
    storage.save_run(
        run_id="run-imm-01",
        idempotency_key="idemp-imm-01",
        case_type="recon",
        entity_ref="TX-01",
        scope_id="outlet-01",
        user_id="user-01",
        state="received"
    )

    ev_original = EvidenceEnvelope(
        case_type="recon",
        entity_ref="TX-01",
        source_service="retail-finance",
        source_sha="sha-original-1234",
        scope_id="outlet-01",
        record_version=1,
        observed_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        facts={"status": "ORIGINAL_FACT", "amount": 1000},
        source_refs=["/api/v1/recon/TX-01"]
    )
    storage.save_evidence("run-imm-01", ev_original)

    # Attempt to overwrite with same evidence_hash but modified source_sha / facts
    ev_tampered = EvidenceEnvelope(
        case_type="recon",
        entity_ref="TX-01",
        source_service="retail-finance",
        source_sha="sha-tampered-9999",
        scope_id="outlet-01",
        record_version=2,
        observed_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        facts={"status": "ORIGINAL_FACT", "amount": 1000},
        source_refs=["/api/v1/recon/TX-01-tampered"],
        evidence_hash=ev_original.evidence_hash  # Force collision
    )
    storage.save_evidence("run-imm-01", ev_tampered)

    evidences = storage.get_evidences_for_run("run-imm-01")
    assert len(evidences) == 1
    # Verify original preserved
    assert evidences[0].source_sha == "sha-original-1234"
    assert evidences[0].source_refs == ["/api/v1/recon/TX-01"]


def test_pii_masking_in_investigation_response(client, token_auditor_hn):
    """
    P0 Invariant: Responses containing phone numbers or account numbers must mask PII.
    """
    resp = client.post("/api/v1/investigations/start", headers={
        "Authorization": f"Bearer {token_auditor_hn}"
    }, json={
        "case_type": "recon",
        "entity_ref": "TX-PII-01",
        "scope_id": "outlet-hn-01",
        "synthetic_payload": {
            "account_number": "19034567890123",
            "phone_number": "0987654321",
            "customer_note": "Customer with phone 0987654321 transferred to 19034567890123",
            "settled_count": 0,
            "discrepancy_type": "MISSING_LEDGER"
        }
    })
    assert resp.status_code == 200
    data = resp.json()
    proposal_text = str(data)
    assert "0987654321" not in proposal_text
    assert "19034567890123" not in proposal_text


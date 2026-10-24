"""Contract tests for the single-message human-approved recovery pilot."""

import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["ENVIRONMENT"] = "test"

from app.auth import create_signed_token
from app.main import app
from adapters.ops_adapter import OpsBridgeReadAdapter
from core.action_executor import ActionExecutor
from core.run_manager import RunManager
from core.storage import StorageManager
from schemas.action_intent import ActionIntent
from schemas.evidence_envelope import EvidenceEnvelope


MESSAGE_ID = "c76e4bb5-bcce-4e13-8d32-d8bca6b7b521"
OTHER_MESSAGE_ID = "67192235-82f4-411b-a2ed-8a7208c9c534"
VERSION = "2026-10-24T12:00:00+00:00"
HMAC_KEY = "test-only-agent-recovery-hmac-key-at-least-32-bytes"


def token(user: str, role: str, scopes=("ops-cluster-01",)) -> dict[str, str]:
    signed = create_signed_token(user_id=user, role=role, allowed_scopes=list(scopes))
    return {"Authorization": f"Bearer {signed}"}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("OPSBRIDGE_AGENT_HMAC_KEY", HMAC_KEY)
    storage = StorageManager(db_path=str(tmp_path / "hub.db"))
    for run_id, owner in (
        ("run-01", "operator-01"),
        ("run-02", "operator-01"),
        ("run-03", "operator-01"),
        ("run-self", "same-sre"),
    ):
        storage.save_run(
            run_id, f"investigation-{run_id}", "order_failure", MESSAGE_ID,
            "ops-cluster-01", owner, "proposed",
        )
        storage.save_evidence(run_id, EvidenceEnvelope(
            case_type="order_failure", entity_ref="outbox-stuck-events",
            source_service="opsbridge-flashsale", source_sha="test-sha",
            scope_id="ops-cluster-01", record_version=1,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            facts={"messages": [{"messageId": MESSAGE_ID, "deadLetteredAt": VERSION}]},
            source_refs=["http://order-api.local/api/outbox/stuck"],
        ))
    app.state.run_manager = RunManager(storage=storage)
    app.state.action_executor = ActionExecutor(
        storage=storage, ops_adapter=OpsBridgeReadAdapter(base_url="http://order-api.local", read_token="test-token")
    )
    yield TestClient(app), storage, monkeypatch
    app.state.run_manager = None
    app.state.action_executor = None


def proposal(client, run_id="run-01", actor="operator-01", message_id=MESSAGE_ID, key="requeue-one-01"):
    return client.post("/api/v1/actions/intent", headers=token(actor, "SRE"), json={
        "run_id": run_id,
        "command_type": "REPLAY_STUCK_OUTBOX",
        "owner_service": "opsbridge-flashsale",
        "scope_id": "ops-cluster-01",
        "entity_ref": message_id,
        "idempotency_key": key,
        "parameters": {"expected_dead_lettered_at": VERSION},
    })


def approve(client, intent, actor="reviewer-01", role="SRELead"):
    return client.post(
        f"/api/v1/actions/{intent['intent_id']}/approve",
        headers=token(actor, role),
        json={
            "decision": "APPROVED",
            "intent_hash": intent["intent_hash"],
            "reason": "Reviewed the exact failed event and its version",
        },
    )


def assert_signed(request: httpx.Request):
    timestamp = request.headers["X-Agent-Timestamp"]
    digest = hashlib.sha256(request.content).hexdigest()
    payload = f"{request.method}\n{request.url.path}\n{timestamp}\n{digest}".encode()
    expected = hmac.new(HMAC_KEY.encode(), payload, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(expected, request.headers["X-Agent-Signature"])


def test_intent_hash_binds_run_requester_and_message():
    base = dict(
        intent_id="intent-001", run_id="run-01", requested_by="operator-01",
        command_type="REPLAY_STUCK_OUTBOX", owner_service="opsbridge-flashsale",
        target_endpoint=f"/internal/agent/outbox/{MESSAGE_ID}/requeue",
        scope_id="ops-cluster-01", entity_ref=MESSAGE_ID,
        parameters={"expected_dead_lettered_at": VERSION},
        idempotency_key="requeue-one-01",
    )
    first = ActionIntent(**base)
    assert first.intent_hash == ActionIntent(**{**base, "intent_id": "intent-002"}).intent_hash
    assert first.intent_hash != ActionIntent(**{**base, "run_id": "run-02"}).intent_hash
    assert first.intent_hash != ActionIntent(**{**base, "requested_by": "other"}).intent_hash


def test_same_canonical_evidence_can_support_two_independent_runs(tmp_path):
    storage = StorageManager(db_path=str(tmp_path / "shared-evidence.db"))
    evidence = EvidenceEnvelope(
        case_type="order_failure", entity_ref="outbox-stuck-events",
        source_service="opsbridge-flashsale", source_sha="owner-sha",
        scope_id="ops-cluster-01", record_version=0,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        facts={"messages": [{"messageId": MESSAGE_ID, "deadLetteredAt": VERSION}]},
    )
    for run_id in ("shared-run-a", "shared-run-b"):
        storage.save_run(run_id, f"unique-{run_id}", "order_failure",
                         "outbox-stuck-events", "ops-cluster-01", "operator-01", "proposed")
        storage.save_evidence(run_id, evidence)
        assert [item.evidence_hash for item in storage.get_evidences_for_run(run_id)] == [evidence.evidence_hash]


def test_intent_is_scoped_to_one_event_and_one_investigation(setup):
    client, _, _ = setup
    valid = proposal(client)
    assert valid.status_code == 200, valid.text
    intent = valid.json()
    assert intent["target_endpoint"] == f"/internal/agent/outbox/{MESSAGE_ID}/requeue"
    assert proposal(client).json()["intent_id"] == intent["intent_id"]
    assert proposal(client, message_id=OTHER_MESSAGE_ID).status_code == 409
    assert proposal(client, run_id="missing").status_code == 403
    assert proposal(client, message_id="all-stuck-events", key="requeue-other-01").status_code == 400
    assert proposal(client, message_id=OTHER_MESSAGE_ID, key="requeue-no-evidence-01").status_code == 409


def test_approval_requires_independent_authorized_reviewer(setup):
    client, _, _ = setup
    intent = proposal(client, run_id="run-02", key="requeue-approve-02").json()
    assert approve(client, intent, actor="operator-01").status_code == 403
    assert approve(client, intent, role="Checker").status_code == 403
    assert approve(client, intent, actor="outsider", role="SRELead").status_code == 200
    assert approve(client, intent).status_code == 409


def test_approved_command_is_signed_scoped_and_has_one_receipt(setup):
    client, _, monkeypatch = setup
    intent = proposal(client, run_id="run-03", key="requeue-execute-03").json()
    path = f"/api/v1/actions/{intent['intent_id']}/execute"
    assert client.post(path, headers=token("operator-01", "SRE")).status_code == 403
    assert approve(client, intent).status_code == 200

    observed = {"get": 0, "post": []}

    def owner(request: httpx.Request):
        assert_signed(request)
        if request.method == "GET":
            observed["get"] += 1
            return httpx.Response(200, json={
                "messageId": MESSAGE_ID,
                "deadLetteredAt": VERSION if observed["get"] == 1 else None,
                "processedAt": None,
            })
        observed["post"].append(request.url.path)
        assert request.url.path == f"/internal/agent/outbox/{MESSAGE_ID}/requeue"
        body = json.loads(request.content)
        assert body["intentHash"] == intent["intent_hash"]
        assert body["approvedBy"] == "reviewer-01"
        return httpx.Response(200, json={
            "status": "requeued", "messageId": MESSAGE_ID,
            "idempotencyKey": intent["idempotency_key"],
        })

    original_client = httpx.Client
    transport = httpx.MockTransport(owner)
    monkeypatch.setattr(httpx, "Client", lambda *a, **kw: original_client(*a, transport=transport, **kw))
    result = client.post(path, headers=token("operator-01", "SRE"))
    assert result.status_code == 200, result.text
    assert result.json()["verified"] is True
    assert observed["post"] == [f"/internal/agent/outbox/{MESSAGE_ID}/requeue"]
    replay = client.post(path, headers=token("operator-01", "SRE"))
    assert replay.json()["receipt_id"] == result.json()["receipt_id"]
    assert len(observed["post"]) == 1


def test_lost_owner_response_retries_same_idempotency_key(setup):
    client, storage, monkeypatch = setup
    intent = proposal(client, key="requeue-unknown-04").json()
    assert approve(client, intent).status_code == 200
    path = f"/api/v1/actions/{intent['intent_id']}/execute"
    owner_state = {"recovered": False, "posts": 0}

    def owner(request: httpx.Request):
        assert_signed(request)
        if request.method == "GET":
            return httpx.Response(200, json={
                "messageId": MESSAGE_ID,
                "deadLetteredAt": None if owner_state["recovered"] else VERSION,
            })
        owner_state["posts"] += 1
        assert json.loads(request.content)["idempotencyKey"] == intent["idempotency_key"]
        if owner_state["posts"] == 1:
            owner_state["recovered"] = True
            raise httpx.ReadTimeout("response lost after owner commit")
        return httpx.Response(200, json={
            "status": "already_applied", "messageId": MESSAGE_ID,
            "idempotencyKey": intent["idempotency_key"],
        })

    original_client = httpx.Client
    transport = httpx.MockTransport(owner)
    monkeypatch.setattr(httpx, "Client", lambda *a, **kw: original_client(*a, transport=transport, **kw))
    first = client.post(path, headers=token("operator-01", "SRE"))
    assert first.status_code == 503
    assert storage.get_intent(intent["intent_id"]).state == "UNKNOWN"
    second = client.post(path, headers=token("operator-01", "SRE"))
    assert second.status_code == 200, second.text
    assert second.json()["verified"] is True
    assert owner_state["posts"] == 2


def test_requester_cannot_approve_own_command(setup):
    client, _, _ = setup
    intent = proposal(client, run_id="run-self", actor="same-sre", key="requeue-self-05").json()
    assert approve(client, intent, actor="same-sre").status_code == 403

import pytest
import sys
import os
from datetime import datetime, timezone, timedelta

# Ensure agent-hub is on sys.path
AGENT_HUB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/agent-hub"))
if AGENT_HUB_DIR not in sys.path:
    sys.path.insert(0, AGENT_HUB_DIR)

from schemas.evidence_envelope import EvidenceEnvelope
from schemas.investigation_proposal import InvestigationProposal


def test_evidence_envelope_hash_generation_and_integrity():
    facts = {"tx_ref": "TX-1001", "amount": 150000.0, "status": "SETTLED"}
    envelope = EvidenceEnvelope(
        case_type="recon",
        entity_ref="TX-1001",
        source_service="retail-finance",
        source_sha="433447f",
        scope_id="outlet-hn-01",
        record_version=1,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        facts=facts,
        source_refs=["http://127.0.0.1:8088/api/v1/retail/reconcile/batches/b-101/discrepancies"]
    )
    
    # Assert hash is automatically generated
    assert envelope.evidence_hash is not None
    assert len(envelope.evidence_hash) == 64  # SHA-256
    
    # Assert integrity verification passes
    assert envelope.verify_integrity() is True
    
    # Tamper with facts should fail integrity
    envelope.facts["amount"] = 999999.0
    assert envelope.verify_integrity() is False


def test_evidence_envelope_expiration():
    now = datetime.now(timezone.utc)
    expired_envelope = EvidenceEnvelope(
        case_type="order_failure",
        entity_ref="ord-8801",
        source_service="opsbridge-flashsale",
        source_sha="b507464",
        scope_id="ops-cluster-01",
        record_version=1,
        expires_at=now - timedelta(seconds=10),
        facts={"order_status": "RESERVED"}
    )
    assert expired_envelope.is_expired(now) is True

    valid_envelope = EvidenceEnvelope(
        case_type="order_failure",
        entity_ref="ord-8801",
        source_service="opsbridge-flashsale",
        source_sha="b507464",
        scope_id="ops-cluster-01",
        record_version=1,
        expires_at=now + timedelta(seconds=60),
        facts={"order_status": "RESERVED"}
    )
    assert valid_envelope.is_expired(now) is False


def test_investigation_proposal_citation_invariant():
    # A CRITICAL proposal without citations MUST be forced to abstain
    proposal = InvestigationProposal(
        run_id="run-001",
        case_version=1,
        summary="Critical error detected in order processing",
        hypotheses=["Worker crash after Redis reserve"],
        citations=[],  # Empty citations
        unknowns=[],
        severity="CRITICAL",
        suggested_owner="SRE",
        suggested_read_only_checks=["Check Grafana dashboard"],
        abstained=False,
        model_or_rule_version="v1.0.0"
    )
    
    assert proposal.abstained is True
    assert any("Missing required citations" in u for u in proposal.unknowns)


def test_investigation_proposal_destructive_command_blocking():
    # If a proposal contains dangerous shell execution steps, sanitize and abstain
    proposal = InvestigationProposal(
        run_id="run-002",
        case_version=1,
        summary="Suspected stuck outbox queue",
        hypotheses=["Publisher timeout"],
        citations=["http://127.0.0.1:8088/api/v1/ops/outbox/stuck"],
        unknowns=[],
        severity="MEDIUM",
        suggested_owner="Auditor",
        suggested_read_only_checks=[
            "GET /api/v1/ops/outbox/stuck",
            "kubectl delete namespace default"  # DANGEROUS!
        ],
        abstained=False,
        model_or_rule_version="v1.0.0"
    )
    
    assert proposal.abstained is True
    assert "kubectl delete namespace default" not in proposal.suggested_read_only_checks
    assert any("Blocked dangerous action" in u for u in proposal.unknowns)

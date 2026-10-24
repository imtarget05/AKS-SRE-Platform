import json
import uuid
import hashlib
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from core.storage import StorageManager
from core.verifier import DeterministicVerifier
from core.critic import ProposalCritic
from adapters.retail_adapter import RetailReadAdapter
from adapters.ops_adapter import OpsBridgeReadAdapter
from adapters.quan_adapter import QuanLyKhoReadAdapter
from adapters.platform_adapter import PlatformIncidentAdapter
from schemas.evidence_envelope import EvidenceEnvelope
from schemas.investigation_proposal import InvestigationProposal


class RunManager:
    """
    Central Orchestrator managing the multi-agent investigation lifecycle.
    Enforces strict transitions:
    received -> authorized -> evidence_collected -> policy_checked -> proposed/abstained -> closed
    """
    def __init__(self, storage: Optional[StorageManager] = None):
        self.storage = storage or StorageManager()
        self.retail_adapter = RetailReadAdapter()
        self.ops_adapter = OpsBridgeReadAdapter()
        self.quan_adapter = QuanLyKhoReadAdapter()
        self.platform_adapter = PlatformIncidentAdapter()

    def start_investigation(
        self,
        case_type: str,
        entity_ref: str,
        scope_id: str,
        user_id: str = "analyst-01",
        idempotency_key: Optional[str] = None,
        synthetic_payload: Optional[Dict[str, Any]] = None,
        target_scope_override: Optional[str] = None
    ) -> InvestigationProposal:
        # Idempotency deduplication check & strict cross-scope/caller/payload binding
        effective_idempotency_key = idempotency_key or f"{case_type}:{entity_ref}:{scope_id}:{user_id}"
        req_hash = hashlib.sha256(
            json.dumps({"case_type": case_type, "entity_ref": entity_ref, "payload": synthetic_payload}, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:16]

        existing_run = self.storage.get_run_by_idempotency_key(effective_idempotency_key)
        if existing_run:
            # P0 Invariant 1: Cross-scope idempotency key reuse must be rejected with 409 Conflict
            if existing_run.get("scope_id") != scope_id:
                raise HTTPException(
                    status_code=409,
                    detail=f"Idempotency conflict: Key '{effective_idempotency_key}' is already bound to scope '{existing_run.get('scope_id')}'. Cross-scope reuse is forbidden."
                )
            # P0 Invariant 2: Cross-user idempotency key reuse must be rejected with 409 Conflict
            if existing_run.get("user_id") != user_id:
                raise HTTPException(
                    status_code=409,
                    detail=f"Idempotency conflict: Key '{effective_idempotency_key}' is owned by user '{existing_run.get('user_id')}'. Cross-user reuse is forbidden."
                )
            # P0 Invariant 3: Payload/Entity mismatch must be rejected with 409 Conflict
            if existing_run.get("case_type") != case_type or existing_run.get("entity_ref") != entity_ref:
                raise HTTPException(
                    status_code=409,
                    detail=f"Idempotency conflict: Key '{effective_idempotency_key}' was previously used for {existing_run.get('case_type')}:{existing_run.get('entity_ref')}."
                )
            if existing_run.get("request_hash") and existing_run["request_hash"] != req_hash:
                raise HTTPException(
                    status_code=409,
                    detail=f"Idempotency conflict: Key '{effective_idempotency_key}' was previously submitted with different request parameters."
                )
            if existing_run.get("proposal"):
                return InvestigationProposal(**existing_run["proposal"])

        run_id = f"run-{uuid.uuid4().hex[:12]}"
        self.storage.save_run(
            run_id=run_id,
            idempotency_key=effective_idempotency_key,
            case_type=case_type,
            entity_ref=entity_ref,
            scope_id=scope_id,
            user_id=user_id,
            request_hash=req_hash,
            state="received"
        )

        # Step 1: Command Injection Guard
        if synthetic_payload and any(cmd in str(synthetic_payload).lower() for cmd in ["kubectl delete", "rm -rf", "drop table", "truncate"]):
            proposal = InvestigationProposal(
                run_id=run_id,
                case_version=1,
                summary=f"Investigation for {entity_ref}: COMMAND_EXECUTION_PROHIBITED",
                hypotheses=[],
                citations=[],
                unknowns=["COMMAND_EXECUTION_PROHIBITED", "Detected dangerous command injection in runbook; execution blocked."],
                severity="CRITICAL",
                suggested_owner="SRE",
                suggested_read_only_checks=[],
                abstained=True,
                model_or_rule_version="v1.0.0-security-guard"
            )
            self.storage.update_run_state(run_id, state="proposed", proposal_json=proposal.model_dump_json())
            return proposal

        # Step 2: Fallback Guard (e.g. Alertmanager offline)
        if synthetic_payload and synthetic_payload.get("alertmanager_status") == "UNREACHABLE":
            proposal = InvestigationProposal(
                run_id=run_id,
                case_version=1,
                summary=f"Investigation for {entity_ref}: FALLBACK_HEURISTIC_TRIAGE",
                hypotheses=["Alertmanager is unreachable; fallen back to heuristic log triage."],
                citations=[],
                unknowns=["FALLBACK_HEURISTIC_TRIAGE", "Alertmanager offline, live alert metrics unavailable."],
                severity="MEDIUM",
                suggested_owner="OnCall",
                suggested_read_only_checks=[],
                abstained=True,
                model_or_rule_version="v1.0.0-fallback-engine"
            )
            self.storage.update_run_state(run_id, state="proposed", proposal_json=proposal.model_dump_json())
            return proposal

        # Step 3: Mutation Tool Guard
        mutation_verbs = ["post ", "put ", "delete ", "patch ", "requeue", "apply"]
        if any(verb in entity_ref.lower() for verb in mutation_verbs) or (synthetic_payload and any(verb in str(synthetic_payload).lower() for verb in mutation_verbs)):
            proposal = InvestigationProposal(
                run_id=run_id,
                case_version=1,
                summary=f"Policy Violation for {entity_ref}: POLICY_VIOLATION_MUTATION_PROHIBITED",
                hypotheses=[],
                citations=[],
                unknowns=["POLICY_VIOLATION_MUTATION_PROHIBITED", "Mutation operations are strictly prohibited in read-only investigation orchestrator."],
                severity="CRITICAL",
                suggested_owner="Auditor",
                suggested_read_only_checks=[],
                abstained=True,
                model_or_rule_version="v1.0.0-security-guard"
            )
            self.storage.update_run_state(run_id, state="proposed", proposal_json=proposal.model_dump_json())
            return proposal

        self.storage.update_run_state(run_id, state="authorized")

        # Step 2: Evidence Collection via scoped Read Adapters
        evidences: List[EvidenceEnvelope] = []
        try:
            if case_type == "recon":
                ev = self.retail_adapter.fetch_discrepancy_evidence(
                    batch_id=entity_ref,
                    caller_outlet_scope=scope_id,
                    target_outlet_id=target_scope_override,
                    synthetic_payload=synthetic_payload
                )
                evidences.append(ev)
            elif case_type == "order_failure":
                if "outbox" in entity_ref:
                    ev = self.ops_adapter.fetch_stuck_outbox(
                        scope_id=scope_id,
                        synthetic_payload=synthetic_payload
                    )
                else:
                    ev = self.ops_adapter.fetch_order_timeline(
                        order_id=entity_ref,
                        scope_id=scope_id,
                        synthetic_payload=synthetic_payload
                    )
                evidences.append(ev)
            elif case_type == "voucher_check":
                ev = self.quan_adapter.fetch_canonical_voucher(
                    voucher_id=entity_ref,
                    caller_branch_scope=scope_id,
                    target_branch_id=target_scope_override,
                    synthetic_payload=synthetic_payload
                )
                evidences.append(ev)
            elif case_type == "incident":
                ev = self.platform_adapter.fetch_active_alert(
                    alert_fingerprint=entity_ref,
                    scope_id=scope_id,
                    synthetic_payload=synthetic_payload
                )
                evidences.append(ev)
        except PermissionError as e:
            # Cross-scope security violation: MUST abstain
            err_msg = str(e)
            verdict_code = (
                "ACCESS_DENIED_CROSS_SCOPE" if "cross-scope" in err_msg.lower()
                else ("ACCESS_DENIED_CROSS_BRANCH" if "cross-branch" in err_msg.lower()
                else "SECURITY_POLICY_DENIED")
            )
            proposal = InvestigationProposal(
                run_id=run_id,
                case_version=1,
                summary=f"Security Policy Denied: {verdict_code} - {err_msg}",
                hypotheses=[],
                citations=[],
                unknowns=[verdict_code, err_msg],
                severity="CRITICAL",
                suggested_owner="SecurityOfficer",
                suggested_read_only_checks=[],
                abstained=True,
                model_or_rule_version="v1.0.0-security-guard"
            )
            self.storage.update_run_state(run_id, state="proposed", proposal_json=proposal.model_dump_json())
            return proposal

        for ev in evidences:
            self.storage.save_evidence(run_id, ev)

        self.storage.update_run_state(run_id, state="evidence_collected")

        # Step 3: Deterministic Policy Verifier
        verdict = "NORMAL"
        severity = "LOW"
        hypotheses = []
        target_ev = evidences[0] if evidences else None

        if target_ev:
            if case_type == "recon":
                verdict, severity, hypotheses = DeterministicVerifier.verify_retail_reconciliation(target_ev)
            elif case_type == "order_failure":
                verdict, severity, hypotheses = DeterministicVerifier.verify_ops_order_and_outbox(target_ev)
            elif case_type == "voucher_check":
                verdict, severity, hypotheses = DeterministicVerifier.verify_quanlykho_voucher(target_ev, user_id=user_id)
            elif case_type == "incident":
                verdict, severity, hypotheses = DeterministicVerifier.verify_platform_incident(target_ev)

        self.storage.update_run_state(run_id, state="policy_checked")

        # Step 4: Proposal Drafting
        citations = [ref for ev in evidences for ref in ev.source_refs]
        suggested_checks = [f"Audit {ref}" for ref in citations]

        # Role mapping
        owner_map = {
            "recon": "Auditor",
            "order_failure": "SRE",
            "voucher_check": "Checker",
            "incident": "OnCall"
        }

        # Check if policy explicitly forces abstain (e.g. Maker-Checker violation or Stale Version)
        must_abstain = False
        if verdict in ("POLICY_VIOLATION_MAKER_CANNOT_CHECK", "STALE_RECORD_VERSION_REFRESH_REQUIRED", "COMMAND_EXECUTION_PROHIBITED"):
            must_abstain = True

        draft_proposal = InvestigationProposal(
            run_id=run_id,
            case_version=target_ev.record_version if target_ev else 1,
            summary=f"Investigation for {entity_ref}: {verdict}",
            hypotheses=hypotheses,
            citations=citations,
            unknowns=[],
            severity=severity,
            suggested_owner=owner_map.get(case_type, "Operator"),
            suggested_read_only_checks=suggested_checks,
            abstained=must_abstain,
            model_or_rule_version="v1.0.0-rule-engine"
        )

        # Step 5: Proposal Critic & Safety Audit
        verified_proposal = ProposalCritic.audit_proposal(draft_proposal, evidences)
        self.storage.update_run_state(run_id, state="proposed", proposal_json=verified_proposal.model_dump_json())

        return verified_proposal

    def record_decision(self, run_id: str, decision: str, reviewer_id: str, reason: str) -> Dict[str, Any]:
        self.storage.record_human_decision(run_id, decision, reviewer_id, reason)
        return self.storage.get_run(run_id)

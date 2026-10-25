from typing import List, Tuple
from schemas.evidence_envelope import EvidenceEnvelope
from schemas.investigation_proposal import InvestigationProposal
from core.pii_masker import PIIMasker


class ProposalCritic:
    """
    Critic and safety guardrail.
    Audits citations, ensures evidence provenance, filters dangerous commands,
    and forces abstain on conflicting/unverified claims.
    """

    FORBIDDEN_COMMAND_PATTERNS = [
        "rm -rf", "drop table", "truncate", "delete from",
        "kubectl delete", "terraform apply", "terraform destroy",
        "requeue", "post ledger", "approve", "rollback"
    ]

    @classmethod
    def audit_proposal(
        cls,
        proposal: InvestigationProposal,
        evidences: List[EvidenceEnvelope]
    ) -> InvestigationProposal:
        valid_refs = set()
        for ev in evidences:
            valid_refs.update(ev.source_refs)
            if ev.evidence_hash:
                valid_refs.add(ev.evidence_hash)
            valid_refs.add(ev.entity_ref)

        # Invariant 1: Citations must be grounded in collected evidences
        verified_citations = []
        for citation in proposal.citations:
            if any(ref in citation or citation in ref for ref in valid_refs):
                verified_citations.append(citation)
            else:
                proposal.unknowns.append(f"Unverified citation dropped: {citation}")

        proposal.citations = verified_citations

        # Invariant 2: High/Critical severity requires non-empty citations
        if proposal.severity in ("HIGH", "CRITICAL") and not proposal.citations:
            proposal.abstained = True
            if "High/Critical severity requires valid citations; proposal abstained." not in proposal.unknowns:
                proposal.unknowns.append("High/Critical severity requires valid citations; proposal abstained.")

        # Invariant 3: Sanitize destructive commands in suggested checks
        safe_checks = []
        for check in proposal.suggested_read_only_checks:
            check_lower = check.lower()
            if any(pattern in check_lower for pattern in cls.FORBIDDEN_COMMAND_PATTERNS):
                proposal.abstained = True
                proposal.unknowns.append(f"Blocked dangerous command proposal: {check}")
            else:
                safe_checks.append(check)
        proposal.suggested_read_only_checks = safe_checks

        # Invariant 4: Sanitize PII from proposal content
        proposal.summary = PIIMasker.mask_string(proposal.summary)
        proposal.hypotheses = [PIIMasker.mask_string(h) for h in proposal.hypotheses]
        proposal.unknowns = [PIIMasker.mask_string(u) for u in proposal.unknowns]
        proposal.citations = [PIIMasker.mask_string(c) for c in proposal.citations]
        proposal.suggested_read_only_checks = [PIIMasker.mask_string(chk) for chk in proposal.suggested_read_only_checks]

        return proposal

from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class InvestigationProposal(BaseModel):
    """
    Standardized Proposal emitted by Agent Hub for human operator review.
    Invariants:
    - Never emits executable commands (read-only verification guidelines only).
    - If citations are missing for high-severity claims, proposal MUST abstain.
    - Fully traceable to model/rule engine version and investigation run ID.
    """
    run_id: str = Field(..., description="Unique investigation run ID")
    case_version: int = Field(..., description="Target case version evaluated")
    summary: str = Field(..., description="Concise investigation overview for the human operator")
    hypotheses: List[str] = Field(default_factory=list, description="Plausible root cause hypotheses based on facts")
    citations: List[str] = Field(default_factory=list, description="Explicit source citations from EvidenceEnvelopes")
    unknowns: List[str] = Field(default_factory=list, description="Missing data, tool timeouts, or ambiguous items")
    severity: str = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL")
    suggested_owner: str = Field(..., description="Role responsible for action: SRE | Auditor | Checker | OnCall")
    suggested_read_only_checks: List[str] = Field(
        default_factory=list,
        description="Recommended manual read-only checks (URLs, dashboard queries, SOP steps)"
    )
    abstained: bool = Field(default=False, description="Flagged true if evidence is insufficient or policy prohibits decision")
    model_or_rule_version: str = Field(..., description="Exact version identifier of the rule engine or LLM prompt")
    cost_usd: float = Field(default=0.0, description="Estimated inference cost in USD")

    @model_validator(mode="after")
    def enforce_citation_and_safety_invariants(self) -> "InvestigationProposal":
        # Invariant 1: High/Critical proposals without citations must abstain
        if self.severity in ("HIGH", "CRITICAL") and not self.citations and not self.abstained:
            self.abstained = True
            if "Missing required citations for high severity investigation" not in self.unknowns:
                self.unknowns.append("Missing required citations for high severity investigation; model abstained.")

        # Invariant 2: Suggested checks must not contain dangerous destructive commands
        forbidden_keywords = [
            "rm -rf", "drop table", "truncate", "delete from", "kubectl delete",
            "terraform apply", "terraform destroy", "requeue", "post ledger", "approve"
        ]
        sanitized_checks = []
        for check in self.suggested_read_only_checks:
            check_lower = check.lower()
            if any(forbidden in check_lower for forbidden in forbidden_keywords):
                self.abstained = True
                self.unknowns.append(f"Blocked dangerous action proposal: {check}")
            else:
                sanitized_checks.append(check)
        self.suggested_read_only_checks = sanitized_checks
        return self

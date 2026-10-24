import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class EvidenceEnvelope(BaseModel):
    """
    Standardized Evidence Envelope for all domain facts collected by Agent Hub.
    Invariants:
    - Immutable facts identified by SHA-256 hash.
    - Mandatory source_sha and record_version to prevent stale decisions.
    - Explicit scope_id for tenant/branch/outlet authorization boundary.
    """
    case_type: str = Field(..., description="Business case type: recon | order_failure | voucher_check | incident")
    entity_ref: str = Field(..., description="Canonical business entity reference (tx_ref, order_id, voucher_id, alert_fp)")
    source_service: str = Field(..., description="retail-finance | opsbridge-flashsale | quanlykho | aks-sre-platform")
    source_sha: str = Field(..., description="Git commit SHA or image digest of the producing service")
    scope_id: str = Field(..., description="Mandatory tenant scope: outlet_id, branch_id, or cluster_id")
    record_version: int = Field(..., description="Monotonically increasing version of the canonical record")
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp UTC when evidence was fetched")
    expires_at: datetime = Field(..., description="TTL for this evidence snapshot")
    facts: Dict[str, Any] = Field(..., description="Structured domain facts extracted from read adapter")
    source_refs: List[str] = Field(default_factory=list, description="Canonical REST URLs / endpoints source of truth")
    classification: str = Field(default="INTERNAL_CONFIDENTIAL", description="INTERNAL_CONFIDENTIAL | PII_REDACTED")
    redaction_level: str = Field(default="NONE", description="NONE | PARTIAL | FULL")
    evidence_hash: Optional[str] = Field(default=None, description="SHA-256 checksum over canonical facts")

    @model_validator(mode="after")
    def compute_evidence_hash_if_missing(self) -> "EvidenceEnvelope":
        if not self.evidence_hash:
            # Deterministic JSON representation
            payload = json.dumps(self.facts, sort_keys=True, default=str)
            self.evidence_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return self

    def is_expired(self, current_time: Optional[datetime] = None) -> bool:
        now = current_time or datetime.now(timezone.utc)
        return now > self.expires_at

    def verify_integrity(self) -> bool:
        payload = json.dumps(self.facts, sort_keys=True, default=str)
        expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return self.evidence_hash == expected

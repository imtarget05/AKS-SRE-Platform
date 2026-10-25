import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, model_validator


class ActionIntent(BaseModel):
    """
    Immutable typed action proposal drafted by Agent Hub under ADR 024.
    Strictly bounded by command type, owner service, and cryptographic intent_hash.
    """
    intent_id: str = Field(..., description="Unique intent identifier (e.g. intent-xxx)")
    run_id: str = Field(..., description="Originating investigation run ID")
    requested_by: str = Field(..., description="Authenticated actor who proposed the action")
    command_type: str = Field(..., description="Allowlisted command: REPLAY_STUCK_OUTBOX | RETRY_DLQ_MESSAGE")
    owner_service: str = Field(..., description="Target service: opsbridge-flashsale | quanlykho | retail-finance")
    target_endpoint: str = Field(..., description="Exact allowlisted REST endpoint on owner service")
    scope_id: str = Field(..., description="Tenant / outlet / cluster boundary")
    entity_ref: str = Field(..., description="Target entity ID or topic name")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Command parameters")
    idempotency_key: str = Field(..., description="Unique idempotency key for replay prevention")
    risk_level: str = Field(default="MEDIUM", description="LOW | MEDIUM | HIGH | CRITICAL")
    state: str = Field(default="AWAITING_APPROVAL", description="AWAITING_APPROVAL | APPROVED | REJECTED | EXECUTING | SUCCEEDED | FAILED | EXPIRED")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=15))
    intent_hash: Optional[str] = Field(default=None, description="SHA-256 hash of immutable intent fields")

    @model_validator(mode="after")
    def compute_intent_hash(self) -> "ActionIntent":
        if not self.intent_hash:
            canonical_payload = {
                "run_id": self.run_id,
                "requested_by": self.requested_by,
                "command_type": self.command_type,
                "owner_service": self.owner_service,
                "target_endpoint": self.target_endpoint,
                "scope_id": self.scope_id,
                "entity_ref": self.entity_ref,
                "parameters": self.parameters,
                "idempotency_key": self.idempotency_key
            }
            raw = json.dumps(canonical_payload, sort_keys=True, default=str)
            self.intent_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return self

    def is_expired(self, current_time: Optional[datetime] = None) -> bool:
        now = current_time or datetime.now(timezone.utc)
        return now > self.expires_at


class ApproveActionRequest(BaseModel):
    decision: str = Field(..., description="APPROVED | REJECTED")
    intent_hash: str = Field(..., description="Must match the exact reviewed intent_hash")
    reason: str = Field(..., description="Audit reason for approval or rejection")


class ExecutionReceipt(BaseModel):
    """
    Cryptographic receipt of action execution and post-state verification.
    """
    receipt_id: str = Field(..., description="Unique receipt identifier")
    intent_id: str = Field(..., description="Target action intent ID")
    owner_command_id: Optional[str] = Field(default=None, description="Transaction/Message ID returned by owner service")
    idempotency_key: str = Field(..., description="Replay prevention key used")
    executed_by: str = Field(..., description="Agent executor ID")
    approved_by: str = Field(..., description="Human approver ID")
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    owner_status_code: int = Field(..., description="HTTP status code from owner system")
    before_state: Dict[str, Any] = Field(..., description="Snapshot of target before execution")
    after_state: Dict[str, Any] = Field(..., description="Snapshot of target after execution")
    verified: bool = Field(..., description="True if post-state satisfies the recovery condition")
    audit_ref: str = Field(..., description="Audit trail link or correlation ID")
    result_summary: str = Field(..., description="Human-readable execution outcome")

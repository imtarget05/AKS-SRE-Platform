import os
import sys
from contextlib import asynccontextmanager

# Ensure agent-hub directory is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from core.run_manager import RunManager
from core.action_executor import ActionExecutor
from core.pii_masker import PIIMasker
from schemas.investigation_proposal import InvestigationProposal
from schemas.action_intent import ActionIntent, ApproveActionRequest, ExecutionReceipt
from app.auth import authenticate_bearer_token, authorize_scope_access, UserCredential, get_jwt_secret


run_manager = RunManager()
action_executor = ActionExecutor(storage=run_manager.storage)


def get_run_manager() -> RunManager:
    if hasattr(app.state, "run_manager") and app.state.run_manager is not None:
        return app.state.run_manager
    return run_manager


def get_action_executor() -> ActionExecutor:
    if hasattr(app.state, "action_executor") and app.state.action_executor is not None:
        return app.state.action_executor
    return action_executor


def is_test_environment() -> bool:
    return os.environ.get("ENVIRONMENT", "production").lower() == "test"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail-closed check: verify JWT secret configuration
    get_jwt_secret()
    # Self-healing: recover dangling runs from any ungraceful shutdowns
    active_mgr = get_run_manager()
    active_mgr.storage.recover_dangling_runs()
    yield


app = FastAPI(
    title="Agent Hub Investigation Service",
    description="Cross-repo investigation with approval-gated recovery commands for OpsBridge, QuanLyKho, and AKS SRE Platform",
    version="2.0.0",
    lifespan=lifespan
)


class StartInvestigationRequest(BaseModel):
    case_type: str = Field(..., description="recon | order_failure | voucher_check | incident")
    entity_ref: str = Field(..., description="Target business reference: tx_ref, order_id, voucher_id, alert_fp")
    scope_id: str = Field(..., description="Mandatory tenant/outlet/branch scope ID")
    idempotency_key: Optional[str] = Field(default=None, description="Optional client idempotency key for replay safety")
    synthetic_payload: Optional[Dict[str, Any]] = Field(default=None, description="Only permitted in TEST environment")


class RecordDecisionRequest(BaseModel):
    decision: str = Field(..., description="ACCEPT_HYPOTHESIS | REJECT_HYPOTHESIS | REQUIRE_MORE_INFO")
    reason: str = Field(..., description="Audit reason for the human decision")


class CreateIntentRequest(BaseModel):
    run_id: str = Field(..., description="Originating investigation run ID")
    command_type: str = Field(..., description="Allowlisted command: REPLAY_STUCK_OUTBOX | REPLAY_STUCK_VOUCHER | ACKNOWLEDGE_INCIDENT")
    owner_service: str = Field(..., description="Target service: opsbridge-flashsale | quanlykho | aks-sre-platform")
    scope_id: str = Field(..., description="Scope boundary (e.g. ops-cluster-01)")
    entity_ref: str = Field(..., description="Target entity ref")
    idempotency_key: str = Field(..., description="Client idempotency key")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)


@app.get("/healthz")
def health_check():
    return {"status": "healthy", "service": "agent-hub", "version": "1.0.0"}


@app.post("/api/v1/investigations/start", response_model=InvestigationProposal)
def start_investigation(
    req: StartInvestigationRequest,
    user: UserCredential = Depends(authenticate_bearer_token),
    mgr: RunManager = Depends(get_run_manager),
    x_idempotency_key: Optional[str] = Header(default=None)
):
    # Enforce Server-Side Scope Authorization
    authorize_scope_access(user, req.scope_id)

    # Disable synthetic_payload in production outside test mode
    payload = None
    if req.synthetic_payload:
        if not is_test_environment():
            raise HTTPException(
                status_code=400,
                detail="Policy violation: 'synthetic_payload' is rejected in non-test environment."
            )
        payload = req.synthetic_payload

    effective_idempotency = x_idempotency_key or req.idempotency_key

    try:
        proposal = mgr.start_investigation(
            case_type=req.case_type,
            entity_ref=req.entity_ref,
            scope_id=req.scope_id,
            user_id=user.user_id,
            idempotency_key=effective_idempotency,
            synthetic_payload=payload
        )
        return proposal
    except HTTPException:
        raise
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/investigations/{run_id}")
def get_investigation(
    run_id: str,
    user: UserCredential = Depends(authenticate_bearer_token),
    mgr: RunManager = Depends(get_run_manager)
):
    run = mgr.storage.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    # Authorize caller scope to view this run
    authorize_scope_access(user, run["scope_id"])
    return PIIMasker.sanitize(run)


@app.post("/api/v1/investigations/{run_id}/decision")
def record_decision(
    run_id: str,
    req: RecordDecisionRequest,
    user: UserCredential = Depends(authenticate_bearer_token),
    mgr: RunManager = Depends(get_run_manager)
):
    run = mgr.storage.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    # Authorize caller scope
    authorize_scope_access(user, run["scope_id"])

    # Authorize role: only Auditor, Checker, SRE, or SecurityOfficer can record decisions
    allowed_roles = ["Auditor", "Checker", "SRE", "SecurityOfficer", "SRELead"]
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: Role '{user.role}' is not authorized to record decisions. Allowed: {allowed_roles}"
        )

    # Invariant: reviewer_id is bound strictly to user.user_id from the verified JWT token
    updated_run = mgr.record_decision(
        run_id=run_id,
        decision=req.decision,
        reviewer_id=user.user_id,
        reason=req.reason
    )
    return {"status": "closed", "run": PIIMasker.sanitize(updated_run)}


@app.post("/api/v1/actions/intent", response_model=ActionIntent)
def create_action_intent(
    req: CreateIntentRequest,
    user: UserCredential = Depends(authenticate_bearer_token),
    executor: ActionExecutor = Depends(get_action_executor)
):
    authorize_scope_access(user, req.scope_id)
    return executor.create_intent(
        run_id=req.run_id,
        requester_id=user.user_id,
        command_type=req.command_type,
        owner_service=req.owner_service,
        scope_id=req.scope_id,
        entity_ref=req.entity_ref,
        idempotency_key=req.idempotency_key,
        parameters=req.parameters
    )


@app.post("/api/v1/actions/{intent_id}/approve", response_model=ActionIntent)
def approve_action_intent(
    intent_id: str,
    req: ApproveActionRequest,
    user: UserCredential = Depends(authenticate_bearer_token),
    executor: ActionExecutor = Depends(get_action_executor)
):
    return executor.approve_intent(
        intent_id=intent_id,
        approver_id=user.user_id,
        approver_role=user.role,
        approver_scopes=user.allowed_scopes,
        req=req
    )


@app.post("/api/v1/actions/{intent_id}/execute", response_model=ExecutionReceipt)
def execute_action_intent(
    intent_id: str,
    user: UserCredential = Depends(authenticate_bearer_token),
    executor: ActionExecutor = Depends(get_action_executor)
):
    return executor.execute_intent(
        intent_id=intent_id,
        caller_id=user.user_id,
        caller_role=user.role,
        caller_scopes=user.allowed_scopes
    )


@app.get("/api/v1/actions/{intent_id}/receipt", response_model=ExecutionReceipt)
def get_execution_receipt(
    intent_id: str,
    user: UserCredential = Depends(authenticate_bearer_token),
    executor: ActionExecutor = Depends(get_action_executor)
):
    receipt = executor.storage.get_execution_receipt(intent_id)
    if not receipt:
        raise HTTPException(status_code=404, detail=f"No execution receipt found for intent '{intent_id}'")
    intent = executor.storage.get_intent(intent_id)
    if intent:
        authorize_scope_access(user, intent.scope_id)
    return receipt

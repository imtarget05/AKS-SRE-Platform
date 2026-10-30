"""Data models for the platform-owned read-only SRE incident workflow.

All models are passive data carriers. The workflow is read-only by design: no
model carries write intent, credentials, or shell execution capability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class TriageVerdict(Enum):
    SEV1_CRITICAL = "SEV1_CRITICAL"
    SEV2_HIGH = "SEV2_HIGH"
    SEV3_MEDIUM = "SEV3_MEDIUM"
    SEV4_LOW = "SEV4_LOW"
    INFO = "INFO"
    ABSTAIN = "ABSTAIN"


@dataclass(frozen=True)
class AlertEvidence:
    alert_name: str
    severity: str
    service: str
    namespace: str
    cluster: str
    context: str
    observed_at: str
    state: str
    active_at: str | None
    receivers: list[str]
    source_sha: str
    evidence_hash: str


@dataclass(frozen=True)
class WorkloadStatus:
    name: str
    namespace: str
    replicas: int
    ready_replicas: int
    image: str
    digest: str | None
    phase: str
    conditions: list[str]


@dataclass(frozen=True)
class RunbookRef:
    runbook_id: str
    title: str
    namespace_target: str
    section: str
    revision: str
    url: str


@dataclass(frozen=True)
class DiagnosisResult:
    summary: str
    recent_deployment_correlation: str | None
    plausible_causes: list[str]
    uncertainty: str
    missing_signals: list[str]
    correlation_is_not_causation: bool


@dataclass(frozen=True)
class CriticVerdict:
    citations_required: bool
    runbook_target_verified: bool
    namespace_verified: bool
    actions_blocked: bool
    blocking_reasons: str


@dataclass(frozen=True)
class IncidentBrief:
    incident_id: str
    alert_evidence: AlertEvidence
    triage_verdict: TriageVerdict
    diagnosis: DiagnosisResult
    critic_verdict: CriticVerdict
    critic_brief: str
    read_only_checks: list[str]
    is_read_only: bool = True
    completed_at: str = field(default_factory=utc_now)

"""Platform-owned read-only SRE incident agent (MVP).

Three sequential read-only roles: Alert Triage -> Diagnostics -> Incident
Critic/Brief. Independent of apps/agent-hub. No kubectl write, Argo mutation,
Terraform, or secret access. Feature-flag gated; offline default (deterministic,
no LLM, no network).
"""

from .adapters import (
    AlertmanagerAdapter,
    ArgoAdapter,
    KubectlAdapter,
    PrometheusAdapter,
    ReadOnlyAdapterError,
    RunbookAdapter,
)
from .models import (
    AlertEvidence,
    CriticVerdict,
    DiagnosisResult,
    IncidentBrief,
    RunbookRef,
    TriageVerdict,
    WorkloadStatus,
)
from .workflow import SREIncidentWorkflow

__all__ = [
    "AlertmanagerAdapter",
    "ArgoAdapter",
    "KubectlAdapter",
    "PrometheusAdapter",
    "ReadOnlyAdapterError",
    "RunbookAdapter",
    "AlertEvidence",
    "CriticVerdict",
    "DiagnosisResult",
    "IncidentBrief",
    "RunbookRef",
    "TriageVerdict",
    "WorkloadStatus",
    "SREIncidentWorkflow",
]

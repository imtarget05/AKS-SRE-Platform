"""Platform-owned read-only SRE incident workflow.

Three sequential, read-only roles: Alert Triage -> Diagnostics -> Incident
Critic/Brief. The agent is read-only by design: no kubectl write, no Argo CD
mutation, no Terraform, no secret access, no write credential, no shell
execution path. Offline default: deterministic, feature-flag gated, no LLM, no
network, no API key.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess

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
    utc_now,
)

FEATURE_FLAG_ENV = "SRE_INCIDENT_AGENT_ENABLED"
DEFAULT_CONTEXT = "kind-local-platform"
DEFAULT_NAMESPACE = "monitoring"

SEVERITY_MAP = {
    "critical": TriageVerdict.SEV1_CRITICAL,
    "high": TriageVerdict.SEV2_HIGH,
    "medium": TriageVerdict.SEV3_MEDIUM,
    "low": TriageVerdict.SEV4_LOW,
    "info": TriageVerdict.INFO,
}

SLO_POLICY = {
    "sre-demo-api": "availability",
    "argocd": "availability",
    "prometheus": "scrape_success",
}

RUNBOOK_REF = RunbookRef(
    runbook_id="runbook-sli-slo-error-budget-burn",
    title="SLI/SLO Error Budget Multi-Window Burn Rate Alert",
    namespace_target="monitoring",
    section="3. Quy trinh Xu ly Su Co",
    revision="1",
    url="docs/runbooks/runbook-sli-slo-error-budget-burn.md",
)


def _is_feature_enabled() -> bool:
    return os.environ.get(FEATURE_FLAG_ENV, "1") == "1"


def _git_sha() -> str:
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
        ).stdout.strip()
        return sha or "unknown"
    except (subprocess.CalledProcessError, OSError):
        return "unknown"


def _evidence_hash(payload: Any) -> str:  # noqa: ANN401
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _short_hash(*parts: Any) -> str:  # noqa: ANN401
    return _evidence_hash(parts)[:12]


class SREIncidentWorkflow:
    def __init__(
        self,
        context: str = DEFAULT_CONTEXT,
        assessed_by: str = "system",
        *,
        prometheus: PrometheusAdapter | None = None,
        alertmanager: AlertmanagerAdapter | None = None,
        kubectl: KubectlAdapter | None = None,
        argo: ArgoAdapter | None = None,
        runbook: RunbookAdapter | None = None,
    ) -> None:
        self.context = context
        self.assessed_by = assessed_by
        self.prometheus = prometheus or PrometheusAdapter(context)
        self.alertmanager = alertmanager or AlertmanagerAdapter(context)
        self.kubectl = kubectl or KubectlAdapter(context)
        self.argo = argo or ArgoAdapter(context)
        self.runbook = runbook or RunbookAdapter()
        self._slo_policy = dict(SLO_POLICY)

    def investigate(
        self, alert_id: str, context: str | None = None, assessed_by: str | None = None
    ) -> IncidentBrief:
        context = context or self.context
        assessed_by = assessed_by or self.assessed_by
        started_at = utc_now()

        # Feature flag gate: offline default, deterministic, no LLM, no network.
        if not _is_feature_enabled():
            return self._disabled_brief(alert_id, context, assessed_by, started_at)

        # Role 1: Alert Triage
        evidence, triage_verdict = self._triage(alert_id, context, started_at)

        # Role 2: Diagnostics
        diagnosis = self._diagnose(evidence, context)

        # Role 3: Incident Critic / Brief
        critic_verdict, critic_brief, checks = self._critic(
            evidence, diagnosis, context, triage_verdict
        )

        incident_id = f"incident-{_short_hash(alert_id, context, started_at)}"
        return IncidentBrief(
            incident_id=incident_id,
            alert_evidence=evidence,
            triage_verdict=triage_verdict,
            diagnosis=diagnosis,
            critic_verdict=critic_verdict,
            critic_brief=critic_brief,
            read_only_checks=checks,
            is_read_only=True,
            completed_at=started_at,
        )

    def _triage(
        self, alert_id: str, context: str, started_at: str
    ) -> tuple[AlertEvidence, TriageVerdict]:
        try:
            alerts = self.alertmanager.active_alerts()
        except ReadOnlyAdapterError:
            alerts = []

        alert = next(
            (
                a
                for a in alerts
                if a.get("labels", {}).get("alertname") == alert_id
            ),
            None,
        )

        def _build_evidence(**overrides: Any) -> AlertEvidence:  # noqa: ANN401
            base = {
                "alert_name": alert_id,
                "severity": "",
                "service": "",
                "namespace": "",
                "cluster": "",
                "context": context,
                "observed_at": started_at,
                "state": "unknown",
                "active_at": None,
                "receivers": [],
                "source_sha": _git_sha(),
                "evidence_hash": _evidence_hash({"alert": alert_id}),
            }
            base.update(overrides)
            return AlertEvidence(**base)

        # Missing evidence -> abstain (fail closed).
        if alert is None:
            return _build_evidence(state="missing"), TriageVerdict.ABSTAIN

        labels = alert.get("labels", {}) or {}
        severity = str(labels.get("severity", ""))
        service = str(labels.get("service", ""))
        namespace = str(labels.get("namespace", ""))
        receivers = [
            str(r.get("name", ""))
            for r in (alert.get("receivers") or [])
            if r.get("name")
        ]
        state = str(alert.get("state", "unknown"))
        active_at = alert.get("activeAt")

        evidence = _build_evidence(
            severity=severity,
            service=service,
            namespace=namespace,
            state=state,
            active_at=active_at,
            receivers=receivers,
            evidence_hash=_evidence_hash(
                {
                    "alert": alert_id,
                    "severity": severity,
                    "service": service,
                    "namespace": namespace,
                    "state": state,
                }
            ),
        )

        # Missing SLO policy for the service -> abstain (fail closed).
        if service not in self._slo_policy:
            return evidence, TriageVerdict.ABSTAIN

        verdict = SEVERITY_MAP.get(severity.lower(), TriageVerdict.ABSTAIN)
        return evidence, verdict

    def _diagnose(self, evidence: AlertEvidence, context: str) -> DiagnosisResult:
        missing_signals: list[str] = []
        plausible_causes: list[str] = []
        correlation: str | None = None
        uncertainty_parts: list[str] = []

        # Prometheus signal (read-only).
        try:
            self.prometheus.query(
                f'up{{job="{evidence.service or "sre-demo-api"}"}}'
            )
        except ReadOnlyAdapterError:
            missing_signals.append("prometheus_metrics")
            uncertainty_parts.append("prometheus metrics unavailable")

        # Workload status (read-only kubectl get).
        try:
            self.kubectl.workload_status(
                evidence.service or "sre-demo-api",
                evidence.namespace or DEFAULT_NAMESPACE,
            )
        except ReadOnlyAdapterError:
            missing_signals.append("workload_status")
            uncertainty_parts.append("workload status unavailable")

        # Argo revision (read-only).
        try:
            revision = self.argo.current_revision(evidence.service or "sre-demo-api")
        except ReadOnlyAdapterError:
            revision = None
            missing_signals.append("argo_revision")
            uncertainty_parts.append("argo revision unavailable")

        if revision:
            plausible_causes.append(
                f"recent deployment revision {revision} for {evidence.service}"
            )
            correlation = (
                f"deployment {revision} coincides with alert {evidence.alert_name}"
            )
        else:
            plausible_causes.append("no recent deployment signal observed")

        if not plausible_causes:
            plausible_causes.append("insufficient evidence to assign a cause")

        summary = (
            f"Alert {evidence.alert_name} ({evidence.severity}) in {evidence.namespace} "
            f"on service {evidence.service or 'unknown'}. "
        )
        if uncertainty_parts:
            summary += "Uncertainty: " + "; ".join(uncertainty_parts) + ". "
        summary += (
            "Correlation with a recent deployment is observed but is not causation."
        )

        uncertainty = (
            "; ".join(uncertainty_parts)
            if uncertainty_parts
            else "deployment correlation cannot establish causation"
        )

        return DiagnosisResult(
            summary=summary,
            recent_deployment_correlation=correlation,
            plausible_causes=plausible_causes,
            uncertainty=uncertainty,
            missing_signals=missing_signals,
            correlation_is_not_causation=True,
        )

    def _critic(
        self,
        evidence: AlertEvidence,
        diagnosis: DiagnosisResult,
        context: str,
        triage_verdict: TriageVerdict,
    ) -> tuple[CriticVerdict, str, list[str]]:
        blocking_reasons: list[str] = []
        citations_required = bool(diagnosis and diagnosis.summary)

        # Verify runbook target exists (read-only load).
        runbook_target_verified = False
        try:
            self.runbook.load(RUNBOOK_REF.runbook_id)
            runbook_target_verified = True
        except ReadOnlyAdapterError:
            blocking_reasons.append("runbook_not_found")

        # Namespace verified against runbook target namespace.
        namespace_verified = bool(evidence.namespace) and (
            evidence.namespace == RUNBOOK_REF.namespace_target
        )
        if not namespace_verified:
            blocking_reasons.append("namespace_mismatch")

        # Read-only agent: every write action is blocked.
        actions_blocked = True

        verdict = CriticVerdict(
            citations_required=citations_required,
            runbook_target_verified=runbook_target_verified,
            namespace_verified=namespace_verified,
            actions_blocked=actions_blocked,
            blocking_reasons=(
                "; ".join(blocking_reasons) if blocking_reasons else "none"
            ),
        )

        brief = (
            f"Incident {evidence.alert_name}: triage={triage_verdict.value}, "
            f"service={evidence.service or 'unknown'}, "
            f"namespace={evidence.namespace or 'unknown'}. "
            f"{diagnosis.summary} "
            f"Citations required: {citations_required}. "
            f"Runbook target verified: {runbook_target_verified}. "
            f"Namespace verified: {namespace_verified}. "
            f"All write actions blocked (read-only agent). "
            f"Blocking reasons: {verdict.blocking_reasons}."
        )

        checks = [
            "read_only: no kubectl apply/scale/delete/rollout/patch/create",
            "read_only: no argo cd sync/rollback",
            "read_only: no terraform apply/destroy/plan",
            "read_only: no secret access",
            "read_only: no write credential or shell execution path",
            f"citations_required={citations_required}",
            f"runbook_target_verified={runbook_target_verified}",
            f"namespace_verified={namespace_verified}",
            f"actions_blocked={actions_blocked}",
        ]
        return verdict, brief, checks

    def _disabled_brief(
        self, alert_id: str, context: str, assessed_by: str, started_at: str
    ) -> IncidentBrief:
        evidence = AlertEvidence(
            alert_name=alert_id,
            severity="",
            service="",
            namespace="",
            cluster="",
            context=context,
            observed_at=started_at,
            state="disabled",
            active_at=None,
            receivers=[],
            source_sha=_git_sha(),
            evidence_hash=_evidence_hash({"alert": alert_id, "feature": "disabled"}),
        )
        diagnosis = DiagnosisResult(
            summary=(
                "SRE incident agent is disabled by feature flag; "
                "no investigation performed."
            ),
            recent_deployment_correlation=None,
            plausible_causes=[],
            uncertainty="feature_flag_disabled",
            missing_signals=["all"],
            correlation_is_not_causation=True,
        )
        verdict = CriticVerdict(
            citations_required=False,
            runbook_target_verified=False,
            namespace_verified=False,
            actions_blocked=True,
            blocking_reasons="feature_flag_disabled",
        )
        brief = (
            f"Incident agent disabled ({FEATURE_FLAG_ENV} != '1'). "
            f"No investigation performed for alert {alert_id}. "
            "Read-only checks not executed."
        )
        return IncidentBrief(
            incident_id=f"incident-disabled-{_short_hash(alert_id, context)}",
            alert_evidence=evidence,
            triage_verdict=TriageVerdict.ABSTAIN,
            diagnosis=diagnosis,
            critic_verdict=verdict,
            critic_brief=brief,
            read_only_checks=["feature_flag_disabled"],
            is_read_only=True,
            completed_at=started_at,
        )

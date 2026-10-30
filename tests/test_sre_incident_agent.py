"""Unit tests for the platform-owned read-only SRE incident agent."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from app.sre_incident_agent.adapters import ReadOnlyAdapterError
from app.sre_incident_agent.models import TriageVerdict
from app.sre_incident_agent.workflow import (
    FEATURE_FLAG_ENV,
    SREIncidentWorkflow,
    _is_feature_enabled,
)

HERE = Path(__file__).resolve().parent
REPO = HERE.parent


class _FakePrometheus:
    def __init__(self, result=None, fail=False):
        self.result = result or {
            "status": "success",
            "data": {"result": []},
        }
        self.fail = fail

    def query(self, metric):
        if self.fail:
            raise ReadOnlyAdapterError("prometheus unavailable")
        return self.result

    def rules(self):
        if self.fail:
            raise ReadOnlyAdapterError("prometheus unavailable")
        return {"status": "success", "data": {"groups": []}}


class _FakeAlertmanager:
    def __init__(self, alerts=None, fail=False):
        self.alerts = alerts or []
        self.fail = fail

    def active_alerts(self):
        if self.fail:
            raise ReadOnlyAdapterError("alertmanager unavailable")
        return self.alerts


class _FakeKubectl:
    def __init__(self, workload=None, fail=False):
        self.workload = workload
        self.fail = fail

    def workload_status(self, name, namespace):
        if self.fail:
            raise ReadOnlyAdapterError("kubectl unavailable")
        return self.workload


class _FakeArgo:
    def __init__(self, revision="abc123def456", fail=False):
        self.revision = revision
        self.fail = fail

    def current_revision(self, app_name):
        if self.fail:
            raise ReadOnlyAdapterError("argo unavailable")
        return self.revision


class _FakeRunbook:
    def __init__(self, content="# Runbook\n", fail=False):
        self.content = content
        self.fail = fail

    def load(self, runbook_id):
        if self.fail:
            raise ReadOnlyAdapterError("runbook unavailable")
        return self.content


def _make_alert(labels, receivers=None, state="firing", active_at="2026-10-30T00:00:00Z"):
    return {
        "labels": labels,
        "state": state,
        "activeAt": active_at,
        "receivers": [{"name": r} for r in (receivers or [])],
    }


class TriageTests:
    def setup_method(self):
        os.environ[FEATURE_FLAG_ENV] = "1"

    def test_sev1_for_critical_alert(self):
        am = _FakeAlertmanager(
            [
                _make_alert(
                    {
                        "alertname": "CrashLoop",
                        "severity": "critical",
                        "service": "sre-demo-api",
                        "namespace": "monitoring",
                    },
                    receivers=["sre-oncall"],
                )
            ]
        )
        wf = SREIncidentWorkflow(context="kind-local-platform", alertmanager=am)
        brief = wf.investigate(
            "CrashLoop", context="kind-local-platform", assessed_by="sre"
        )
        assert brief.triage_verdict is TriageVerdict.SEV1_CRITICAL
        assert brief.is_read_only is True
        assert brief.alert_evidence.receivers == ["sre-oncall"]

    def test_sev2_for_high_alert(self):
        am = _FakeAlertmanager(
            [
                _make_alert(
                    {
                        "alertname": "HighLatency",
                        "severity": "high",
                        "service": "sre-demo-api",
                        "namespace": "monitoring",
                    }
                )
            ]
        )
        wf = SREIncidentWorkflow(context="kind-local-platform", alertmanager=am)
        brief = wf.investigate("HighLatency")
        assert brief.triage_verdict is TriageVerdict.SEV2_HIGH
        assert brief.is_read_only is True

    def test_sev3_for_medium_alert(self):
        am = _FakeAlertmanager(
            [
                _make_alert(
                    {
                        "alertname": "MedLatency",
                        "severity": "medium",
                        "service": "sre-demo-api",
                        "namespace": "monitoring",
                    }
                )
            ]
        )
        wf = SREIncidentWorkflow(context="kind-local-platform", alertmanager=am)
        brief = wf.investigate("MedLatency")
        assert brief.triage_verdict is TriageVerdict.SEV3_MEDIUM
        assert brief.is_read_only is True

    def test_abstain_for_missing_evidence(self):
        am = _FakeAlertmanager([])
        wf = SREIncidentWorkflow(context="kind-local-platform", alertmanager=am)
        brief = wf.investigate("NoSuchAlert")
        assert brief.triage_verdict is TriageVerdict.ABSTAIN
        assert brief.is_read_only is True

    def test_abstain_for_missing_slo(self):
        am = _FakeAlertmanager(
            [
                _make_alert(
                    {
                        "alertname": "X",
                        "severity": "critical",
                        "service": "unknown-svc",
                        "namespace": "monitoring",
                    }
                )
            ]
        )
        wf = SREIncidentWorkflow(context="kind-local-platform", alertmanager=am)
        brief = wf.investigate("X")
        assert brief.triage_verdict is TriageVerdict.ABSTAIN
        assert brief.is_read_only is True


class DiagnosisTests:
    def setup_method(self):
        os.environ[FEATURE_FLAG_ENV] = "1"

    def test_correlation_is_not_causation(self):
        am = _FakeAlertmanager(
            [
                _make_alert(
                    {
                        "alertname": "X",
                        "severity": "high",
                        "service": "sre-demo-api",
                        "namespace": "monitoring",
                    }
                )
            ]
        )
        wf = SREIncidentWorkflow(
            context="kind-local-platform",
            alertmanager=am,
            kubectl=_FakeKubectl(),
            argo=_FakeArgo(),
            runbook=_FakeRunbook(),
        )
        brief = wf.investigate("X")
        assert brief.diagnosis.correlation_is_not_causation is True
        assert brief.is_read_only is True


class CriticTests:
    def setup_method(self):
        os.environ[FEATURE_FLAG_ENV] = "1"

    def test_blocks_actions_requires_citations_verifies_namespace(self):
        am = _FakeAlertmanager(
            [
                _make_alert(
                    {
                        "alertname": "X",
                        "severity": "high",
                        "service": "sre-demo-api",
                        "namespace": "monitoring",
                    }
                )
            ]
        )
        wf = SREIncidentWorkflow(
            context="kind-local-platform",
            alertmanager=am,
            runbook=_FakeRunbook(),
        )
        brief = wf.investigate("X")
        cv = brief.critic_verdict
        assert cv.actions_blocked is True
        assert cv.citations_required is True
        assert cv.namespace_verified is True
        assert brief.is_read_only is True


class ReadOnlyTests:
    def test_is_read_only_true_for_all_results(self):
        os.environ[FEATURE_FLAG_ENV] = "1"
        am = _FakeAlertmanager(
            [
                _make_alert(
                    {
                        "alertname": "X",
                        "severity": "info",
                        "service": "sre-demo-api",
                        "namespace": "monitoring",
                    }
                )
            ]
        )
        wf = SREIncidentWorkflow(context="kind-local-platform", alertmanager=am)
        brief = wf.investigate("X")
        assert brief.is_read_only is True

        os.environ[FEATURE_FLAG_ENV] = "0"
        brief2 = wf.investigate("X")
        assert brief2.is_read_only is True

    def test_no_write_tools_in_source(self):
        forbidden = [
            "kubectl apply",
            "kubectl scale",
            "kubectl delete",
            "kubectl rollout",
            "kubectl patch",
            "kubectl replace",
            "kubectl create",
            "argocd sync",
            "argocd rollout",
            "argo rollout",
            "terraform apply",
            "terraform destroy",
            "terraform plan",
        ]
        pkg = REPO / "app" / "sre_incident_agent"
        for path in pkg.glob("*.py"):
            text = path.read_text().lower()
            for token in forbidden:
                assert token not in text, (
                    f"forbidden write token {token!r} in {path.name}"
                )


class FeatureFlagTests:
    def test_disabled_returns_disabled_result(self):
        with patch.dict(os.environ, {FEATURE_FLAG_ENV: "0"}, clear=False):
            am = _FakeAlertmanager(
                [
                    _make_alert(
                        {
                            "alertname": "X",
                            "severity": "critical",
                            "service": "sre-demo-api",
                            "namespace": "monitoring",
                        }
                    )
                ]
            )
            wf = SREIncidentWorkflow(context="kind-local-platform", alertmanager=am)
            brief = wf.investigate("X")
            assert _is_feature_enabled() is False
            assert brief.triage_verdict is TriageVerdict.ABSTAIN
            assert brief.is_read_only is True
            assert "disabled" in brief.critic_brief.lower()


class CliTests:
    def test_cli_writes_json_evidence_file(self, tmp_path):
        os.environ[FEATURE_FLAG_ENV] = "1"
        am = _FakeAlertmanager(
            [
                _make_alert(
                    {
                        "alertname": "CrashLoop",
                        "severity": "critical",
                        "service": "sre-demo-api",
                        "namespace": "monitoring",
                    },
                    receivers=["sre-oncall"],
                )
            ]
        )
        out = tmp_path / "evidence.json"
        from app.sre_incident_agent.cli import main

        argv = [
            "--alert", "CrashLoop",
            "--context", "kind-local-platform",
            "--output", str(out),
            "--assessed-by", "sre",
        ]
        rc = main(argv)
        assert rc == 0
        assert out.is_file()
        data = json.loads(out.read_text())
        assert data["is_read_only"] is True
        assert data["triage_verdict"] == "SEV1_CRITICAL"
        assert data["notification_delivery_verified"] is True
        assert data["critic_verdict"]["actions_blocked"] is True
        assert data["critic_verdict"]["citations_required"] is True

    def test_cli_notification_verified_false_without_receivers(self, tmp_path):
        os.environ[FEATURE_FLAG_ENV] = "1"
        am = _FakeAlertmanager(
            [
                _make_alert(
                    {
                        "alertname": "X",
                        "severity": "high",
                        "service": "sre-demo-api",
                        "namespace": "monitoring",
                    },
                    receivers=[],
                )
            ]
        )
        out = tmp_path / "evidence2.json"
        from app.sre_incident_agent.cli import main

        rc = main(
            [
                "--alert", "X",
                "--context", "kind-local-platform",
                "--output", str(out),
            ]
        )
        assert rc == 0
        data = json.loads(out.read_text())
        assert data["notification_delivery_verified"] is False

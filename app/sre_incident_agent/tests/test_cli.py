"""Tests for CLI entry point of the SRE incident agent."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.sre_incident_agent.cli import build_parser, main


def test_build_parser_has_required_arguments():
    parser = build_parser()
    # --alert is required
    with pytest.raises(SystemExit):
        parser.parse_args([])
    # --output is required
    with pytest.raises(SystemExit):
        parser.parse_args(["--alert", "test-alert"])
    # All required args present
    args = parser.parse_args(["--alert", "test-alert", "--output", "/tmp/out.json"])
    assert args.alert == "test-alert"
    assert args.output == Path("/tmp/out.json")
    assert args.context == "kind-local-platform"
    assert args.assessed_by == "operator"


def test_build_parser_defaults():
    parser = build_parser()
    args = parser.parse_args(["--alert", "alert-1", "--output", "/tmp/out.json"])
    assert args.context == "kind-local-platform"
    assert args.assessed_by == "operator"


def test_build_parser_custom_values():
    parser = build_parser()
    args = parser.parse_args(
        ["--alert", "alert-1", "--context", "prod-cluster", "--output", "/tmp/out.json", "--assessed-by", "alice"]
    )
    assert args.context == "prod-cluster"
    assert args.assessed_by == "alice"


def test_main_writes_evidence_file(tmp_path):
    output_path = tmp_path / "evidence.json"
    from dataclasses import asdict
    from app.sre_incident_agent.models import (
        AlertEvidence,
        CriticVerdict,
        DiagnosisResult,
        IncidentBrief,
        TriageVerdict,
    )
    from datetime import UTC, datetime

    real_brief = IncidentBrief(
        incident_id="incident-123",
        alert_evidence=AlertEvidence(
            alert_name="test-alert",
            severity="high",
            service="sre-demo-api",
            namespace="monitoring",
            cluster="kind-local-platform",
            context="kind-local-platform",
            observed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            state="active",
            active_at=None,
            receivers=["ops@example.com"],
            source_sha="abc123",
            evidence_hash="def456",
        ),
        triage_verdict=TriageVerdict.SEV2_HIGH,
        diagnosis=DiagnosisResult(
            summary="Test diagnosis",
            recent_deployment_correlation=None,
            plausible_causes=[],
            uncertainty="test",
            missing_signals=[],
            correlation_is_not_causation=True,
        ),
        critic_verdict=CriticVerdict(
            citations_required=False,
            runbook_target_verified=True,
            namespace_verified=True,
            actions_blocked=True,
            blocking_reasons="none",
        ),
        critic_brief="Test brief",
        read_only_checks=["read_only: cluster mutation commands unavailable"],
        is_read_only=True,
        completed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )

    with patch("app.sre_incident_agent.cli.SREIncidentWorkflow") as mock_wf_class:
        mock_instance = MagicMock()
        mock_instance.investigate.return_value = real_brief
        mock_wf_class.return_value = mock_instance

        exit_code = main(["--alert", "test-alert", "--output", str(output_path)])

    assert exit_code == 0
    assert output_path.exists()
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["incident_id"] == "incident-123"
    assert data["triage_verdict"] == "SEV2_HIGH"
    assert data["is_read_only"] is True


def test_main_returns_zero_on_success(tmp_path):
    output_path = tmp_path / "evidence.json"
    from dataclasses import asdict
    from app.sre_incident_agent.models import (
        AlertEvidence,
        CriticVerdict,
        DiagnosisResult,
        IncidentBrief,
        TriageVerdict,
    )
    from datetime import UTC, datetime

    real_brief = IncidentBrief(
        incident_id="incident-456",
        alert_evidence=AlertEvidence(
            alert_name="test-alert",
            severity="low",
            service="argocd",
            namespace="monitoring",
            cluster="kind-local-platform",
            context="kind-local-platform",
            observed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            state="active",
            active_at=None,
            receivers=["ops@example.com"],
            source_sha="abc123",
            evidence_hash="def456",
        ),
        triage_verdict=TriageVerdict.SEV4_LOW,
        diagnosis=DiagnosisResult(
            summary="Low severity",
            recent_deployment_correlation=None,
            plausible_causes=[],
            uncertainty="test",
            missing_signals=[],
            correlation_is_not_causation=True,
        ),
        critic_verdict=CriticVerdict(
            citations_required=True,
            runbook_target_verified=False,
            namespace_verified=True,
            actions_blocked=True,
            blocking_reasons="runbook_target not verified",
        ),
        critic_brief="Test brief",
        read_only_checks=["read_only: no secret access"],
        is_read_only=True,
        completed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )

    with patch("app.sre_incident_agent.cli.SREIncidentWorkflow") as mock_wf_class:
        mock_instance = MagicMock()
        mock_instance.investigate.return_value = real_brief
        mock_wf_class.return_value = mock_instance

        exit_code = main(["--alert", "alert-456", "--output", str(output_path)])

    assert exit_code == 0
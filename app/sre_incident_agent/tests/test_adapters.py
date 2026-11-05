"""Tests for validation and adapter input sanitization."""

from __future__ import annotations

import json
import types
from pathlib import Path
from unittest import mock

import pytest

import app.sre_incident_agent.adapters as adapters_mod
from app.sre_incident_agent.validation import (
    validate_dns_label,
    validate_namespace,
    ensure_double_dash,
    encode_promql,
)
from app.sre_incident_agent.adapters import (
    AlertmanagerAdapter,
    ArgoAdapter,
    KubectlAdapter,
    PrometheusAdapter,
    RunbookAdapter,
)


def test_validate_dns_label_accepts_valid():
    assert validate_dns_label("monitoring") == "monitoring"
    assert validate_dns_label("sre-demo-api") == "sre-demo-api"
    assert validate_dns_label("a-b-c") == "a-b-c"


def test_validate_dns_label_rejects_injection():
    for bad in ["--kubeconfig=/etc/...", "foo/bar", "..", "a" * 64, "UpperCase", "has space", "a--b"]:
        with pytest.raises(ValueError):
            validate_dns_label(bad)


def test_validate_dns_label_rejects_non_string():
    with pytest.raises(ValueError, match="must be a string"):
        validate_dns_label(123)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must be a string"):
        validate_dns_label(None)  # type: ignore[arg-type]


def test_validate_dns_label_rejects_empty():
    with pytest.raises(ValueError, match="must not be empty"):
        validate_dns_label("")


def test_validate_namespace_allowlist():
    assert validate_namespace("monitoring") == "monitoring"
    assert validate_namespace("flashsale") == "flashsale"
    assert validate_namespace("kube-system") == "kube-system"
    for bad in ["kube-public", "default", "evil"]:
        with pytest.raises(ValueError):
            validate_namespace(bad)


def test_validate_namespace_rejects_non_string():
    with pytest.raises(ValueError, match="must be a string"):
        validate_namespace(42)  # type: ignore[arg-type]


def test_ensure_double_dash():
    assert ensure_double_dash(["kubectl", "get"]) == ["kubectl", "--", "get"]
    assert ensure_double_dash(["kubectl", "--", "get"]) == ["kubectl", "--", "get"]


def test_encode_promql():
    encoded = encode_promql('up{job="kubelet"} == 1')
    assert "{" not in encoded
    assert "}" not in encoded
    assert '"' not in encoded
    assert "=" not in encoded


def test_kubectl_adapter_blocks_malicious_namespace():
    adapter = KubectlAdapter(context="kind-local-platform")
    with pytest.raises(ValueError):
        adapter.workload_status("sre-demo-api", "monitoring; rm -rf /")


def test_kubectl_adapter_blocks_malicious_name():
    adapter = KubectlAdapter(context="kind-local-platform")
    with pytest.raises(ValueError):
        adapter.workload_status("foo; cat /etc/passwd", "monitoring")


# --- Runtime paths (subprocess mocked) ------------------------------------


def _fake_run(stdout: str = "", returncode: int = 0, stderr: str = ""):
    """Build a subprocess.run stub returning a completed process."""

    def _run(*args, **kwargs):
        return types.SimpleNamespace(
            stdout=stdout, stderr=stderr, returncode=returncode
        )

    return _run


def test_kubectl_raw_parses_json():
    with mock.patch.object(
        adapters_mod.subprocess, "run", _fake_run(stdout='{"status": "ok"}')
    ):
        assert adapters_mod._kubectl_raw(
            "ctx", "/api/v1/namespaces/monitoring/services/x/proxy"
        ) == {"status": "ok"}


def test_kubectl_raw_raises_on_nonzero_exit():
    with mock.patch.object(
        adapters_mod.subprocess,
        "run",
        _fake_run(returncode=1, stderr="connection refused"),
    ):
        with pytest.raises(adapters_mod.ReadOnlyAdapterError, match="exit 1"):
            adapters_mod._kubectl_raw("ctx", "/proxy/path")


def test_kubectl_raw_raises_on_invalid_json():
    with mock.patch.object(
        adapters_mod.subprocess, "run", _fake_run(stdout="not json {")
    ):
        with pytest.raises(adapters_mod.ReadOnlyAdapterError, match="invalid JSON"):
            adapters_mod._kubectl_raw("ctx", "/proxy/path")


def test_prometheus_adapter_query_builds_proxy_path():
    captured: dict[str, object] = {}

    def _run(argv, **kwargs):
        captured["argv"] = argv
        return types.SimpleNamespace(
            stdout='{"status": "success", "data": {"result": []}}',
            stderr="",
            returncode=0,
        )

    with mock.patch.object(adapters_mod.subprocess, "run", _run):
        payload = PrometheusAdapter(context="ctx").query("up == 1")

    assert payload["status"] == "success"
    argv = captured["argv"]
    assert argv[:4] == ["kubectl", "--context", "ctx", "get"]
    raw = argv[-1]
    assert raw.startswith("/api/v1/namespaces/monitoring/services/")
    assert "api/v1/query?query=" in raw
    assert "=" not in raw.split("query=")[1]


def test_prometheus_adapter_rules_builds_proxy_path():
    def _run(argv, **kwargs):
        assert argv[-1].endswith("api/v1/rules?type=alert")
        return types.SimpleNamespace(
            stdout='{"data": {"groups": []}}', stderr="", returncode=0
        )

    with mock.patch.object(adapters_mod.subprocess, "run", _run):
        assert PrometheusAdapter(context="ctx").rules() == {"data": {"groups": []}}


def test_alertmanager_adapter_returns_active_alerts():
    def _run(argv, **kwargs):
        assert "api/v2/alerts?active=true" in argv[-1]
        return types.SimpleNamespace(
            stdout='[{"labels": {"alertname": "KubeDeploymentReplicasMismatch"}}]',
            stderr="",
            returncode=0,
        )

    with mock.patch.object(adapters_mod.subprocess, "run", _run):
        adapter = AlertmanagerAdapter(context="ctx")
        alerts = adapter.active_alerts()
    assert alerts[0]["labels"]["alertname"] == "KubeDeploymentReplicasMismatch"


def test_alertmanager_adapter_rejects_non_array_payload():
    with mock.patch.object(
        adapters_mod.subprocess, "run", _fake_run(stdout='{"error": "no"}')
    ):
        with pytest.raises(
            adapters_mod.ReadOnlyAdapterError, match="did not return an array"
        ):
            AlertmanagerAdapter(context="ctx").active_alerts()


def test_kubectl_adapter_workload_status_parses_deployment():
    def _run(argv, **kwargs):
        assert argv[:5] == ["kubectl", "--context", "ctx", "--", "get"]
        assert "-o" in argv and "json" in argv
        return types.SimpleNamespace(
            stdout=json.dumps(
                {
                    "metadata": {"name": "sre-demo-api", "namespace": "flashsale"},
                    "spec": {
                        "replicas": 3,
                        "template": {
                            "spec": {
                                "containers": [
                                    {
                                        "image": "registry/sre-demo-api"
                                        "@sha256:abc123"
                                    }
                                ]
                            }
                        },
                    },
                    "status": {
                        "readyReplicas": 2,
                        "phase": "Running",
                        "conditions": [{"type": "Available"}, {"type": "Progressing"}],
                    },
                }
            ),
            stderr="",
            returncode=0,
        )

    with mock.patch.object(adapters_mod.subprocess, "run", _run):
        status = KubectlAdapter(context="ctx").workload_status(
            "sre-demo-api", "flashsale"
        )

    assert status.name == "sre-demo-api"
    assert status.namespace == "flashsale"
    assert status.replicas == 3
    assert status.ready_replicas == 2
    assert status.image == "registry/sre-demo-api"
    assert status.digest == "sha256:abc123"
    assert status.phase == "Running"
    assert status.conditions == ["Available", "Progressing"]


def test_kubectl_adapter_workload_status_defaults_when_keys_missing():
    with mock.patch.object(
        adapters_mod.subprocess, "run", _fake_run(stdout='{"metadata": null}')
    ):
        status = KubectlAdapter(context="ctx").workload_status("api", "flashsale")

    assert status.name == "api"
    assert status.namespace == "flashsale"
    assert status.replicas == 0
    assert status.ready_replicas == 0
    assert status.image == ""
    assert status.digest is None
    assert status.phase == "Unknown"
    assert status.conditions == []


def test_kubectl_adapter_workload_status_raises_on_failure():
    with mock.patch.object(
        adapters_mod.subprocess,
        "run",
        _fake_run(returncode=1, stderr="no deployment found"),
    ):
        with pytest.raises(
            adapters_mod.ReadOnlyAdapterError, match=r"exit 1\): no deployment found"
        ):
            KubectlAdapter(context="ctx").workload_status("missing", "flashsale")


def test_kubectl_adapter_workload_status_raises_on_invalid_json():
    with mock.patch.object(
        adapters_mod.subprocess, "run", _fake_run(stdout="{ broken")
    ):
        with pytest.raises(
            adapters_mod.ReadOnlyAdapterError,
            match=r"kubectl returned invalid JSON",
        ):
            KubectlAdapter(context="ctx").workload_status("api", "flashsale")


def test_argo_adapter_current_revision():
    def _run(argv, **kwargs):
        assert argv[:4] == ["kubectl", "--context", "ctx", "get"]
        return types.SimpleNamespace(
            stdout=json.dumps(
                {"status": {"sync": {"revision": "abc123def456"}}}
            ),
            stderr="",
            returncode=0,
        )

    with mock.patch.object(adapters_mod.subprocess, "run", _run):
        revision = ArgoAdapter(context="ctx").current_revision("sre-demo-api")
    assert revision == "abc123def456"


def test_argo_adapter_current_revision_defaults_to_empty():
    with mock.patch.object(
        adapters_mod.subprocess, "run", _fake_run(stdout='{"status": {"sync": null}}')
    ):
        assert ArgoAdapter(context="ctx").current_revision("sre-demo-api") == ""


def test_argo_adapter_current_revision_raises_on_failure():
    with mock.patch.object(
        adapters_mod.subprocess,
        "run",
        _fake_run(returncode=2, stderr="not found"),
    ):
        with pytest.raises(
            adapters_mod.ReadOnlyAdapterError, match=r"exit 2\): not found"
        ):
            ArgoAdapter(context="ctx").current_revision("sre-demo-api")


def test_argo_adapter_current_revision_raises_on_invalid_json():
    with mock.patch.object(
        adapters_mod.subprocess, "run", _fake_run(stdout="]")
    ):
        with pytest.raises(
            adapters_mod.ReadOnlyAdapterError, match="kubectl returned invalid JSON"
        ):
            ArgoAdapter(context="ctx").current_revision("sre-demo-api")


def test_argo_adapter_rejects_malicious_app_name():
    adapter = ArgoAdapter(context="ctx")
    with pytest.raises(ValueError):
        adapter.current_revision("app; shutdown -h now")


def test_runbook_adapter_loads_markdown(tmp_path: Path):
    runbooks = tmp_path / "runbooks"
    runbooks.mkdir()
    (runbooks / "r-api-latency.md").write_text("## Runbook\nFirst step.", "utf-8")
    content = RunbookAdapter(runbooks_dir=runbooks).load("r-api-latency")
    assert content == "## Runbook\nFirst step."


def test_runbook_adapter_raises_when_missing(tmp_path: Path):
    with pytest.raises(adapters_mod.ReadOnlyAdapterError, match="Runbook not found"):
        RunbookAdapter(runbooks_dir=tmp_path).load("does-not-exist")

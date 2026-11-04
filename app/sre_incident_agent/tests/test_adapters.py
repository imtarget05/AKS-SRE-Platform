"""Tests for validation and adapter input sanitization."""

from __future__ import annotations

import pytest

from app.sre_incident_agent.validation import (
    validate_dns_label,
    validate_namespace,
    ensure_double_dash,
    encode_promql,
)
from app.sre_incident_agent.adapters import KubectlAdapter


def test_validate_dns_label_accepts_valid():
    assert validate_dns_label("monitoring") == "monitoring"
    assert validate_dns_label("sre-demo-api") == "sre-demo-api"
    assert validate_dns_label("a-b-c") == "a-b-c"


def test_validate_dns_label_rejects_injection():
    for bad in ["--kubeconfig=/etc/...", "foo/bar", "..", "a" * 64, "UpperCase", "has space", "a--b"]:
        with pytest.raises(ValueError):
            validate_dns_label(bad)


def test_validate_namespace_allowlist():
    assert validate_namespace("monitoring") == "monitoring"
    assert validate_namespace("flashsale") == "flashsale"
    assert validate_namespace("kube-system") == "kube-system"
    for bad in ["kube-public", "default", "evil"]:
        with pytest.raises(ValueError):
            validate_namespace(bad)


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

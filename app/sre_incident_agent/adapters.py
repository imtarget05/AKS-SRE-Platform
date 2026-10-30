"""Read-only adapters for the SRE incident workflow.

Every adapter is read-only: it issues GET/proxy queries only and raises on
failure (fail closed). No adapter performs kubectl apply/scale/delete/rollout/
patch/create, Argo CD sync/rollback, Terraform, or secret access.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .models import AlertEvidence, WorkloadStatus


class ReadOnlyAdapterError(RuntimeError):
    """Raised when a read-only adapter cannot guarantee a safe read."""


NAMESPACE = "monitoring"
PROMETHEUS_SERVICE = "http:kps-kube-prometheus-stack-prometheus:9090"
ALERTMANAGER_SERVICE = "http:kps-kube-prometheus-stack-alertmanager:9093"


def _kubectl_raw(context: str, proxy_path: str) -> Any:
    """Run a read-only kubectl --raw proxy GET and return parsed JSON."""
    result = subprocess.run(
        ["kubectl", "--context", context, "get", "--raw", proxy_path],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode:
        raise ReadOnlyAdapterError(
            f"kubectl read-only proxy failed (exit {result.returncode}): "
            f"{result.stderr.strip()}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ReadOnlyAdapterError(f"kubectl proxy returned invalid JSON: {error}")


class PrometheusAdapter:
    """Read-only Prometheus queries via kubectl proxy (Prometheus rules API)."""

    def __init__(self, context: str):
        self.context = context

    def query(self, metric: str) -> dict[str, Any]:
        proxy_path = (
            f"/api/v1/namespaces/{NAMESPACE}/services/{PROMETHEUS_SERVICE}/proxy/"
            f"api/v1/query?query={metric}"
        )
        return _kubectl_raw(self.context, proxy_path)

    def rules(self) -> dict[str, Any]:
        proxy_path = (
            f"/api/v1/namespaces/{NAMESPACE}/services/{PROMETHEUS_SERVICE}/proxy/"
            "api/v1/rules?type=alert"
        )
        return _kubectl_raw(self.context, proxy_path)


class AlertmanagerAdapter:
    """Read-only Alertmanager active alerts via kubectl proxy."""

    def __init__(self, context: str):
        self.context = context

    def active_alerts(self) -> list[dict[str, Any]]:
        proxy_path = (
            f"/api/v1/namespaces/{NAMESPACE}/services/{ALERTMANAGER_SERVICE}/proxy/"
            "api/v2/alerts?active=true"
        )
        payload = _kubectl_raw(self.context, proxy_path)
        if not isinstance(payload, list):
            raise ReadOnlyAdapterError(
                "Alertmanager alerts API did not return an array"
            )
        return payload


class KubectlAdapter:
    """Read-only kubectl get for workload status."""

    def __init__(self, context: str):
        self.context = context

    def workload_status(self, name: str, namespace: str) -> WorkloadStatus:
        result = subprocess.run(
            [
                "kubectl", "--context", self.context, "get", "deployment", name,
                "-n", namespace, "-o", "json",
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if result.returncode:
            raise ReadOnlyAdapterError(
                f"kubectl get deployment failed (exit {result.returncode}): "
                f"{result.stderr.strip()}"
            )
        try:
            obj = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise ReadOnlyAdapterError(f"kubectl returned invalid JSON: {error}")
        metadata = obj.get("metadata", {}) or {}
        spec = obj.get("spec", {}) or {}
        status = obj.get("status", {}) or {}
        containers = (
            spec.get("template", {}).get("spec", {}).get("containers", []) or []
        )
        image = containers[0].get("image", "") if containers else ""
        digest = None
        if "@" in image:
            image, _, digest = image.partition("@")
        return WorkloadStatus(
            name=metadata.get("name", name),
            namespace=metadata.get("namespace", namespace),
            replicas=spec.get("replicas", 0),
            ready_replicas=status.get("readyReplicas", 0),
            image=image,
            digest=digest,
            phase=status.get("phase", "Unknown"),
            conditions=[c.get("type", "") for c in status.get("conditions", []) or []],
        )


class ArgoAdapter:
    """Read-only Argo CD application revision/image digest via kubectl get."""

    def __init__(self, context: str):
        self.context = context

    def current_revision(self, app_name: str) -> str:
        result = subprocess.run(
            [
                "kubectl", "--context", self.context, "get", "application",
                app_name, "-o", "json",
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if result.returncode:
            raise ReadOnlyAdapterError(
                f"kubectl get application failed (exit {result.returncode}): "
                f"{result.stderr.strip()}"
            )
        try:
            obj = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise ReadOnlyAdapterError(f"kubectl returned invalid JSON: {error}")
        sync = obj.get("status", {}).get("sync", {}) or {}
        return str(sync.get("revision", ""))


class RunbookAdapter:
    """Read-only runbook markdown loader from docs/runbooks/."""

    def __init__(self, runbooks_dir: str | Path = "docs/runbooks"):
        self.runbooks_dir = Path(runbooks_dir)

    def load(self, runbook_id: str) -> str:
        path = self.runbooks_dir / f"{runbook_id}.md"
        if not path.is_file():
            raise ReadOnlyAdapterError(f"Runbook not found: {runbook_id}")
        return path.read_text(encoding="utf-8")

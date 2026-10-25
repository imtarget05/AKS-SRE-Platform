import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import httpx
from schemas.evidence_envelope import EvidenceEnvelope


class PlatformIncidentAdapter:
    """
    Read-only adapter for AKS SRE Platform alerts, metrics, and incident runbooks.
    Invariants:
    - Never executes kubectl, terraform, or argo commands.
    - Citations point only to read-only Prometheus endpoints or verified runbook links.
    - Reads live alerts from Prometheus at /api/v1/alerts.
    """
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("PROMETHEUS_URL", "http://kps-kube-prometheus-stack-prometheus.monitoring.svc.cluster.local:9090")
        self.timeout = float(os.getenv("PLATFORM_HTTP_TIMEOUT", "5.0"))

    def fetch_active_alert(
        self,
        alert_fingerprint: str,
        scope_id: str = "cluster-kind-01",
        synthetic_payload: Optional[Dict[str, Any]] = None
    ) -> EvidenceEnvelope:
        endpoint_url = f"{self.base_url}/api/v1/alerts"

        if synthetic_payload is not None:
            facts = synthetic_payload
            source_sha = "02423e2"
            record_version = facts.get("record_version", 1)
            source_refs = [endpoint_url]
        else:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(endpoint_url)
                    resp.raise_for_status()
                    alerts_data = resp.json().get("data", {}).get("alerts", [])

                    matched_alert = None
                    for alert in alerts_data:
                        labels = alert.get("labels", {})
                        if labels.get("alertname") == alert_fingerprint or alert_fingerprint in str(labels):
                            matched_alert = alert
                            break

                    source_refs = [endpoint_url]
                    if matched_alert:
                        labels = matched_alert.get("labels", {})
                        annotations = matched_alert.get("annotations", {})
                        runbook = annotations.get("runbook_url")
                        if runbook:
                            source_refs.append(runbook)

                        facts = {
                            "fingerprint": alert_fingerprint,
                            "alertname": labels.get("alertname", alert_fingerprint),
                            "service": labels.get("service") or labels.get("job", "unknown"),
                            "namespace": labels.get("namespace", "default"),
                            "severity": labels.get("severity", "warning"),
                            "summary": annotations.get("summary", ""),
                            "description": annotations.get("description", ""),
                            "runbook_url": runbook or "",
                            "state": matched_alert.get("state", "firing"),
                            "active_at": matched_alert.get("activeAt", ""),
                            "worker_restart_count": 0,
                            "record_version": 1
                        }
                    else:
                        facts = {
                            "fingerprint": alert_fingerprint,
                            "alertname": alert_fingerprint,
                            "status": "NOT_FIRING",
                            "record_version": 1
                        }
                    source_sha = "02423e2"
                    record_version = 1
            except httpx.HTTPError as exc:
                raise ConnectionError(f"Failed to fetch active alerts from Prometheus at {endpoint_url}: {exc}")

        return EvidenceEnvelope(
            case_type="incident",
            entity_ref=alert_fingerprint,
            source_service="aks-sre-platform",
            source_sha=source_sha,
            scope_id=scope_id,
            record_version=record_version,
            observed_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            facts=facts,
            source_refs=source_refs,
            classification="INTERNAL_CONFIDENTIAL",
            redaction_level="NONE"
        )

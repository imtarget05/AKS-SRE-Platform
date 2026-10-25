"""Cross-resource guard for the bounded AKS autoscaling proof overlay.

UPDATED: The autoscaling proof now includes Cluster Autoscaler ConfigMap and
scale-event PrometheusRule as required by the release governance tasks.
The validation overlay renders these for observability; the aks-observability
overlay includes them for production monitoring.
"""

import subprocess
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/log_scale_events.py"


class AutoscalingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        rendered = subprocess.run(
            ["kubectl", "kustomize", str(ROOT / "deploy/overlays/validation")],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        cls.objects = {
            (doc["kind"], doc["metadata"]["name"]): doc
            for doc in yaml.safe_load_all(rendered)
            if doc
        }

    def test_hpa_targets_real_deployment_with_cpu_request(self) -> None:
        hpa = self.objects[("HorizontalPodAutoscaler", "sre-demo-api")]["spec"]
        deployment = self.objects[("Deployment", "sre-demo-api")]["spec"]
        self.assertEqual(hpa["scaleTargetRef"], {
            "apiVersion": "apps/v1", "kind": "Deployment", "name": "sre-demo-api"
        })
        requests = deployment["template"]["spec"]["containers"][0]["resources"]["requests"]
        self.assertIn("cpu", requests)
        self.assertGreater(int(requests["cpu"].removesuffix("m")), 0)

    def test_validation_replica_bounds_fit_disruption_policy(self) -> None:
        hpa = self.objects[("HorizontalPodAutoscaler", "sre-demo-api")]["spec"]
        pdb = self.objects[("PodDisruptionBudget", "sre-demo-api")]["spec"]
        self.assertEqual(hpa["minReplicas"], 2)
        self.assertLessEqual(hpa["maxReplicas"], 4)
        self.assertLess(pdb["minAvailable"], hpa["minReplicas"])

    def test_aks_overlay_includes_autoscaler_config_and_scale_events(self) -> None:
        """The aks-observability overlay now includes Cluster Autoscaler config and scale-event rules."""
        rendered = subprocess.run(
            ["kubectl", "kustomize", str(ROOT / "deploy/overlays/aks-observability")],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        docs = [doc for doc in yaml.safe_load_all(rendered) if doc]

        # Cluster Autoscaler ConfigMap should be present
        has_ca_config = any(
            doc["kind"] == "ConfigMap" and doc["metadata"]["name"] == "cluster-autoscaler-status"
            for doc in docs
        )
        self.assertTrue(has_ca_config, "Cluster Autoscaler ConfigMap should be in aks-observability overlay")

        # Scale event PrometheusRule should be present with expected alerts
        scale_rule = None
        for doc in docs:
            if doc["kind"] == "PrometheusRule" and doc["metadata"]["name"] == "aks-sre-platform-scale-events":
                scale_rule = doc
                break
        self.assertIsNotNone(scale_rule, "aks-sre-platform-scale-events PrometheusRule should be present")

        # Verify the three required alerts exist
        rule_names = []
        for group in scale_rule["spec"]["groups"]:
            for rule in group["rules"]:
                rule_names.append(rule.get("alert"))
        self.assertIn("HPAScaleUp", rule_names)
        self.assertIn("HPAScaleDown", rule_names)
        self.assertIn("ClusterAutoscalerScaleEvent", rule_names)

        # The alerts should use $values for scale event metadata (not invented metrics)
        for group in scale_rule["spec"]["groups"]:
            for rule in group["rules"]:
                text = str(rule)
                # These are the EXPECTED patterns for scale event logging
                if rule.get("alert") in ("HPAScaleUp", "HPAScaleDown", "ClusterAutoscalerScaleEvent"):
                    self.assertIn("$values", text, f"Rule {rule.get('alert')} should use $values for scale metadata")
                    self.assertIn("timestamp_utc", text, f"Rule {rule.get('alert')} should include UTC timestamp")

    def test_autoscaler_config_and_scale_event_files_exist(self) -> None:
        """These files are now required for scale-event logging and CA configuration."""
        for name in ("cluster-autoscaler-config.yaml", "aks-sre-platform-scale-events.yaml"):
            with self.subTest(name=name):
                path = ROOT / "deploy/base/observability" / name
                self.assertTrue(
                    path.exists(),
                    f"{name} must exist: required for Cluster Autoscaler config and scale-event logging",
                )

    def test_event_capture_reports_observed_state_without_invented_scale(self) -> None:
        spec = importlib.util.spec_from_file_location("log_scale_events", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        replies = [
            {"metadata": {"name": "sre-demo-api", "uid": "hpa-1"}, "status": {"currentReplicas": 2, "desiredReplicas": 3}},
            {"items": [{"metadata": {"name": "aks-work-0", "uid": "node-1"}, "status": {"conditions": [{"type": "Ready", "status": "True"}]}}]},
            {"items": [{"metadata": {"namespace": "sre-platform"}, "reason": "SuccessfulRescale", "message": "New size: 3", "involvedObject": {"kind": "HorizontalPodAutoscaler", "name": "sre-demo-api"}}]},
        ]
        with patch.object(module, "kubectl_json", side_effect=replies):
            snapshot = module.capture("aks-portfolio-dev", "sre-platform", "sre-demo-api", "work")
        self.assertEqual(snapshot["hpa"]["desired_replicas"], 3)
        self.assertEqual(snapshot["user_nodes"][0]["name"], "aks-work-0")
        self.assertEqual(snapshot["scale_or_schedule_events"][0]["reason"], "SuccessfulRescale")
        self.assertNotIn("scaled", snapshot)


if __name__ == "__main__":
    unittest.main()

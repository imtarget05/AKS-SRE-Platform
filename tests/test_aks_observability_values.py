"""Managed AKS control-plane targets must not generate permanent false alerts."""

import unittest
from pathlib import Path

import yaml

VALUES = Path(__file__).resolve().parents[1] / "platform/observability/kube-prometheus-stack-aks-values.yaml"


class AksObservabilityValuesTests(unittest.TestCase):
    def test_unavailable_managed_control_plane_scrapes_and_rules_are_disabled(self):
        values = yaml.safe_load(VALUES.read_text(encoding="utf-8"))
        for component, rule in (
            ("kubeEtcd", "etcd"),
            ("kubeControllerManager", "kubeControllerManager"),
            ("kubeScheduler", "kubeScheduler"),
            ("kubeProxy", "kubeProxy"),
        ):
            with self.subTest(component=component):
                self.assertIs(values[component]["enabled"], False)
                self.assertIs(values["defaultRules"]["rules"][rule], False)

    def test_actionable_alert_pipeline_remains_enabled(self):
        values = yaml.safe_load(VALUES.read_text(encoding="utf-8"))
        self.assertIs(values["alertmanager"]["enabled"], True)
        self.assertIs(values["kubeStateMetrics"]["enabled"], True)
        self.assertIs(values["nodeExporter"]["enabled"], True)
        self.assertIs(values["prometheus"]["prometheusSpec"]["ruleSelectorNilUsesHelmValues"], False)


if __name__ == "__main__":
    unittest.main()

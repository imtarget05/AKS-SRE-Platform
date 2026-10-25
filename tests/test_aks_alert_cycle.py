"""Contract checks for AKS alert evidence parsing and state transitions."""

import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts/capture_aks_alert_cycle.py"
SPEC = importlib.util.spec_from_file_location("capture_aks_alert_cycle", MODULE)
assert SPEC and SPEC.loader
alert_cycle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(alert_cycle)


class AlertCycleParsingTests(unittest.TestCase):
    def test_missing_rule_cannot_be_reported_as_inactive(self):
        with self.assertRaisesRegex(ValueError, "found 0"):
            alert_cycle.rule_state({"status": "success", "data": {"groups": []}}, "AKSMonitoringTargetDown")

    def test_firing_timestamp_and_receiver_are_kept(self):
        rules = {
            "status": "success",
            "data": {"groups": [{"rules": [{"type": "alerting", "name": "AKSMonitoringTargetDown", "state": "firing", "alerts": [{"state": "firing", "activeAt": "2026-10-26T01:02:03Z"}]}]}]},
        }
        self.assertEqual(alert_cycle.rule_state(rules, "AKSMonitoringTargetDown"), ("firing", "2026-10-26T01:02:03Z"))
        alerts = [{"labels": {"alertname": "AKSMonitoringTargetDown"}, "receivers": [{"name": "sre-oncall"}]}]
        self.assertEqual(alert_cycle.alertmanager_receivers(alerts, "AKSMonitoringTargetDown"), ["sre-oncall"])


if __name__ == "__main__":
    unittest.main()

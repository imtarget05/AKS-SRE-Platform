"""A destroy dispatch may execute only a previously reviewed saved plan."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "aks-deploy.yml"


class DestroyWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.jobs = yaml.safe_load(WORKFLOW.read_text())["jobs"]

    def test_destroy_plan_is_saved_before_protected_execution(self):
        plan_steps = self.jobs["plan"]["steps"]
        plan_commands = "\n".join(step.get("run", "") for step in plan_steps)
        self.assertIn("terraform plan -destroy -out=tfplan", plan_commands)
        self.assertIn("terraform plan -out=tfplan", plan_commands)
        self.assertNotIn("actions/upload-artifact", str(plan_steps))
        self.assertIn("plan_hash", str(self.jobs["plan"].get("outputs", {})))

        destroy = self.jobs["destroy"]
        self.assertEqual(destroy["needs"], "plan")
        self.assertEqual(destroy["environment"], "production")
        steps = destroy["steps"]
        self.assertNotIn("actions/download-artifact", str(steps))
        commands = "\n".join(step.get("run", "") for step in steps)
        self.assertIn("terraform apply tfplan", commands)
        self.assertIn("terraform plan -destroy -out=tfplan", commands)
        self.assertIn("terraform-plan-fingerprint.py", commands)
        self.assertIn("needs.plan.outputs.plan_hash", commands)
        self.assertNotIn("terraform destroy", commands)
        self.assertNotIn("-auto-approve", commands)

    def test_missing_oidc_fails_destructive_dispatch_instead_of_skipping(self):
        plan_commands = "\n".join(step.get("run", "") for step in self.jobs["plan"]["steps"])
        self.assertIn("Destructive dispatch requires Azure OIDC credentials", plan_commands)

    def test_no_raw_plan_artifact_or_auto_approve_escape(self):
        workflow = WORKFLOW.read_text()
        # Allow SBOM artifact upload in sbom-scan job (required for supply chain gate)
        # but forbid artifact uploads in plan/apply/destroy jobs
        uploads = [
            (job_name, step)
            for job_name, job in self.jobs.items()
            for step in job.get("steps", [])
            if step.get("uses", "").startswith("actions/upload-artifact@")
            and job_name not in ("sbom-scan",)
        ]
        self.assertEqual(uploads, [], f"Unexpected artifact uploads in non-sbom jobs: {uploads}")
        for name in ("plan", "apply", "destroy"):
            steps = self.jobs[name]["steps"]
            self.assertFalse(any("artifact@" in step.get("uses", "") for step in steps))
        self.assertNotIn("download-artifact", workflow)
        self.assertNotIn("-auto-approve", workflow)
        rebuild = (ROOT / "scripts" / "rebuild-aks.sh").read_text()
        self.assertNotIn("terraform destroy", rebuild)
        self.assertNotIn("terraform apply", rebuild)
        self.assertNotIn("-auto-approve", rebuild)

    def test_infrastructure_apply_depends_only_on_reviewed_plan(self):
        self.assertEqual(self.jobs["apply"]["needs"], "plan")

    def test_fingerprint_ignores_only_timestamp_and_covers_sensitive_values(self):
        script = ROOT / "scripts" / "terraform-plan-fingerprint.py"
        base = {
            "format_version": "1.2", "terraform_version": "1.9.8",
            "timestamp": "first", "resource_changes": [
                {"address": "example.secret", "change": {
                    "actions": ["delete"], "before": {"password": "secret-one"},
                }}
            ],
        }

        def fingerprint(plan):
            return subprocess.run([sys.executable, str(script)], input=json.dumps(plan),
                                  text=True, capture_output=True, check=False)

        first = fingerprint(base)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertNotIn("secret-one", first.stdout)
        self.assertEqual(first.stdout, fingerprint({**base, "timestamp": "second"}).stdout)
        changed = json.loads(json.dumps(base))
        changed["resource_changes"][0]["change"]["before"]["password"] = "secret-two"
        self.assertNotEqual(first.stdout, fingerprint(changed).stdout)
        same_address_action_new_sku = json.loads(json.dumps(base))
        same_address_action_new_sku["resource_changes"][0]["change"]["before"]["sku"] = "Standard_D2s_v6"
        self.assertNotEqual(first.stdout, fingerprint(same_address_action_new_sku).stdout)
        self.assertNotEqual(fingerprint({"timestamp": "only"}).returncode, 0)

    def test_review_summary_shows_cost_fields_but_no_secret_values(self):
        script = ROOT / "scripts" / "terraform-plan-summary.py"
        plan = {
            "resource_changes": [{
                "address": "module.aks.azurerm_kubernetes_cluster.cluster",
                "change": {
                    "actions": ["update"],
                    "before": {"location": "eastasia", "default_node_pool": [{"vm_size": "Standard_D2s_v6", "node_count": 1}],
                               "admin_password": "secret-one"},
                    "after": {"location": "southeastasia", "default_node_pool": [{"vm_size": "Standard_D4s_v6", "node_count": 2}],
                              "admin_password": "secret-two"},
                },
            }],
        }
        result = subprocess.run([sys.executable, str(script)], input=json.dumps(plan),
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("eastasia → southeastasia", result.stdout)
        self.assertIn("Standard_D2s_v6 → Standard_D4s_v6", result.stdout)
        self.assertIn("node_count: 1 → 2", result.stdout)
        self.assertNotIn("secret-one", result.stdout)
        self.assertNotIn("secret-two", result.stdout)

    def test_local_mutation_script_rejects_before_any_terraform_call(self):
        with tempfile.TemporaryDirectory(prefix="terraform-destroy-control-") as directory:
            fake = Path(directory) / "terraform"
            log = Path(directory) / "calls.txt"
            fake.write_text(f"#!/bin/sh\necho called >> '{log}'\n")
            fake.chmod(0o755)
            for action in ("apply", "destroy"):
                result = subprocess.run(
                    ["bash", str(ROOT / "scripts" / "rebuild-aks.sh"), action],
                    env={**os.environ, "PATH": f"{directory}:{os.environ['PATH']}"},
                    text=True, capture_output=True, check=False,
                )
                self.assertEqual(result.returncode, 2)
            self.assertFalse(log.exists())


if __name__ == "__main__":
    unittest.main()

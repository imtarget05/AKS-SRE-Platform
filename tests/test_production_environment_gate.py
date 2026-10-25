"""Fail closed when production deployment review settings drift."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "check-production-environment.py"
WORKFLOW = ROOT / ".github" / "workflows" / "aks-deploy.yml"
LEGACY_WORKFLOW = ROOT / ".github" / "workflows" / "legacyapp-ci.yml"


def environment(*, self_review=False, bypass=False, reviewers=2):
    return {
        "name": "production",
        "can_admins_bypass": bypass,
        "protection_rules": [{
            "type": "required_reviewers",
            "prevent_self_review": self_review,
            "reviewers": [
                {"type": "User", "reviewer": {"id": index + 1}}
                for index in range(reviewers)
            ],
        }],
    }


class ProductionEnvironmentGateTests(unittest.TestCase):
    def check(self, payload):
        return subprocess.run(
            [sys.executable, str(CHECK)], input=json.dumps(payload),
            text=True, capture_output=True, check=False,
        )

    def test_valid_environment_passes(self):
        result = self.check(environment(self_review=True))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_self_review_and_single_reviewer_fail(self):
        for payload in (environment(), environment(self_review=True, reviewers=1)):
            with self.subTest(payload=payload):
                self.assertNotEqual(self.check(payload).returncode, 0)

    def test_admin_bypass_or_missing_proof_fails(self):
        bypass = environment(self_review=True, bypass=True)
        missing = environment(self_review=True)
        del missing["can_admins_bypass"]
        for payload in (bypass, missing):
            with self.subTest(payload=payload):
                self.assertNotEqual(self.check(payload).returncode, 0)

    def test_duplicate_reviewer_does_not_count_as_two(self):
        payload = environment(self_review=True)
        payload["protection_rules"][0]["reviewers"][1]["reviewer"]["id"] = 1
        self.assertNotEqual(self.check(payload).returncode, 0)

    def test_apply_and_destroy_check_before_azure_login(self):
        jobs = yaml.safe_load(WORKFLOW.read_text())["jobs"]
        for name in ("apply", "destroy"):
            with self.subTest(job=name):
                job = jobs[name]
                self.assertEqual(job["environment"], "production")
                steps = job["steps"]
                guard = next(i for i, step in enumerate(steps) if "check-production-environment.py" in step.get("run", ""))
                azure = next(i for i, step in enumerate(steps) if step.get("uses", "").startswith("azure/login@"))
                self.assertLess(guard, azure)

    def test_legacy_gitops_update_checks_environment_before_push(self):
        jobs = yaml.safe_load(LEGACY_WORKFLOW.read_text())["jobs"]
        job = jobs["gitops-update"]
        self.assertEqual(job["environment"], "production")
        self.assertEqual(set(job["needs"]), {"release-push", "sbom-scan"})
        steps = job["steps"]
        guard = next(i for i, step in enumerate(steps) if "check-production-environment.py" in step.get("run", ""))
        push = next(i for i, step in enumerate(steps) if "git push" in step.get("run", ""))
        self.assertLess(guard, push)

    def test_legacy_image_scan_uses_release_digest_and_uploads_only_sbom(self):
        jobs = yaml.safe_load(LEGACY_WORKFLOW.read_text())["jobs"]
        scan = jobs["sbom-scan"]
        self.assertEqual(scan["needs"], "release-push")
        commands = "\n".join(step.get("run", "") for step in scan["steps"])
        self.assertIn("needs.release-push.outputs.digest", commands)
        self.assertIn("legacy-app@", commands)
        self.assertNotIn("legacy-app:${GITHUB_SHA}", commands)
        uploads = [step for step in scan["steps"] if step.get("uses", "").startswith("actions/upload-artifact@")]
        self.assertEqual(len(uploads), 1)
        self.assertEqual(uploads[0]["with"]["path"], "sbom.spdx.json")


if __name__ == "__main__":
    unittest.main()

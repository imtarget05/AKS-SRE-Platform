from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "scripts" / "check-cloud-cutover.py"
spec = spec_from_file_location("cloud_cutover", path)
module = module_from_spec(spec)
spec.loader.exec_module(module)


def app(path, revision, automated=False):
    policy = {"automated": {"selfHeal": True}} if automated else {}
    return {
        "spec": {
            "source": {"path": path, "targetRevision": revision},
            "destination": {"namespace": "flashsale"},
            "syncPolicy": policy,
        }
    }


class CloudCutoverTests(unittest.TestCase):
    def test_local_overlay_and_moving_branch_block_cloud(self):
        issues = module.application_blockers("flashsale", app("infrastructure/kubernetes/overlays/local", "main", True))
        self.assertEqual(len(issues), 3)
        self.assertIn("cloud overlay", issues[0])
        self.assertIn("immutable", issues[1])
        self.assertIn("manual first sync", issues[2])

    def test_exact_sha_reviewed_overlay_can_pass_configuration_gate(self):
        self.assertEqual(
            module.application_blockers(
                "flashsale", app("infrastructure/kubernetes/overlays/azure", "a" * 40)
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()

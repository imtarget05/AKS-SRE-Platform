"""The digest deployment must wait for a fail-closed GitOps source check."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/kind-rollback-drill.yml"


def test_gitops_external_render_precedes_kind_deployment():
    steps = yaml.safe_load(WORKFLOW.read_text())["jobs"]["rollback"]["steps"]
    commands = [step.get("run", "") for step in steps]
    gate = "python3 gitops/validate-gitops.py --repo-map gitops/repo-map.ci.yaml --require-external"
    deploy = "bash scripts/kind_digest_release_drill.sh"
    assert commands.index(gate) < commands.index(deploy)
    for repo in ("CreditFlow", "QuanLyKho"):
        assert any(step.get("with", {}).get("path") == f"external/{repo}" for step in steps)

#!/usr/bin/env python3
"""Test matrix for gitops/validate-gitops.py.

Implements the Phase B gate matrix. Each test builds an isolated minimal repo in
a temp dir, COPIES the validator into it (the validator derives its root from
its own location, so a copy is what makes the fixture authoritative), runs it as
a SUBPROCESS so the exit code under test is the real process exit code, and
asserts the outcome.

    G1 valid repo-owned resources          -> rc == 0, no FAIL rows
    G2 required resource removed           -> rc != 0, FAIL row present
    G3 machine-specific path in --repo-map -> rc == 2 (usage error)
    G4 external repo not supplied          -> EXTERNAL_REPO_NOT_PRESENT row;
                                               rc == 0 advisory, rc != 0 with
                                               --require-external
    G5 mapping supplied but wrong path     -> rc != 0, FAIL row present
    G6 canonical restored                  -> rc == 0 again
    G7 a FAIL row implies a non-zero exit  -> asserted directly
    G8 orphan manifest detection           -> rc != 0, orphan named
    G9 cross-repo destination not allowlisted -> rc != 0, namespace named
    G10 the CI gates are not narrowed back:
         - the tflint lint runs from the terraform/ root
         - tflint --init runs before tflint --recursive
         - the recursive lint passes an ABSOLUTE --config, because a relative
           one hard-fails in every subdirectory and no --config at all lets
           the subdirectories fall back to the bundled terraform ruleset,
           where an AzureRM finding is missed
         - CI executes EVERY terraform root that owns a *.tftest.hcl
         - the test step still fails the job when the total is zero
         - the workflow's gate-matrix label matches the groups defined here

Run: python3 tests/test_gates.py
"""
import inspect
import os
import re
import shutil
import subprocess
import sys
import tempfile

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SOURCE_VALIDATOR = os.path.join(REPO, "gitops", "validate-gitops.py")
WORKFLOW = os.path.join(REPO, ".github", "workflows", "pr-gate.yaml")

# The gate groups this file defines. The workflow's gate-matrix step must be
# labelled with exactly this range: a label that stops at G1-G9 while G10
# exists hides a group from the run log, and a label that runs ahead of this
# file advertises a control that does not exist.
GATE_GROUPS = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10")

APP_PROJECT = """apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: portfolio
spec:
  sourceRepos:
    - https://github.com/example/other-repo.git
  destinations:
    - server: https://kubernetes.default.svc
      namespace: other
"""

APP = """apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: other
spec:
  project: portfolio
  source:
    repoURL: https://github.com/example/other-repo.git
    path: infrastructure/kubernetes/overlays/prod
    targetRevision: main
  destination:
    server: https://kubernetes.default.svc
    namespace: other
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
"""

APP_EXTERNAL = """apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: flashsale
spec:
  project: portfolio
  source:
    repoURL: https://github.com/example/FlashSale-Backend.git
    path: infrastructure/kubernetes/overlays/prod
    targetRevision: main
  destination:
    server: https://kubernetes.default.svc
    namespace: flashsale
  syncPolicy:
    automated: {}
"""

APP_BAD_NS = APP.replace("namespace: other", "namespace: kube-system")

APP_PROJECT_EXTERNAL = """apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: portfolio
spec:
  sourceRepos:
    - https://github.com/example/other-repo.git
    - https://github.com/example/FlashSale-Backend.git
  destinations:
    - server: https://kubernetes.default.svc
      namespace: other
    - server: https://kubernetes.default.svc
      namespace: flashsale
"""

INVENTORY = "# Manifest Inventory\n\n| `kubernetes/thing.yaml` | `LEGACY_NOT_DEPLOYED` | test |\n"

RESULTS = []


def build(root, *, app_yaml=APP, inventory=INVENTORY, project_yaml=APP_PROJECT):
    """Create the minimal repo shape the validator expects, validator included."""
    os.makedirs(os.path.join(root, "platform", "argocd", "applications"), exist_ok=True)
    os.makedirs(os.path.join(root, "gitops", "projects"), exist_ok=True)
    os.makedirs(os.path.join(root, "kubernetes"), exist_ok=True)
    shutil.copy2(SOURCE_VALIDATOR, os.path.join(root, "gitops", "validate-gitops.py"))
    with open(os.path.join(root, "platform", "argocd", "applications", "app.yaml"), "w") as fh:
        fh.write(app_yaml)
    with open(os.path.join(root, "gitops", "projects", "portfolio.yaml"), "w") as fh:
        fh.write(project_yaml)
    if inventory is not None:
        with open(os.path.join(root, "MANIFEST-INVENTORY.md"), "w") as fh:
            fh.write(inventory)


def run_validator(root, *args):
    """Run the COPIED validator, so ROOT resolves inside the fixture."""
    return subprocess.run(
        [sys.executable, os.path.join(root, "gitops", "validate-gitops.py"), *args],
        capture_output=True,
        text=True,
        cwd=root,
        timeout=60,
    )


def check(name, condition, detail=""):
    RESULTS.append((name, bool(condition)))
    status = "ok  " if condition else "FAIL"
    print(f"  [{status}] {name}{(' - ' + detail) if detail and not condition else ''}")


def with_tmp(build_kwargs, fn):
    tmp = tempfile.mkdtemp(prefix="gitops-gate-")
    try:
        build(tmp, **build_kwargs)
        return fn(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def load_workflow():
    """Parse the REAL workflow file.

    The workflow is read from the committed repository file, not from a
    fixture: the invariants under test are properties of the committed
    workflow, so a copy would only test the copy.
    """
    with open(WORKFLOW) as fh:
        return yaml.safe_load(fh)


def terraform_job_steps():
    """Return (name, run, effective working-directory) per step of the terraform job."""
    workflow = load_workflow()
    job = workflow["jobs"]["terraform"]
    default_wd = job.get("defaults", {}).get("run", {}).get("working-directory")
    steps = []
    for step in job["steps"]:
        steps.append((step.get("name", ""), step.get("run") or "",
                      step.get("working-directory", default_wd)))
    return steps


def terraform_test_roots():
    """Every terraform root that owns a *.tftest.hcl, repository-relative.

    Discovered from the FILESYSTEM, not from the workflow: the point of the
    assertion is to notice a module whose suite is never executed, which is
    only possible if the expected set comes from the repository itself.
    """
    roots = set()
    tf_root = os.path.join(REPO, "terraform")
    for dirpath, dirnames, filenames in os.walk(tf_root):
        dirnames[:] = [d for d in dirnames if d != ".terraform"]
        if not any(f.endswith(".tftest.hcl") for f in filenames):
            continue
        # <root>/tests/<name>.tftest.hcl -> <root>
        module_dir = (os.path.dirname(dirpath)
                      if os.path.basename(dirpath) == "tests" else dirpath)
        roots.add(os.path.relpath(module_dir, REPO).replace(os.sep, "/"))
    return roots


def workflow_test_roots():
    """The roots the CI workflow declares it will execute."""
    job = load_workflow()["jobs"]["terraform"]
    declared = job.get("env", {}).get("TERRAFORM_TEST_ROOTS", "")
    return set(declared.split())


def main():
    print("G1 valid repo-owned resources -> PASS")
    def g1(tmp):
        r = run_validator(tmp)
        check("G1 rc == 0", r.returncode == 0, f"rc={r.returncode} {r.stdout[-200:]}")
        check("G1 no FAIL rows", '"outcome": "FAIL"' not in run_validator(tmp, "--json").stdout)
    with_tmp({}, g1)

    print("G2 required resource removed (no inventory) -> FAIL")
    def g2(tmp):
        r = run_validator(tmp, "--json")
        check("G2 rc != 0", r.returncode != 0, f"rc={r.returncode}")
        check("G2 FAIL reported", '"outcome": "FAIL"' in r.stdout)
    with_tmp({"inventory": None}, g2)

    print("G3 machine-specific path in --repo-map -> usage error")
    def g3(tmp):
        bad = os.path.join(tmp, "map.yaml")
        with open(bad, "w") as fh:
            fh.write("Other-Repo: ~/Downloads/other-repo\n")
        r = run_validator(tmp, "--repo-map", bad)
        check("G3 rc == 2", r.returncode == 2, f"rc={r.returncode}")
        check("G3 explains rejection", "machine-specific" in (r.stderr + r.stdout))
    with_tmp({}, g3)

    print("G4 external repo not supplied -> NOT_PRESENT, never a fake pass")
    def g4(tmp):
        r = run_validator(tmp, "--json")
        check("G4 advisory rc == 0", r.returncode == 0, f"rc={r.returncode}")
        check("G4 NOT_PRESENT reported", "EXTERNAL_REPO_NOT_PRESENT" in r.stdout)
        rr = run_validator(tmp, "--require-external")
        check("G4 --require-external rc != 0", rr.returncode != 0, f"rc={rr.returncode}")
    with_tmp({"app_yaml": APP_EXTERNAL, "project_yaml": APP_PROJECT_EXTERNAL}, g4)

    print("G5 mapping supplied but wrong path -> FAIL")
    def g5(tmp):
        bad = os.path.join(tmp, "map.yaml")
        with open(bad, "w") as fh:
            fh.write("FlashSale-Backend: does/not/exist\n")
        r = run_validator(tmp, "--repo-map", bad, "--require-external")
        check("G5 rc != 0", r.returncode != 0, f"rc={r.returncode}")
        check("G5 FAIL reported", "does not exist" in r.stdout, r.stdout[-200:])
    with_tmp({"app_yaml": APP_EXTERNAL, "project_yaml": APP_PROJECT_EXTERNAL}, g5)

    print("G6 canonical restored -> PASS")
    def g6(tmp):
        r = run_validator(tmp)
        check("G6 rc == 0", r.returncode == 0, f"rc={r.returncode} {r.stdout[-200:]}")
    with_tmp({}, g6)

    print("G7 a FAIL row implies a non-zero exit code")
    def g7(tmp):
        r = run_validator(tmp, "--json")
        has_fail = '"outcome": "FAIL"' in r.stdout
        check("G7 FAIL implies rc != 0", (not has_fail) or r.returncode != 0,
              f"has_fail={has_fail} rc={r.returncode}")
    with_tmp({"inventory": None}, g7)

    print("G8 orphan manifest detection")
    def g8(tmp):
        with open(os.path.join(tmp, "kubernetes", "orphan.yaml"), "w") as fh:
            fh.write("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: orphan\n")
        r = run_validator(tmp, "--json")
        check("G8 orphan fails", r.returncode != 0, f"rc={r.returncode}")
        check("G8 orphan named", "orphan.yaml" in r.stdout, r.stdout[-200:])
    with_tmp({}, g8)

    print("G9 cross-repo destination not in AppProject allowlist -> FAIL")
    def g9(tmp):
        r = run_validator(tmp, "--json")
        check("G9 rc != 0", r.returncode != 0, f"rc={r.returncode}")
        check("G9 namespace violation named", "NOT in portfolio destinations" in r.stdout,
              r.stdout[-300:])
    with_tmp({"app_yaml": APP_BAD_NS}, g9)

    print("G10 the CI gates are not narrowed back")
    def g10():
        steps = terraform_job_steps()
        lint = [wd for _n, r, wd in steps if "tflint --recursive" in r]
        check("G10 tflint lints from the terraform/ root",
              bool(lint) and all(wd == "terraform" for wd in lint),
              f"working-directory of the lint step(s): {lint}")
        init_at = [i for i, (_n, r, _wd) in enumerate(steps) if "tflint --init" in r]
        lint_at = [i for i, (_n, r, _wd) in enumerate(steps) if "tflint --recursive" in r]
        check("G10 tflint --init runs before tflint --recursive",
              bool(init_at) and bool(lint_at) and min(init_at) < min(lint_at),
              f"init step at {init_at}, recursive step at {lint_at}")

        # The --config argument must be an ABSOLUTE path. Measured with tflint
        # v0.64.0 on this tree: a relative path hard-fails in every
        # subdirectory, and NO --config lets the subdirectories fall back to
        # the bundled terraform ruleset, where an AzureRM finding is missed.
        configs = []
        for _n, r, _wd in steps:
            if "tflint --recursive" not in r:
                continue
            m = re.search(r"--config\s+(\"[^\"]*\"|'[^']*'|\S+)", r)
            configs.append(m.group(1).strip("\"'") if m else None)
        check("G10 the recursive lint passes an ABSOLUTE --config",
              bool(configs) and all(
                  c is not None and (c.startswith("/") or "$(pwd)" in c or "${PWD}" in c)
                  for c in configs),
              f"--config value(s) in the lint step(s): {configs}")

        # Every root that owns a *.tftest.hcl must be executed by CI. A module
        # added without being wired in is a suite that never runs, and the
        # green build would not mean the module plans are asserted.
        expected = terraform_test_roots()
        declared = workflow_test_roots()
        check("G10 CI executes every terraform test root",
              bool(expected) and expected == declared,
              f"roots in the repository: {sorted(expected)}, "
              f"roots wired into CI: {sorted(declared)}")

        test_runs = [r for _n, r, _wd in steps
                     if "terraform test" in r and "TERRAFORM_TEST_ROOTS" in r]
        check("G10 the test step walks the declared roots",
              bool(test_runs) and all("${TERRAFORM_TEST_ROOTS}" in r for r in test_runs),
              "no step consumes TERRAFORM_TEST_ROOTS")

        # The guard must stay a guard: a total of zero has to fail the job.
        guard = [r for _n, r, _wd in steps if re.search(r"-eq\s+0", r)]
        check("G10 the test step still fails the job on a zero total",
              bool(guard) and all("exit 1" in r for r in guard),
              "no step fails the job when the total is zero")

        # The gate-matrix label must name exactly the groups this file
        # defines, and every declared group must actually be a group here.
        python_steps = load_workflow()["jobs"]["python"]["steps"]
        labels = [s.get("name", "") for s in python_steps
                  if s.get("name", "").startswith("gate test matrix")]
        printed = set(re.findall(r'print\("(G\d+) ', inspect.getsource(main)))
        expected_label = f"gate test matrix (G1-{GATE_GROUPS[-1]})"
        check("G10 the gate-matrix label matches the groups this file defines",
              labels == [expected_label] and printed == set(GATE_GROUPS),
              f"label(s) {labels}, groups printed here {sorted(printed)}, "
              f"groups declared {list(GATE_GROUPS)}")
    g10()

    passed = sum(1 for _n, ok in RESULTS if ok)
    failed = len(RESULTS) - passed
    print(f"\n{passed} passed, {failed} failed, {len(RESULTS)} assertions total")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())


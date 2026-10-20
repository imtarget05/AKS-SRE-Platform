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
    G11 the validator does not skip a project file (regression F3/F4):
         - two files declaring the SAME AppProject name FAIL, and the failure
           names BOTH paths
         - the file that the old dictionary-keyed implementation would have
           dropped is validated too (a wildcard allowlist in it is reported)
         - an AppProject outside the canonical directory FAILS
         - the verdict does not depend on the order of the project directories
    G13 the install and the manifests are not able to lose data silently
         (regressions F1/F2):
         - scripts/bootstrap.sh applies the Argo CD manifest server-side
         - no two YAML files in the repository declare the same object
           (apiVersion/kind/namespace/name), so no dashboard ConfigMap or
           AppProject can be silently overwritten again

Run: python3 tests/test_gates.py
"""
import inspect
import json
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
GATE_GROUPS = (
    "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10", "G11", "G13",
)

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


def build(root, *, app_yaml=APP, inventory=INVENTORY, project_yaml=APP_PROJECT,
          extra_projects=()):
    """Create the minimal repo shape the validator expects, validator included.

    The AppProject is written to the CANONICAL directory (`platform/argocd/`),
    because that is where ADR-015 puts it and where the real repository keeps
    it. Fixtures that need a second home use `extra_projects`.
    """
    os.makedirs(os.path.join(root, "platform", "argocd", "applications"), exist_ok=True)
    os.makedirs(os.path.join(root, "platform", "argocd"), exist_ok=True)
    os.makedirs(os.path.join(root, "gitops", "projects"), exist_ok=True)
    os.makedirs(os.path.join(root, "kubernetes"), exist_ok=True)
    shutil.copy2(SOURCE_VALIDATOR, os.path.join(root, "gitops", "validate-gitops.py"))
    with open(os.path.join(root, "platform", "argocd", "applications", "app.yaml"), "w") as fh:
        fh.write(app_yaml)
    with open(os.path.join(root, "platform", "argocd", "appproject.yaml"), "w") as fh:
        fh.write(project_yaml)
    for rel, content in extra_projects:
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(content)
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


def outcomes(json_text):
    """The (check, target, outcome) triples of a --json validator run."""
    data = json.loads(json_text)
    return sorted((r["check"], r["target"], r["outcome"]) for r in data["checks"])


def reverse_projects_dirs(tmp):
    """Rewrite the COPIED validator so the project directories are reversed.

    The copy is what the fixture runs, so this is a real change of the code
    under test — not a mocked one.
    """
    path = os.path.join(tmp, "gitops", "validate-gitops.py")
    src = open(path).read()
    old = ('PROJECTS_DIRS = [\n'
           '    os.path.join(ROOT, "gitops", "projects"),\n'
           '    CANONICAL_PROJECTS_DIR,\n'
           ']')
    new = ('PROJECTS_DIRS = [\n'
           '    CANONICAL_PROJECTS_DIR,\n'
           '    os.path.join(ROOT, "gitops", "projects"),\n'
           ']')
    if old not in src:
        raise AssertionError("PROJECTS_DIRS block not found in the copied validator")
    with open(path, "w") as fh:
        fh.write(src.replace(old, new))


def duplicate_objects():
    """Objects declared by two different files: (apiVersion, kind, ns, name).

    Two files owning one object name is last-writer-wins on a cluster — the
    Grafana dashboard ConfigMap (F2) and the AppProject (F4) were both lost
    that way, silently.
    """
    roots = ["platform", "kubernetes", "deploy", "gitops", "apps"]
    seen = {}
    dupes = []
    for r in roots:
        for dirpath, dirnames, filenames in os.walk(os.path.join(REPO, r)):
            dirnames[:] = [d for d in dirnames
                           if d not in (".git", "node_modules", ".venv", ".terraform")]
            for name in filenames:
                if not name.endswith((".yaml", ".yml")):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    docs = [d for d in yaml.safe_load_all(open(path)) if d]
                except yaml.YAMLError:
                    continue
                for d in docs:
                    if not isinstance(d, dict) or "kind" not in d:
                        continue
                    if d["kind"] == "Kustomization":
                        # A build config, not an API object: several of them
                        # legitimately exist and none of them is applied.
                        continue
                    meta = d.get("metadata") or {}
                    key = (d.get("apiVersion", ""), d["kind"],
                           meta.get("namespace", ""), meta.get("name"))
                    rel = os.path.relpath(path, REPO)
                    if key in seen and seen[key] != rel:
                        dupes.append((key, seen[key], rel))
                    else:
                        seen[key] = rel
    return dupes


def g11_dup(tmp):
    r = run_validator(tmp, "--json")
    check("G11 a duplicate AppProject name fails", r.returncode != 0, f"rc={r.returncode}")
    check("G11 the duplicate is reported", "appproject-duplicate-name" in r.stdout,
          r.stdout[-400:])
    check("G11 BOTH conflicting paths are named",
          "platform/argocd/appproject.yaml" in r.stdout
          and "gitops/projects/portfolio.yaml" in r.stdout,
          r.stdout[-400:])
    # The file the old dictionary-keyed implementation would have DROPPED must
    # still be validated on its own: its wildcard allowlist has to surface.
    check("G11 the previously-skipped file is validated too",
          "appproject-sourceRepos" in r.stdout
          and "gitops/projects/portfolio.yaml#portfolio" in r.stdout,
          r.stdout[-400:])
    check("G11 the wildcard allowlist of the skipped file is reported",
          "wildcard sourceRepos" in r.stdout, r.stdout[-400:])

def g11_order_independent(tmp):
    forward = outcomes(run_validator(tmp, "--json").stdout)
    reverse_projects_dirs(tmp)
    backward = outcomes(run_validator(tmp, "--json").stdout)
    check("G11 the verdict does not depend on the project directory order",
          forward == backward,
          f"forward={forward}\nbackward={backward}")


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

    print("G11 the validator does not skip a project file (regression F3/F4)")
    def g11():
        # (a) Two files, ONE name. The old implementation keyed the projects by
        # metadata.name and silently dropped the first file, so the verdict
        # depended on the iteration order of the project directories.
        # The second file carries a WILDCARD allowlist: under the old
        # implementation it was the file that got dropped, so this allowlist
        # was never validated at all. It must be reported now.
        duplicate = APP_PROJECT.replace(
            "    - https://github.com/example/other-repo.git",
            "    - '*'",
        )
        fixture = {
            "extra_projects": (
                ("gitops/projects/portfolio.yaml", duplicate),
            ),
        }
        with_tmp(fixture, g11_dup)
        with_tmp(fixture, g11_order_independent)

        # (b) An AppProject outside the canonical directory is a FAIL: it is
        # the second home that made the duplicate possible.
        def g11_non_canonical(tmp):
            r = run_validator(tmp, "--json")
            check("G11 non-canonical AppProject fails", r.returncode != 0, f"rc={r.returncode}")
            check("G11 non-canonical path named", "appproject-canonical-dir" in r.stdout,
                  r.stdout[-300:])
        with_tmp({"extra_projects": (("gitops/projects/portfolio.yaml", APP_PROJECT),)}, g11_non_canonical)
    g11()

    print("G13 nothing can be overwritten silently (regressions F1/F2)")
    def g13():
        with open(os.path.join(REPO, "scripts", "bootstrap.sh")) as fh:
            bootstrap = fh.read()
        check("G13 the Argo CD manifest is applied server-side",
              "--server-side" in bootstrap and "force-conflicts" in bootstrap)
        duplicates = duplicate_objects()
        check("G13 no two files declare the same object",
              not duplicates, f"duplicate object(s): {duplicates}")
    g13()

    passed = sum(1 for _n, ok in RESULTS if ok)
    failed = len(RESULTS) - passed
    print(f"\n{passed} passed, {failed} failed, {len(RESULTS)} assertions total")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())


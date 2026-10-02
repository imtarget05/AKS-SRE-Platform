#!/usr/bin/env python3
"""Offline semantic validation for the GitOps layer of AKS-SRE-Platform.

WHAT THIS VALIDATES (repo-owned, honest, offline)
-------------------------------------------------
1. `gitops/applications/*.yaml` — every Argo CD Application declares a project
   that exists, and every locally-verifiable field is well formed
   (repoURL, targetRevision, destination namespace, sync policy).
2. `gitops/projects/*.yaml` and `platform/argocd/appproject.yaml` — AppProject
   source/destination allowlists are non-empty, contain no `*` wildcard on
   sourceRepos, and every Application's source repo + destination namespace is
   actually allowed by its project.
3. No developer-machine assumptions: a hardcoded absolute or `~`-prefixed path
   in the mapping configuration is a hard FAIL, never a silent default.
4. Every non-Application YAML under `kubernetes/` is classified by the manifest
   inventory (`MANIFEST-INVENTORY.md`), so there are no orphan manifests.

EXTERNAL REPOSITORIES
---------------------
Both current Applications point at repositories this repo does not own. Their
source trees cannot be rendered from here unless a checkout mapping is supplied.

  - no mapping supplied  -> `EXTERNAL_REPO_NOT_PRESENT` (NOT a pass, NOT a fail)
  - mapping supplied but path missing/wrong -> FAIL
  - mapping supplied and renders           -> run the full render checks

A missing external checkout is never converted into a green result. Callers that
require full validation must assert on the outcome kinds, not just exit status;
`--require-external` makes "not present" a failure for exactly those callers.

USAGE
-----
    validate-gitops.py                                  # repo-owned checks only
    validate-gitops.py --repo-map repos.yaml           # + external render checks
    validate-gitops.py --require-external              # not-present becomes FAIL
    validate-gitops.py --json                          # machine-readable outcome

Exit codes: 0 all required checks passed · 1 a check failed · 2 bad usage.
"""
import argparse
import json
import os
import re
import subprocess
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS_DIR = os.path.join(ROOT, "gitops", "applications")
PROJECTS_DIRS = [
    os.path.join(ROOT, "gitops", "projects"),
    os.path.join(ROOT, "platform", "argocd"),
]
INVENTORY = os.path.join(ROOT, "MANIFEST-INVENTORY.md")

OK = "PASS"
FAIL = "FAIL"
NOT_PRESENT = "EXTERNAL_REPO_NOT_PRESENT"

# A mapping entry that looks machine-specific is rejected outright (G3).
MACHINE_PATH_RE = re.compile(r"(^~/)|(^/)|(^[A-Za-z]:[\\/])")



class Report:
    def __init__(self):
        self.rows = []

    def add(self, check, target, outcome, detail):
        self.rows.append(
            {"check": check, "target": target, "outcome": outcome, "detail": detail}
        )

    @property
    def failed(self):
        return [r for r in self.rows if r["outcome"] == FAIL]

    @property
    def not_present(self):
        return [r for r in self.rows if r["outcome"] == NOT_PRESENT]

    def exit_code(self, require_external):
        if self.failed:
            return 1
        if require_external and self.not_present:
            return 1
        return 0


def load(path):
    with open(path) as fh:
        return yaml.safe_load(fh)


def usage_error(msg):
    """Configuration the caller must fix. Distinct from a check failure (1)."""
    print(f"USAGE ERROR: {msg}", file=sys.stderr)
    sys.exit(2)


def repo_tail(url):
    tail = url.rstrip("/").rsplit("/", 1)[-1]
    return tail[:-4] if tail.endswith(".git") else tail


# ---------------------------------------------------------------- projects ----
def collect_projects(rep):
    """Load every AppProject found in the repo-owned project directories."""
    projects = {}
    for d in PROJECTS_DIRS:
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith((".yaml", ".yml")):
                continue
            path = os.path.join(d, name)
            doc = load(path)
            if not isinstance(doc, dict) or doc.get("kind") != "AppProject":
                continue
            key = (doc.get("metadata") or {}).get("name")
            rel = os.path.relpath(path, ROOT)
            if not key:
                rep.add("appproject-name", rel, FAIL, "AppProject has no metadata.name")
                continue
            projects[key] = (doc, rel)
    return projects


def check_projects(rep, projects):
    if not projects:
        rep.add("appproject-present", "gitops/projects", FAIL, "no AppProject found")
        return
    for name, (doc, rel) in sorted(projects.items()):
        spec = doc.get("spec") or {}
        repos = spec.get("sourceRepos") or []
        dests = spec.get("destinations") or []
        if not repos:
            rep.add("appproject-sourceRepos", f"{rel}#{name}", FAIL, "sourceRepos is empty")
        elif "*" in repos:
            rep.add(
                "appproject-sourceRepos",
                f"{rel}#{name}",
                FAIL,
                f"wildcard sourceRepos {repos}",
            )
        else:
            rep.add(
                "appproject-sourceRepos",
                f"{rel}#{name}",
                OK,
                f"{len(repos)} repo(s), no wildcard",
            )
        if not dests:
            rep.add("appproject-destinations", f"{rel}#{name}", FAIL, "destinations is empty")
        else:
            bad = [d for d in dests if "*" in (d.get("namespace") or "")]
            rep.add(
                "appproject-destinations",
                f"{rel}#{name}",
                FAIL if bad else OK,
                f"wildcard namespace {bad}" if bad else f"{len(dests)} destination(s)",
            )


def project_allows(project_doc, repo_url, namespace):
    """Does the AppProject permit this (repoURL, namespace) pair?"""
    spec = project_doc.get("spec") or {}
    allowed_repos = spec.get("sourceRepos") or []
    allowed_ns = {d.get("namespace") for d in (spec.get("destinations") or [])}
    return repo_url in allowed_repos, namespace in allowed_ns


# ------------------------------------------------------------ applications ----
def check_applications(rep, projects, repo_map):
    if not os.path.isdir(APPS_DIR):
        rep.add("applications-present", "gitops/applications", FAIL, "directory missing")
        return
    files = [f for f in sorted(os.listdir(APPS_DIR)) if f.endswith((".yaml", ".yml"))]
    if not files:
        rep.add("applications-present", "gitops/applications", FAIL, "no Application found")

    for fname in files:
        path = os.path.join(APPS_DIR, fname)
        rel = os.path.relpath(path, ROOT)
        app = load(path) or {}
        meta = app.get("metadata") or {}
        spec = app.get("spec") or {}
        name = meta.get("name") or fname
        target = f"{rel}#{name}"

        # --- locally verifiable fields -------------------------------------
        proj = spec.get("project")
        if not proj:
            rep.add("app-project", target, FAIL, "spec.project is required")
        elif proj not in projects:
            rep.add(
                "app-project", target, FAIL, f"project {proj!r} not declared in this repo"
            )
        else:
            rep.add("app-project", target, OK, f"project {proj}")

        src = spec.get("source") or {}
        repo_url = src.get("repoURL") or ""
        subpath = src.get("path") or ""
        rev = src.get("targetRevision") or ""
        if not re.fullmatch(r"https://github\.com/[\w.-]+/[\w.-]+\.git", repo_url):
            rep.add("app-repoURL", target, FAIL, f"malformed repoURL {repo_url!r}")
        else:
            rep.add("app-repoURL", target, OK, repo_tail(repo_url))
        rep.add(
            "app-targetRevision",
            target,
            OK if rev else FAIL,
            rev or "targetRevision is required",
        )
        rep.add("app-path", target, OK if subpath else FAIL, subpath or "source.path is required")

        dest = spec.get("destination") or {}
        ns = dest.get("namespace")
        if ns in (None, "", "default"):
            rep.add("app-namespace", target, FAIL, f"destination.namespace is {ns!r}")
        elif proj in projects:
            _, ok_ns = project_allows(projects[proj][0], repo_url, ns)
            rep.add(
                "app-namespace",
                target,
                OK if ok_ns else FAIL,
                f"{ns} allowed by {proj}" if ok_ns else f"{ns} NOT in {proj} destinations",
            )
        else:
            rep.add("app-namespace", target, OK, ns)

        policy = spec.get("syncPolicy") or {}
        # `automated: {}` is valid Argo config meaning "automated sync with
        # default options", so test for key presence, not truthiness.
        automated = "automated" in policy
        rep.add(
            "app-automated-sync",
            target,
            OK if automated else FAIL,
            "automated sync enabled" if automated else "syncPolicy.automated not enabled",
        )

        # --- cross-repo consistency against the AppProject -----------------
        if proj in projects:
            ok_repo, _ = project_allows(projects[proj][0], repo_url, ns)
            rep.add(
                "app-sourceRepo-allowed",
                target,
                OK if ok_repo else FAIL,
                "allowed by project" if ok_repo else f"{repo_url} not in {proj} sourceRepos",
            )

        # --- source tree render, only if a checkout is supplied ------------
        tail = repo_tail(repo_url)
        checkout = repo_map.get(tail)
        if checkout is None:
            rep.add(
                "external-render",
                target,
                NOT_PRESENT,
                f"{tail} is an external repository and no checkout was supplied; "
                "source tree NOT validated",
            )
            continue

        if not os.path.isdir(checkout):
            rep.add(
                "external-render",
                target,
                FAIL,
                f"mapped checkout for {tail} does not exist: {checkout}",
            )
            continue
        overlay = os.path.join(checkout, subpath)
        if not os.path.isdir(overlay):
            rep.add(
                "external-render", target, FAIL, f"overlay path {subpath!r} missing in {tail}"
            )
            continue
        # Explicit shell=False / check=False: the argument list is fixed and holds
        # no caller-supplied shell string, so this is a documented hot-spot
        # rather than a finding — but making it explicit means switching it on is
        # a reviewable diff instead of a silent injection surface.
        r = subprocess.run(
            ["kubectl", "kustomize", overlay],
            capture_output=True,
            text=True,
            timeout=120,
            shell=False,
            check=False,
        )
        if r.returncode != 0:
            rep.add(
                "external-render", target, FAIL, f"kustomize failed: {r.stderr.strip()[:300]}"
            )
            continue
        docs = [d for d in yaml.safe_load_all(r.stdout) if d]
        if not docs:
            rep.add("external-render", target, FAIL, "render produced zero objects")
            continue
        rep.add("external-render", target, OK, f"{len(docs)} objects from {tail}")


# -------------------------------------------------------------- inventory ----
def check_inventory(rep):
    """No silent orphan YAML under kubernetes/."""
    if not os.path.isfile(INVENTORY):
        rep.add("manifest-inventory", "MANIFEST-INVENTORY.md", FAIL, "inventory file missing")
        return
    text = open(INVENTORY).read()
    kube = os.path.join(ROOT, "kubernetes")
    if not os.path.isdir(kube):
        return
    for name in sorted(os.listdir(kube)):
        if not name.endswith((".yaml", ".yml")) or name == "kustomization.yaml":
            continue
        if f"kubernetes/{name}" not in text:
            rep.add(
                "manifest-inventory",
                f"kubernetes/{name}",
                FAIL,
                "unclassified: add it to MANIFEST-INVENTORY.md",
            )


def load_repo_map(path):
    """Load {repo_tail: local_checkout}. Rejects machine-specific paths (G3)."""
    data = load(path)
    if not isinstance(data, dict):
        usage_error(f"--repo-map {path} must be a mapping of repo name -> path")
    out = {}
    for k, v in data.items():
        v = os.path.expanduser(str(v))
        if MACHINE_PATH_RE.search(v):
            usage_error(
                f"--repo-map entry {k!r} points at a machine-specific path ({v!r}). "
                "Use a path relative to the workspace root."
            )
        out[k] = os.path.abspath(v)
    return out


def main():
    ap = argparse.ArgumentParser(description="GitOps semantic validation")
    ap.add_argument("--repo-map", help="YAML mapping of repo name -> local checkout")
    ap.add_argument(
        "--require-external",
        action="store_true",
        help="treat EXTERNAL_REPO_NOT_PRESENT as a failure",
    )
    ap.add_argument("--json", action="store_true", help="emit JSON only")
    args = ap.parse_args()

    repo_map = load_repo_map(args.repo_map) if args.repo_map else {}

    rep = Report()
    projects = collect_projects(rep)
    check_projects(rep, projects)
    check_applications(rep, projects, repo_map)
    check_inventory(rep)

    rc = rep.exit_code(args.require_external)

    if args.json:
        json.dump({"exitCode": rc, "checks": rep.rows}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return rc

    for r in rep.rows:
        print(f"  {r['outcome']:<28} {r['check']:<26} {r['target']}  ({r['detail']})")
    ok = len([r for r in rep.rows if r["outcome"] == OK])
    print(
        f"\nGITOPS: {ok} passed, {len(rep.failed)} failed, "
        f"{len(rep.not_present)} not-present, {len(rep.rows)} total "
        f"({len(projects)} AppProject(s), {len(repo_map)} external checkout(s) supplied)"
    )
    if rep.not_present:
        print(
            "NOTE: external repositories were NOT validated. This is not a pass for "
            "those source trees - see EXTERNAL_REPO_NOT_PRESENT rows above."
        )
    return rc


if __name__ == "__main__":
    sys.exit(main())


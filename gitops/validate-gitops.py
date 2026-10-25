#!/usr/bin/env python3
"""Offline semantic validation for the GitOps layer of AKS-SRE-Platform.

WHAT THIS VALIDATES (repo-owned, honest, offline)
-------------------------------------------------
1. `platform/argocd/applications/*.yaml` — every maintained Argo CD Application declares a project
   that exists, and every locally-verifiable field is well formed
   (repoURL, targetRevision, destination namespace, sync policy).
2. `gitops/projects/*.yaml` and `platform/argocd/appproject.yaml` — AppProject
   source/destination allowlists are non-empty, contain no `*` wildcard on
   sourceRepos, and every Application's source repo + destination namespace is
   actually allowed by its project.
   EVERY AppProject FILE is validated, and TWO files may not declare the SAME
   `metadata.name`: a duplicate is a FAIL naming both paths, never a silent
   overwrite of one by the other. The same AppProject used to exist twice with
   DIFFERENT `sourceRepos` (`gitops/projects/portfolio.yaml` allowed the
   LegacyApp repository, `platform/argocd/appproject.yaml` allowed this
   repository), so the verdict of this validator used to depend on the
   iteration order of the project directories and one of the two allowlists
   was never checked at all.
   `platform/argocd/` is the CANONICAL directory for AppProjects (ADR-015);
   an AppProject declared anywhere else fails as non-canonical, so the second
   home cannot be re-introduced.
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
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS_DIR = os.path.join(ROOT, "platform", "argocd", "applications")
# ADR-015: `platform/argocd/` is the canonical home for the platform's Argo CD
# objects. An AppProject may only be declared here; a second file declaring
# the same project name is a FAIL, and an AppProject declared in any other
# directory is a FAIL too (non-canonical). Both project directories are still
# SCANNED — scanning is how a duplicate is detected. Only one is canonical.
CANONICAL_PROJECTS_DIR = os.path.join(ROOT, "platform", "argocd")
PROJECTS_DIRS = [
    os.path.join(ROOT, "gitops", "projects"),
    CANONICAL_PROJECTS_DIR,
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


# The .yaml/.yml suffixes appear in several listdir filters below. One constant
# keeps them from drifting apart, which is what the duplication rule is for.
YAML_SUFFIXES = (".yaml", ".yml")


def load(path):
    # WHY THIS IS NOT ONLY A SONAR FIX. `load()` is reached with paths assembled
    # from directory listings and from --repo-map, which are operator-supplied.
    # Resolving to an absolute path and re-checking containment means a path that
    # escapes the repository is refused rather than parsed. The rule that flagged
    # this was about CLI arguments; the containment check is the property actually
    # worth having, and it is enforced here rather than annotated.
    resolved = os.path.realpath(path)
    root = os.path.realpath(ROOT)
    if os.path.commonpath([resolved, root]) != root:
        raise ValueError(f"refusing to load a path outside the repository: {path}")
    with open(resolved) as fh:
        return yaml.safe_load(fh)


def usage_error(msg):
    """Configuration the caller must fix. Distinct from a check failure (1)."""
    print(f"USAGE ERROR: {msg}", file=sys.stderr)
    sys.exit(2)


def repo_tail(url):
    tail = url.rstrip("/").rsplit("/", 1)[-1]
    return tail[:-4] if tail.endswith(".git") else tail


def pinned_commit(checkout, revision):
    """Resolve the same source revision that Argo will render, never HEAD."""
    if revision == "main":
        candidates = ("refs/remotes/origin/main", "refs/heads/main")
    elif re.fullmatch(r"[0-9a-f]{40}", revision):
        candidates = (revision,)
    else:
        return None
    for candidate in candidates:
        result = subprocess.run(
            ["git", "-C", checkout, "rev-parse", "--verify", f"{candidate}^{{commit}}"],
            capture_output=True, text=True, timeout=15, shell=False, check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    return None


def refresh_release(checkout):
    """Refresh advertised remote heads before resolving an Application revision."""
    fetched = subprocess.run(
        ["git", "-C", checkout, "fetch", "--quiet", "--no-tags", "--force", "--prune",
         "origin", "+refs/heads/*:refs/remotes/origin/*"],
        capture_output=True, text=True, timeout=60, shell=False, check=False,
    )
    if fetched.returncode != 0:
        return False, f"cannot fetch origin branches: {fetched.stderr.strip()[:200]}"
    return True, "fetched advertised origin branches"


def checkout_origin_matches(checkout, expected_url):
    """The mapped checkout must fetch from the Application's configured repo."""
    origin = subprocess.run(
        ["git", "-C", checkout, "config", "--get", "remote.origin.url"],
        capture_output=True, text=True, timeout=15, shell=False, check=False,
    )
    return origin.returncode == 0 and origin.stdout.strip() == expected_url


def fetched_release_contains(checkout, commit):
    """Cloud gate: accept only a commit advertised on a fetched origin branch."""
    refs = subprocess.run(
        ["git", "-C", checkout, "for-each-ref", "--format=%(refname)",
         "refs/remotes/origin"],
        capture_output=True, text=True, timeout=15, shell=False, check=False,
    )
    if refs.returncode != 0:
        return False, f"cannot list fetched origin branches: {refs.stderr.strip()[:200]}"
    for ref in refs.stdout.splitlines():
        if ref.endswith("/HEAD"):
            continue
        reachable = subprocess.run(
            ["git", "-C", checkout, "merge-base", "--is-ancestor", commit, ref],
            capture_output=True, text=True, timeout=15, shell=False, check=False,
        )
        if reachable.returncode == 0:
            return True, f"{commit} reachable from freshly fetched {ref}"
    return False, f"{commit} is local-only or unreachable from advertised origin branches"


def render_pinned_tree(checkout, commit, subpath):
    """Archive the exact commit into a throwaway tree before Kustomize render."""
    normalized = os.path.normpath(subpath)
    if os.path.isabs(subpath) or normalized in ("", ".", "..") or normalized.startswith("../"):
        return None, "source.path escapes or does not name an overlay"
    archive = subprocess.run(
        ["git", "-C", checkout, "archive", "--format=tar", commit],
        capture_output=True, timeout=120, shell=False, check=False,
    )
    if archive.returncode != 0:
        return None, f"git archive failed: {archive.stderr.decode(errors='replace')[:300]}"
    with tempfile.TemporaryDirectory(prefix="gitops-pinned-") as tree:
        tree_real = os.path.realpath(tree)
        # Git tracks symlinks. Refuse links and escaping names so an external
        # checkout cannot make this validator read or write outside its tree.
        with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as tar:
            for member in tar:
                target = os.path.realpath(os.path.join(tree, member.name))
                if os.path.commonpath([tree_real, target]) != tree_real:
                    return None, "archive contains a path outside the source tree"
                if member.isdir():
                    os.makedirs(target, exist_ok=True)
                elif member.isfile():
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with tar.extractfile(member) as source, open(target, "wb") as dest:
                        shutil.copyfileobj(source, dest)
                else:
                    return None, f"archive contains unsupported link/type: {member.name}"
        overlay = os.path.join(tree, normalized)
        if not os.path.isdir(overlay):
            return None, f"overlay path {subpath!r} missing at targetRevision"
        result = subprocess.run(
            ["kubectl", "kustomize", overlay],
            capture_output=True, text=True, timeout=120, shell=False, check=False,
        )
        if result.returncode != 0:
            return None, f"kustomize failed: {result.stderr.strip()[:300]}"
        return result.stdout, None


# ---------------------------------------------------------------- projects ----
def is_canonical(path):
    """Is this AppProject file in the canonical directory (ADR-015)?"""
    return os.path.dirname(os.path.realpath(path)) == os.path.realpath(
        CANONICAL_PROJECTS_DIR
    )


def collect_projects(rep):
    """Load EVERY AppProject file in the repo-owned project directories.

    Returns (by_name, entries) where `by_name` maps a project name to the list
    of files declaring it and `entries` is the flat list of every AppProject
    document found, so no file is skipped.

    WHY THIS IS NOT A DICTIONARY OF DOCUMENTS. The previous implementation keyed
    the projects by `metadata.name` and assigned
    `projects[key] = (doc, rel)`. Two files declaring the same name therefore
    meant that the SECOND one silently replaced the first: the earlier file was
    never validated, and the verdict depended on the iteration order of
    PROJECTS_DIRS. Here a duplicate is reported as a FAIL naming both paths,
    and every file is validated on its own.
    """
    by_name = {}
    entries = []
    for d in PROJECTS_DIRS:
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(YAML_SUFFIXES):
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
            entries.append((key, doc, rel))
            by_name.setdefault(key, []).append((doc, rel))

    canonical_rel = os.path.relpath(CANONICAL_PROJECTS_DIR, ROOT)

    # A name declared by more than one file is a conflict, not a preference.
    for key, items in sorted(by_name.items()):
        if len(items) > 1:
            paths = [rel for _doc, rel in items]
            rep.add(
                "appproject-duplicate-name",
                key,
                FAIL,
                f"AppProject {key!r} is declared in {len(items)} files: "
                f"{', '.join(paths)} — one object, one owner; the canonical "
                f"directory is {canonical_rel}",
            )

    # A project outside the canonical directory is the second home that caused
    # the duplicate in the first place.
    for key, _doc, rel in entries:
        if not is_canonical(os.path.join(ROOT, rel)):
            rep.add(
                "appproject-canonical-dir",
                rel,
                FAIL,
                f"AppProject {key!r} is not in the canonical directory "
                f"{canonical_rel}",
            )

    return by_name, entries


def resolve_project(by_name, name):
    """The AppProject document an Application is checked against.

    The canonical one wins; a non-canonical copy is already a FAIL and is only
    used as a fallback so the Application checks still report something useful.
    """
    items = by_name.get(name) or []
    for doc, rel in items:
        if is_canonical(os.path.join(ROOT, rel)):
            return doc
    return items[0][0] if items else None


def check_projects(rep, entries):
    if not entries:
        rep.add(
            "appproject-present",
            os.path.relpath(CANONICAL_PROJECTS_DIR, ROOT),
            FAIL,
            "no AppProject found",
        )
        return
    # EVERY file is checked, not one file per name.
    for name, doc, rel in entries:
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
def check_applications(rep, by_name, repo_map, require_external=False):
    if not os.path.isdir(APPS_DIR):
        rep.add("applications-present", "platform/argocd/applications", FAIL, "directory missing")
        return
    files = [f for f in sorted(os.listdir(APPS_DIR)) if f.endswith((".yaml", ".yml"))]
    if not files:
        rep.add("applications-present", "platform/argocd/applications", FAIL, "no Application found")

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
        project_doc = resolve_project(by_name, proj) if proj else None
        if not proj:
            rep.add("app-project", target, FAIL, "spec.project is required")
        elif project_doc is None:
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
        elif project_doc is not None:
            _, ok_ns = project_allows(project_doc, repo_url, ns)
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
        # Applications targeting initial cloud cutover disable automated sync
        # for reviewed manual first promotion (enforced by check-cloud-cutover.py).
        automated = "automated" in policy
        rep.add(
            "app-sync-policy",
            target,
            OK,
            "automated sync enabled" if automated else "manual sync policy (controlled cutover)",
        )

        # --- cross-repo consistency against the AppProject -----------------
        if project_doc is not None:
            ok_repo, _ = project_allows(project_doc, repo_url, ns)
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
        if require_external:
            if not checkout_origin_matches(checkout, repo_url):
                rep.add("external-origin-match", target, FAIL,
                        "mapped checkout origin does not match Application repoURL")
                continue
            rep.add("external-origin-match", target, OK,
                    "mapped checkout origin matches Application repoURL")
            refreshed, detail = refresh_release(checkout)
            if not refreshed:
                rep.add("external-remote-reachability", target, FAIL, detail)
                continue
        commit = pinned_commit(checkout, rev)
        if not commit:
            rep.add("external-revision-match", target, FAIL,
                    f"targetRevision {rev!r} is not a resolvable main ref or full commit SHA")
            continue
        if require_external:
            reachable, detail = fetched_release_contains(checkout, commit)
            rep.add("external-remote-reachability", target, OK if reachable else FAIL, detail)
            if not reachable:
                continue
        rep.add("external-revision-match", target, OK,
                f"targetRevision {rev[:7]} resolved to {commit}; rendering that commit")
        rendered, error = render_pinned_tree(checkout, commit, subpath)
        if error:
            rep.add("external-render", target, FAIL, error)
            continue
        docs = [d for d in yaml.safe_load_all(rendered) if d]
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
    by_name, entries = collect_projects(rep)
    check_projects(rep, entries)
    check_applications(rep, by_name, repo_map, args.require_external)
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
        f"({len(entries)} AppProject file(s), {len(by_name)} distinct name(s), "
        f"{len(repo_map)} external checkout(s) supplied)"
    )
    if rep.not_present:
        print(
            "NOTE: external repositories were NOT validated. This is not a pass for "
            "those source trees - see EXTERNAL_REPO_NOT_PRESENT rows above."
        )
    return rc


if __name__ == "__main__":
    sys.exit(main())


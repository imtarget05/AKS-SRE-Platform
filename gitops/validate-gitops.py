#!/usr/bin/env python3
"""Cross-repo render validation for the P03 GitOps skeleton (offline, 10-12h slot).

For every Application under ../../gitops/applications, this checks THAT THE
THING THE APP POINTS AT ACTUALLY RENDERS:

  1. source.repoURL + source.path resolve to a checked-out repo + overlay
     (repo URL -> local clone mapping is derived from the URL tail, e.g.
     .../FlashSale-Backend.git -> ~/Downloads/FlashSale-Backend);
  2. `kubectl kustomize <path>` succeeds against that checkout;
  3. every rendered object lands in the Application's declared destination
     namespace (no app in `default`, no cross-namespace bleed);
  4. cross-repo image pins actually appear in the render (P01's api_wrong_registry
     lesson: a repo-wide grep is satisfied by ANY one line, so here we assert each
     workload image is pinned ACR + 40-hex SHA inside ITS OWN document).

Exit 0 only if ALL applications pass. Not a substitute for Argo CD's own
server-side dry-run — that needs a live cluster; this is the offline layer
below it.
"""
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
# Repo URL tail -> local checkout. This is a LOCAL-DEV convenience mapping, not
# infrastructure: it lets the validator resolve repoURL without network access.
REPO_CHECKOUTS = {
    "FlashSale-Backend": os.path.expanduser("~/Downloads/FlashSale-Backend"),
    "Productionized-LegacyApp": os.path.expanduser("~/Downloads/Productionized-LegacyApp"),
}


def fail(msg, failures):
    print(f"FAIL: {msg}", file=sys.stderr)
    failures.append(msg)


def check_app(path, failures):
    app = yaml.safe_load(open(path))
    name = (app.get("metadata") or {}).get("name", os.path.basename(path))
    spec = app.get("spec", {})
    src, dest = spec.get("source") or {}, spec.get("destination") or {}
    repo_url, subpath = src.get("repoURL", ""), src.get("path", "")
    want_ns = dest.get("namespace", "")

    tail = repo_url.rstrip("/").rsplit("/", 1)[-1]
    tail = tail[:-4] if tail.endswith(".git") else tail
    if tail not in REPO_CHECKOUTS or not os.path.isdir(REPO_CHECKOUTS[tail]):
        return fail(f"{name}: no local checkout mapped for repoURL {repo_url!r}", failures)
    overlay = os.path.join(REPO_CHECKOUTS[tail], subpath)
    if not os.path.isdir(overlay):
        return fail(f"{name}: overlay path {subpath!r} missing in {tail}", failures)

    r = subprocess.run(["kubectl", "kustomize", overlay],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return fail(f"{name}: kustomize render failed: {r.stderr.strip()[:300]}", failures)
    docs = [d for d in yaml.safe_load_all(r.stdout) if d]
    if not docs:
        return fail(f"{name}: render produced zero objects", failures)

    for d in docs:
        where = f"{d.get('kind')}/{(d.get('metadata') or {}).get('name')}"
        ns = (d.get("metadata") or {}).get("namespace")
        if ns != want_ns:
            fail(f"{name}: {where} lands in {ns!r}, Application declares {want_ns!r}", failures)
        if ns in (None, "", "default"):
            fail(f"{name}: {where} has no/explicit-default namespace (must be {want_ns!r})", failures)
        # P01 render form: containers list under spec.template.spec.
        pod = (((d.get("spec") or {}).get("template") or {}).get("spec") or {})
        for c in pod.get("containers") or []:
            img = c.get("image", "")
            if not re.fullmatch(r"acrflashsalep6\.azurecr\.io/\S+:[0-9a-f]{40}", img):
                fail(f"{name}: {where}/{c.get('name')} image not pinned (got {img!r})", failures)
    print(f"  ok: {name} ({len(docs)} objects, all in {want_ns})")


def main():
    failures = []
    apps = sorted(f for f in os.listdir(APPS_DIR) if f.endswith((".yaml", ".yml")))
    if not apps:
        print("FAIL: no Applications under gitops/applications", file=sys.stderr)
        return 1
    for f in apps:
        check_app(os.path.join(APPS_DIR, f), failures)
    if failures:
        print(f"\nCROSS-REPO VALIDATION FAILED ({len(failures)} problems)", file=sys.stderr)
        return 1
    print(f"\nALL {len(apps)} applications resolve, render and stay in their namespace.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
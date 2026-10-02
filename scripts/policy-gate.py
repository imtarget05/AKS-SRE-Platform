#!/usr/bin/env python3
"""Static policy + image gate for maintained Kubernetes manifests.

Two rules, both enforceable without a cluster:

IMAGE-RULE (staged; see MANIFEST-INVENTORY.md)
    Phase B  : a `:latest` tag or a placeholder registry fails.
    Phase O  : the gate is upgraded to require `image@sha256:...`.

    The staging is deliberate. Requiring digests before the supply-chain
    pipeline exists would make every manifest permanently red, which teaches
    the reader to ignore this gate. `:latest` is forbidden today; a version tag
    is accepted today; a digest becomes mandatory later.

POLICY-RULE
    Maintained manifests must declare all three probes, resource requests and
    limits, a non-root / least-privilege securityContext, and topology spread.
    Scoped to `deploy/` so the legacy `kubernetes/` tree is judged by
    MANIFEST-INVENTORY.md instead of failing on manifests that are explicitly
    classified as legacy.

Usage:
    python3 scripts/policy-gate.py                   # maintained overlays
    python3 scripts/policy-gate.py --scope all       # also kubernetes/
    python3 scripts/policy-gate.py --require-digest  # Phase O behaviour

Exit 0 when every enabled rule passes, 1 otherwise.
"""
import argparse
import os
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILURES = []


def fail(path, rule, detail):
    FAILURES.append({"file": path, "rule": rule, "detail": detail})


def rel(p):
    return os.path.relpath(p, ROOT)


def kustomize_dirs(scope):
    """Every directory holding a kustomization.yaml we are responsible for."""
    roots = ["deploy"] if scope == "maintained" else ["deploy", "kubernetes"]
    out = []
    for r in roots:
        base = os.path.join(ROOT, r)
        if not os.path.isdir(base):
            continue
        if os.path.isfile(os.path.join(base, "kustomization.yaml")):
            out.append(base)
        for dirpath, _dirs, files in os.walk(base):
            if "kustomization.yaml" in files:
                out.append(dirpath)
    return sorted(set(out))


def render(directory):
    # shell=False is explicit rather than implicit: these are hot-spots, not
    # findings, but a future refactor that reaches for shell=True should have to
    # delete this argument to do it — which is a reviewable diff instead of a
    # silent injection surface. The argument list is fixed and contains no
    # caller-supplied shell string.
    r = subprocess.run(
        ["kubectl", "kustomize", directory],
        capture_output=True,
        text=True,
        timeout=120,
        shell=False,
        check=False,
    )
    if r.returncode != 0:
        fail(rel(directory), "render", f"kubectl kustomize failed: {r.stderr.strip()[:200]}")
        return []
    return [d for d in yaml.safe_load_all(r.stdout) if d]


# ------------------------------------------------------------------ images ----
WORKLOAD_KINDS = ("Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob", "Pod")


def check_images(docs, source, require_digest):
    for d in docs:
        kind = d.get("kind")
        if kind not in WORKLOAD_KINDS:
            continue
        pod = ((d.get("spec") or {}).get("template") or {}).get("spec") or {}
        for c in pod.get("containers") or []:
            img = c.get("image", "")
            name = f"{kind}/{(d.get('metadata') or {}).get('name')}:{c.get('name')}"
            if not img:
                fail(source, "image-present", f"{name} has no image")
            elif "placeholder" in img:
                fail(source, "image-registry", f"{name} uses a placeholder registry: {img}")
            elif img.endswith(":latest"):
                fail(source, "image-tag", f"{name} uses a mutable :latest tag: {img}")
            elif require_digest and "@sha256:" not in img:
                fail(source, "image-digest", f"{name} is not digest-pinned (Phase O): {img}")
            elif ":" not in img.split("/")[-1]:
                fail(source, "image-tag", f"{name} has no explicit tag: {img}")


# ------------------------------------------------------------------ policy ----
def check_pod_spec(docs, source):
    for d in docs:
        kind = d.get("kind")
        if kind not in ("Deployment", "StatefulSet", "DaemonSet"):
            continue
        path = f"{kind}/{(d.get('metadata') or {}).get('name')}"
        tmpl = ((d.get("spec") or {}).get("template") or {})
        pod = tmpl.get("spec") or {}

        if not pod.get("topologySpreadConstraints"):
            fail(source, "topology-spread", f"{path} has no topologySpreadConstraints")

        for probe in ("livenessProbe", "readinessProbe", "startupProbe"):
            # Probes are per-container, not per-pod: a sidecar may legitimately
            # omit one. Checking the pod spec here would fail every Deployment
            # that has an unprobed sidecar, including correct ones.
            missing = [
                c.get("name") for c in pod.get("containers") or [] if probe not in c
            ]
            if missing:
                fail(source, "probes", f"{path} containers {missing} have no {probe}")

        psc = pod.get("securityContext") or {}
        if psc.get("runAsNonRoot") is not True:
            fail(source, "securityContext", f"{path} does not set runAsNonRoot=true")
        if (psc.get("seccompProfile") or {}).get("type") != "RuntimeDefault":
            fail(source, "securityContext", f"{path} does not use RuntimeDefault seccomp")

        for c in pod.get("containers") or []:
            cn = f"{path}:{c.get('name')}"
            res = c.get("resources") or {}
            if not res.get("requests"):
                fail(source, "resources", f"{cn} has no resource requests")
            if not res.get("limits"):
                fail(source, "resources", f"{cn} has no resource limits")

            sc = c.get("securityContext") or {}
            if sc.get("allowPrivilegeEscalation") is not False:
                fail(source, "securityContext", f"{cn} lacks allowPrivilegeEscalation=false")
            if sc.get("readOnlyRootFilesystem") is not True:
                fail(source, "securityContext", f"{cn} lacks readOnlyRootFilesystem=true")
            if "ALL" not in ((sc.get("capabilities") or {}).get("drop") or []):
                fail(source, "securityContext", f"{cn} does not drop ALL capabilities")


def main():
    ap = argparse.ArgumentParser(description="Static manifest policy and image gate")
    ap.add_argument("--scope", choices=["maintained", "all"], default="maintained")
    # IMAGE DIGEST POLICY — what this actually enforces, and why the flag is
    # named the way it is.
    #
    # The bug this replaces: `--require-digest` existed but CI invoked the gate
    # WITHOUT it, so `digest_required=False` and `:latest` passed. A check that is
    # present but switched off is the empty-suite false green this repo forbids
    # elsewhere — the gate was green while the property it existed to enforce was
    # unenforced.
    #
    # What is forbidden by DEFAULT: a MUTABLE tag (`:latest`, or no tag at all).
    # That is a real supply-chain hazard and nothing in this repository needs it.
    #
    # What is NOT forbidden by default: a pinned non-floating tag such as
    # `:0.1.0`. `deploy/base` ships one deliberately, because the digest is not
    # knowable until an image is built, and pretending otherwise would mean
    # inventing a sha256 that resolves to nothing. Pinning to a digest happens at
    # deploy time via `WORKLOAD_IMAGE`, and `--require-digest` is how a reviewer
    # asserts that a given rendered output IS digest-pinned.
    #
    # So: mutable is rejected outright; "is this digest-pinned?" is a question the
    # reviewer asks explicitly. Neither reading can be obtained by accident.
    ap.add_argument(
        "--require-digest",
        action="store_true",
        help=(
            "Additionally require an immutable @sha256 digest. Use when reviewing "
            "a deploy-time-rendered manifest, where the digest is known."
        ),
    )
    args = ap.parse_args()

    dirs = kustomize_dirs(args.scope)
    if not dirs and args.scope == "maintained":
        # No maintained overlay exists yet. That is a real gap in Phase F, not a
        # reason to pass: the gate must not go green by having nothing to check,
        # which is exactly the empty-suite false green this repo forbids.
        fail(
            "deploy",
            "scope",
            "no kustomization.yaml under deploy/ — the repo-owned workload "
            "overlays do not exist yet (Phase F)",
        )
        dirs = []

    total = 0
    for d in dirs:
        docs = render(d)
        total += len(docs)
        check_images(docs, rel(d), args.require_digest)
        check_pod_spec(docs, rel(d))

    if FAILURES:
        print("POLICY GATE FAILED\n")
        for f in FAILURES:
            print(f"  [{f['rule']}] {f['file']}: {f['detail']}")
        print(f"\n{len(FAILURES)} violation(s) across {len(dirs)} kustomize root(s).")
        return 1

    print(
        f"POLICY GATE PASS: {len(dirs)} kustomize root(s), {total} object(s), "
        f"scope={args.scope}, digest_required={args.require_digest}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())


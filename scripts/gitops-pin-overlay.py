#!/usr/bin/env python3
"""Pin Argo CD Application targetRevision fields to immutable commit SHAs.

Reads every Application manifest in a directory (default
platform/argocd/applications) and rewrites each targetRevision to an immutable
40-hex commit SHA:

  * A full 40-hex SHA is left untouched (already pinned).
  * A branch or tag (e.g. ``main``) is resolved via ``git ls-remote
    <repoURL> <ref>`` and rewritten to the resolved SHA.
  * A revision that cannot be resolved causes a non-zero exit: a floating tag
    such as ``main`` is NEVER silently left in place.

Usage:
    python3 scripts/gitops-pin-overlay.py [applications_dir]

Exit codes:
    0  all Applications pinned to SHA (or already pinned)
    1  at least one revision could not be pinned
    2  usage error
"""
import os
import re
import subprocess
import sys

SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, check=False, **kw)


def resolve_sha(repo_url, ref):
    """Resolve a branch/tag ref to a commit SHA via git ls-remote."""
    r = run(["git", "ls-remote", repo_url, ref])
    if r.returncode != 0:
        return None, f"git ls-remote failed: {r.stderr.strip()}"
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    if not lines:
        return None, f"no ref '{ref}' found in {repo_url}"
    sha = lines[0].split()[0]
    if not SHA_RE.match(sha):
        return None, f"unexpected ls-remote output: {r.stdout.strip()!r}"
    return sha, None


def process_dir(app_dir):
    changed = []
    problems = []
    for name in sorted(os.listdir(app_dir)):
        if not name.endswith((".yaml", ".yml")):
            continue
        path = os.path.join(app_dir, name)
        with open(path) as fh:
            text = fh.read()
        # Minimal YAML parse without pyyaml: handle targetRevision lines.
        out_lines = []
        pinned = True
        for line in text.splitlines():
            stripped = line.strip()
            m = re.match(r"^(\s*targetRevision:\s*)(\S+)\s*$", stripped)
            if m:
                indent, rev = m.group(1), m.group(2)
                if SHA_RE.match(rev):
                    out_lines.append(line)  # already pinned
                    continue
                # Floating ref (branch/tag): resolve to SHA.
                # Repo URL is on a `repoURL:` line somewhere earlier in the doc.
                repo_url = None
                for prev in text.splitlines():
                    pm = re.match(r"^\s*repoURL:\s*(\S+)\s*$", prev.strip())
                    if pm:
                        repo_url = pm.group(1)
                if not repo_url:
                    problems.append(f"{name}: no repoURL to resolve targetRevision {rev}")
                    pinned = False
                    out_lines.append(line)
                    continue
                sha, err = resolve_sha(repo_url, rev)
                if err:
                    problems.append(f"{name}: cannot pin {rev} from {repo_url}: {err}")
                    pinned = False
                    out_lines.append(line)
                    continue
                out_lines.append(f"{indent}{sha}")
                changed.append((name, rev, sha))
            else:
                out_lines.append(line)
        if pinned and changed:
            with open(path, "w") as fh:
                fh.write("\n".join(out_lines) + "\n")

    return changed, problems


def main(argv):
    app_dir = argv[1] if len(argv) > 1 else "platform/argocd/applications"
    if not os.path.isdir(app_dir):
        print(f"error: not a directory: {app_dir}", file=sys.stderr)
        return 2
    changed, problems = process_dir(app_dir)
    if changed:
        print("Pinned the following Applications to immutable SHA:")
        for name, rev, sha in changed:
            print(f"  {name}: {rev} -> {sha}")
    else:
        print("No floating targetRevision found; all Applications already pinned to SHA.")
    if problems:
        print("\nFAILED to pin the following:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

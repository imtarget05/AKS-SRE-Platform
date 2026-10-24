#!/usr/bin/env python3
"""Fail-closed preflight before any Argo Application is pointed at real AKS.

This is a configuration gate, not evidence that a workload is running.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
APPS = ROOT / "platform" / "argocd" / "applications"
SHA = re.compile(r"^[0-9a-f]{40}$")


def application_blockers(name: str, doc: dict) -> list[str]:
    source = doc.get("spec", {}).get("source", {})
    destination = doc.get("spec", {}).get("destination", {})
    issues: list[str] = []
    path = source.get("path", "")
    revision = source.get("targetRevision", "")
    if not path or "/local" in path or "/staging" in path:
        issues.append(f"{name}: source.path must be a reviewed cloud overlay, got {path!r}")
    if not SHA.fullmatch(revision):
        issues.append(f"{name}: targetRevision must be an immutable 40-character commit SHA, got {revision!r}")
    if destination.get("namespace") in ("", "default", None):
        issues.append(f"{name}: destination namespace is missing or unsafe")
    if "automated" in doc.get("spec", {}).get("syncPolicy", {}):
        issues.append(f"{name}: cloud cutover requires a reviewed manual first sync")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-dir", type=Path, default=APPS)
    args = parser.parse_args()
    blockers = []
    for name in ("flashsale", "quanlykho", "retail-finance"):
        path = args.app_dir / f"{name}.yaml"
        if not path.is_file():
            blockers.append(f"{name}: missing Application manifest")
            continue
        blockers.extend(application_blockers(name, yaml.safe_load(path.read_text())))
    if blockers:
        for issue in blockers:
            print(f"BLOCKED: {issue}")
        print("Cloud promotion remains blocked. Local/kind GitOps evidence does not satisfy this gate.")
        return 1
    print("Configuration preflight passed; runtime, certificates, data and budget still require separate proof.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

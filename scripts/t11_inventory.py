#!/usr/bin/env python3
"""T11 read-only Azure inventory / validation script.

Reads ONLY local repository files. Makes NO Azure API calls and requires NO
credentials or secrets. Never labels a resource "live".

Modes:
  tf-resources  Inventory Terraform resources in terraform/ and classify each
                into a T11a (compute/network) or T11b (storage/security)
                category with a TERRAFORM_ONLY / NOT_DECLARED / NOT_LIVE label.
  manifests     List kubernetes/ manifests and validate each parses as YAML.
  syntax        py_compile every Python file under scripts/ and tests/.
  all           Run tf-resources + manifests + syntax; exit non-zero on any
                failure.

Exit codes: 0 = all categories verified / no syntax errors; 1 = failure.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environments without pyyaml
    yaml = None

REPO = Path(__file__).resolve().parents[1]
TERRAFORM = REPO / "terraform"
KUBERNETES = REPO / "kubernetes"
SCRIPTS = REPO / "scripts"
TESTS = REPO / "tests"

# T11a compute/network categories -> Terraform resource types this repo declares.
COMPUTE_TYPES = {
    "azurerm_kubernetes_cluster": "AKS cluster",
    "azurerm_kubernetes_cluster_node_pool": "AKS node pool (VMSS-backed nodes)",
}
NETWORK_TYPES = {
    "azurerm_virtual_network": "VNet",
    "azurerm_subnet": "Subnet",
    "azurerm_network_security_group": "Network Security Group",
    "azurerm_network_security_rule": "NSG rule",
    "azurerm_subnet_network_security_group_association": "Subnet-NSG association",
    "azurerm_private_dns_zone": "Private DNS zone",
    "azurerm_private_dns_zone_virtual_network_link": "Private DNS VNet link",
    "azurerm_network_watcher": "Network Watcher",
    "azurerm_network_watcher_flow_log": "NSG flow log",
}
# T11b storage/security categories.
STORAGE_TYPES = {
    "azurerm_storage_account": "Storage account (Blob/File/Disk-capable)",
}
SECURITY_TYPES = {
    "azurerm_role_assignment": "RBAC role assignment",
}

# Resources the T11 scope names but this repo does NOT DECLARE (active terraform).
NOT_DECLARED = {
    "T11a": [
        ("VM (standalone)", "No standalone azurerm_linux_virtual_machine / azurerm_windows_virtual_machine; AKS nodes come from node pools (VMSS)"),
        ("App Service", "No azurerm_app_service or azurerm_app_service_plan declared"),
        ("VPN", "No azurerm_virtual_network_gateway declared"),
        ("Application Gateway", "No azurerm_application_gateway declared"),
        ("Standalone Load Balancer", "No azurerm_lb; AKS provisions a standard LB via network_profile.load_balancer_sku"),
    ],
    "T11b": [
        ("Key Vault", "No azurerm_key_vault / azurerm_key_vault_key declared"),
        ("Blob container", "No azurerm_storage_container declared"),
        ("File share", "No azurerm_storage_share declared"),
        ("Managed disk", "No azurerm_managed_disk declared"),
    ],
}

RESOURCE_RE = re.compile(r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{', re.MULTILINE)


def iter_tf_files(root: Path):
    for path in sorted(root.rglob("*.tf")):
        if ".terraform" in path.parts:
            continue
        yield path


def collect_tf_resources() -> list[dict]:
    resources = []
    for path in iter_tf_files(TERRAFORM):
        text = path.read_text(encoding="utf-8")
        for rtype, rname in RESOURCE_RE.findall(text):
            resources.append({"type": rtype, "name": rname, "file": str(path.relative_to(REPO))})
    return resources


def category_of(rtype: str):
    if rtype in COMPUTE_TYPES:
        return "T11a-compute", COMPUTE_TYPES[rtype]
    if rtype in NETWORK_TYPES:
        return "T11a-network", NETWORK_TYPES[rtype]
    if rtype in STORAGE_TYPES:
        return "T11b-storage", STORAGE_TYPES[rtype]
    if rtype in SECURITY_TYPES:
        return "T11b-security", SECURITY_TYPES[rtype]
    return None, None


def not_declared_cat(group: str) -> str:
    return "T11a-compute" if group == "T11a" else "T11b-security"


def cmd_tf_resources() -> int:
    resources = collect_tf_resources()
    rows = []
    for r in resources:
        cat, label = category_of(r["type"])
        if cat is None:
            continue  # out of T11 scope (kubernetes_manifest, helm_release, data, ...)
        rows.append({
            "resource": f'{r["type"]} "{r["name"]}"',
            "file": r["file"],
            "category": cat,
            "item": label,
            "classification": "TERRAFORM_ONLY",
            "live": False,
            "note": "Declared in Terraform; not applied to Azure. Not live operations.",
        })
    for group, items in NOT_DECLARED.items():
        for item, reason in items:
            rows.append({
                "resource": item,
                "file": "(none)",
                "category": not_declared_cat(group),
                "item": item,
                "classification": "NOT_DECLARED",
                "live": False,
                "note": reason,
            })

    print("# T11 Azure inventory (read-only; local files only; no Azure API)\n")
    print("| Category | Item | File | Classification | Live? |")
    print("|---|---|---|---|---|")
    for row in rows:
        print(f"| {row['category']} | {row['item']} | {row['file']} | {row['classification']} | {'No' if not row['live'] else 'YES'} |")
    print()

    summary = {
        "declared_resources": [r for r in rows if r["classification"] == "TERRAFORM_ONLY"],
        "not_declared": [r for r in rows if r["classification"] == "NOT_DECLARED"],
        "live_resources": [r for r in rows if r["live"]],
    }
    print(json.dumps(summary, indent=2))

    if summary["live_resources"]:
        print("ERROR: live resources reported (unexpected in read-only inventory)", file=sys.stderr)
        return 1
    return 0


def cmd_manifests() -> int:
    if yaml is None:
        print("ERROR: pyyaml not installed; cannot validate manifests", file=sys.stderr)
        return 1
    roots = []
    for path in sorted(KUBERNETES.rglob("*")):
        if path.is_file() and path.suffix.lower() in (".yaml", ".yml"):
            roots.append(path)
    if not roots:
        print("No kubernetes manifests found.", file=sys.stderr)
        return 1
    print("# Kubernetes manifest inventory (syntax check only)\n")
    print("| File | Documents | Valid YAML |")
    print("|---|---|---|")
    ok = True
    for path in roots:
        text = path.read_text(encoding="utf-8")
        try:
            docs = [d for d in yaml.safe_load_all(text) if d]
            valid = True
        except yaml.YAMLError:
            docs = []
            valid = False
            ok = False
        print(f"| {path.relative_to(REPO)} | {len(docs)} | {'Yes' if valid else 'NO'} |")
    print()
    if not ok:
        print("ERROR: one or more manifests failed to parse", file=sys.stderr)
        return 1
    return 0


def cmd_syntax() -> int:
    targets = []
    for directory in (SCRIPTS, TESTS):
        targets.extend(sorted(directory.rglob("*.py")))
    print("# Python syntax check\n")
    print("| File | Compiles |")
    print("|---|---|")
    ok = True
    for path in targets:
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
            result = "Yes"
        except SyntaxError:
            result = "NO"
            ok = False
        print(f"| {path.relative_to(REPO)} | {result} |")
    print()
    if not ok:
        print("ERROR: one or more Python files failed to compile", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="T11 read-only Azure inventory / validation")
    parser.add_argument("mode", choices=["tf-resources", "manifests", "syntax", "all"])
    args = parser.parse_args()

    modes = {
        "tf-resources": cmd_tf_resources,
        "manifests": cmd_manifests,
        "syntax": cmd_syntax,
    }
    if args.mode == "all":
        rc = 0
        for name in ("tf-resources", "manifests", "syntax"):
            print(f"===== mode: {name} =====\n")
            mode_rc = modes[name]()
            if mode_rc != 0:
                rc = 1
        return rc
    return modes[args.mode]()


if __name__ == "__main__":
    sys.exit(main())

"""Print a deliberately allowlisted Terraform change summary for human review.

The full JSON plan may contain secrets and must stay on the ephemeral runner.
Only resource addresses, actions, and selected cost/placement fields are shown.
"""

import json
import re
import sys

FIELDS = (
    ("location",),
    ("sku",),
    ("sku", "name"),
    ("sku_tier",),
    ("vm_size",),
    ("node_count",),
    ("min_count",),
    ("max_count",),
    ("default_node_pool", "vm_size"),
    ("default_node_pool", "node_count"),
    ("default_node_pool", "min_count"),
    ("default_node_pool", "max_count"),
    ("account_tier",),
    ("account_replication_type",),
)
SAFE_VALUE = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")


def find(source, path):
    value = source
    for part in path:
        if isinstance(value, list) and value:
            value = value[0]
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    if isinstance(value, (str, int, float)) and SAFE_VALUE.fullmatch(str(value)):
        return str(value)
    return None


def format_change_row(item: dict) -> str:
    change = item.get("change") or {}
    address = item.get("address", "[unknown]")
    if not isinstance(address, str) or not SAFE_VALUE.fullmatch(address):
        address = "[redacted]"
    actions = ", ".join(change.get("actions") or [])
    before = change.get("before") or {}
    after = change.get("after") or {}
    details = []
    for path in FIELDS:
        old, new = find(before, path), find(after, path)
        if old is not None or new is not None:
            details.append(f"{'.'.join(path)}: {old or '∅'} → {new or '∅'}")
    return f"| `{address}` | {actions} | {'; '.join(details) or 'none allowlisted'} |"


def main() -> int:
    try:
        plan = json.load(sys.stdin)
        changes = plan["resource_changes"]
        if not isinstance(changes, list):
            raise TypeError("resource_changes must be a list")
    except (ValueError, KeyError, TypeError):
        print("invalid Terraform plan summary input", file=sys.stderr)
        return 2

    print("| Resource | Action | Cost and placement fields (before → after) |")
    print("| --- | --- | --- |")
    for item in changes:
        print(format_change_row(item))
    print(f"\nTotal resource changes: {len(changes)}. Full values remain private on the runner.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

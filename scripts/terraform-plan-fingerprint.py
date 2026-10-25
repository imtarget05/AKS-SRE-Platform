"""Print a value-free digest of the complete Terraform JSON plan on stdin.

Only the top-level generation timestamp is ignored. Every planned value,
prior-state value, action, and provider configuration remains covered by the
digest. Never print the JSON: it may contain secrets.
"""

import hashlib
import json
import sys


def main() -> int:
    try:
        plan = json.load(sys.stdin)
    except ValueError:
        print("invalid Terraform plan JSON", file=sys.stderr)
        return 2
    if (not isinstance(plan, dict)
            or not isinstance(plan.get("format_version"), str)
            or not isinstance(plan.get("terraform_version"), str)
            or not isinstance(plan.get("resource_changes"), list)):
        print("Terraform plan JSON lacks required structure", file=sys.stderr)
        return 2
    plan.pop("timestamp", None)
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    print(hashlib.sha256(canonical.encode()).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())

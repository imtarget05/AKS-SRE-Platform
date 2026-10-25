#!/usr/bin/env python3
"""Validate GitHub's live production environment before Terraform mutation.

Input is the JSON response from GET /repos/{owner}/{repo}/environments/production.
GitHub's environment API and reviewer rule are documented at
https://docs.github.com/en/rest/deployments/environments#get-an-environment.
"""

import json
import sys


def validate(environment: object) -> list[str]:
    if not isinstance(environment, dict) or environment.get("name") != "production":
        return ["expected the production environment response"]

    errors = []
    if environment.get("can_admins_bypass") is not False:
        errors.append("administrator bypass must be explicitly disabled")

    rules = environment.get("protection_rules")
    if not isinstance(rules, list):
        return [*errors, "protection rules are missing"]
    reviewer_rules = [rule for rule in rules if isinstance(rule, dict) and rule.get("type") == "required_reviewers"]
    if len(reviewer_rules) != 1:
        return [*errors, "exactly one required-reviewers rule is required"]

    rule = reviewer_rules[0]
    if rule.get("prevent_self_review") is not True:
        errors.append("self-review must be disabled")
    reviewers = rule.get("reviewers")
    if not isinstance(reviewers, list):
        reviewers = []
    reviewer_ids = {
        (reviewer.get("type"), reviewer.get("reviewer", {}).get("id"))
        for reviewer in reviewers
        if isinstance(reviewer, dict)
        and reviewer.get("type") in {"User", "Team"}
        and isinstance(reviewer.get("reviewer"), dict)
        and isinstance(reviewer["reviewer"].get("id"), int)
    }
    if len(reviewer_ids) < 2:
        errors.append("at least two distinct reviewers must be configured")
    return errors


def main() -> int:
    try:
        environment = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("production environment gate: invalid API response", file=sys.stderr)
        return 1
    errors = validate(environment)
    if errors:
        for error in errors:
            print(f"production environment gate: {error}", file=sys.stderr)
        return 1
    print("production environment gate: configured for independent review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

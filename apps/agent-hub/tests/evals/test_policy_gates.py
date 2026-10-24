import json
import os
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
CASEBOOK_PATH = os.path.join(REPO_ROOT, "tests/evals/casebook/phase0_casebook.json")


@pytest.fixture
def casebook():
    with open(CASEBOOK_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_casebook_domain_distribution(casebook):
    """Ensure exact distribution of cases across the 4 systems."""
    assert len(casebook) == 16, f"Expected 16 cases in Phase 0 Casebook, got {len(casebook)}"

    domains = [c["domain"] for c in casebook]
    assert domains.count("retail-finance") == 4
    assert domains.count("opsbridge-flashsale") == 4
    assert domains.count("quanlykho") == 4
    assert domains.count("aks-sre-platform") == 4


def test_zero_mutation_tools_in_citations(casebook):
    """Invariant: 0 write/mutation tools allowed in citations across all cases."""
    mutation_verbs = ["post", "put", "delete", "patch", "requeue", "apply", "rollback", "undo"]

    for case in casebook:
        for citation in case["expected_citations"]:
            cit_lower = citation.lower()
            for verb in mutation_verbs:
                # Citations must only be GET requests or read URLs
                assert not cit_lower.startswith(f"{verb} "), (
                    f"Mutation tool detected in case {case['id']}: {citation}"
                )


def test_security_negative_cases_must_abstain(casebook):
    """Invariant: All security negative cases (cross-scope, privilege escalation) must abstain."""
    security_cases = [c for c in casebook if "Security Negative" in c.get("title", "") or "Injection" in c.get("title", "")]
    assert len(security_cases) >= 4, "Must have at least 4 security negative cases"

    for case in security_cases:
        assert case["must_abstain"] is True, f"Security negative case {case['id']} did not mandate abstain!"
        assert len(case["expected_citations"]) == 0, f"Abstaining security case {case['id']} must not cite sources"


def test_forbidden_actions_defined(casebook):
    """Invariant: Every case must explicitly declare forbidden actions."""
    for case in casebook:
        assert len(case["forbidden_actions"]) > 0, (
            f"Case {case['id']} must have explicit forbidden actions"
        )

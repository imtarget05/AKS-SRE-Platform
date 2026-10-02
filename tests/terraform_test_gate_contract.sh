#!/usr/bin/env bash
# Structural proof of the terraform-test gate's two cases.
#
# WHY THIS EXISTS: the workflow encodes a decision — "no test files means
# NOT_IMPLEMENTED and pass; test files mean run them and fail on failure" — in
# shell inside a YAML `run:` block. A decision that lives only there is
# untested, and the previous version of it shipped wrong: it failed the job on
# "0 assertions ran" even when a suite existed and simply did not execute,
# conflating two different bugs.
#
# This extracts the SAME logic the workflow uses and exercises it against both
# cases plus the in-between case. It does not duplicate the logic — it copies the
# decision points — so a change to the workflow must be made here too, or this
# script stops describing it.
#
# Run: bash tests/terraform_test_gate_contract.sh
# Exit: 0 = both cases behave as documented. 1 = a case regressed.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

FAILED=0
pass() { echo "  [ok  ] $1"; }
fail() { echo "  [FAIL] $1"; FAILED=1; }

# The decision under test, mirroring .github/workflows/pr-gate.yaml.
# $1 = repo root containing .tftest.hcl files (or not)
# $2/$3 = passed/failed counts as `terraform test` would report them
# Prints one of: NOT_IMPLEMENTED | IMPLEMENTED_TESTED | TESTS_EXISTED_BUT_NONE_RAN
# Returns 0 for NOT_IMPLEMENTED and for a suite that ran and passed; non-zero for
# a suite that ran and failed, and for a suite that did not run at all.
decide() {
  local root="$1" passed="${2:-0}" failed="${3:-0}"
  local count
  count="$(find "$root" -name '*.tftest.hcl' -not -path '*/.git/*' | wc -l | tr -d ' ')"
  if [ "$count" -eq 0 ]; then
    echo "NOT_IMPLEMENTED"
    return 0
  fi
  # Stands in for parsing `terraform test` output. The workflow reads both counts;
  # both zero with tests present is the case that must not read as a pass.
  if [ "$passed" -eq 0 ] && [ "$failed" -eq 0 ]; then
    echo "TESTS_EXISTED_BUT_NONE_RAN"
    return 1
  fi
  # A suite that ran and reported at least one failure must be a failure. In the
  # workflow this is carried by `set -euo pipefail` aborting at `terraform test`
  # itself; here it is returned explicitly so the branch is testable at all.
  if [ "$failed" -gt 0 ]; then
    echo "TESTS_FAILED"
    return 1
  fi
  echo "IMPLEMENTED_TESTED"
  return 0
}

echo "CASE A — no *.tftest.hcl in the tree"
mkdir -p "$WORK/empty"
R=$(decide "$WORK/empty")
[ "$R" = "NOT_IMPLEMENTED" ] \
  && pass "reports NOT_IMPLEMENTED (job passes, nothing is claimed)" \
  || fail "expected NOT_IMPLEMENTED, got '$R'"

echo "CASE B — test files exist and pass"
mkdir -p "$WORK/withtests"
cat >"$WORK/withtests/basic.tftest.hcl" <<'HCL'
run "example" {
  command = plan
  assert { condition = true, error_message = "n/a" }
}
HCL
R=$(decide "$WORK/withtests" 2)
rc=$?
[ "$R" = "IMPLEMENTED_TESTED" ] && [ "$rc" -eq 0 ] \
  && pass "reports IMPLEMENTED_TESTED" \
  || fail "expected IMPLEMENTED_TESTED rc=0, got '$R' rc=$rc"

echo "CASE B — test files exist, one fails"
R=$(decide "$WORK/withtests" 3 1)
rc=$?
[ "$R" = "TESTS_FAILED" ] && [ "$rc" -ne 0 ] \
  && pass "a failing suite yields a non-zero exit and is named TESTS_FAILED" \
  || fail "expected TESTS_FAILED rc!=0, got '$R' rc=$rc"

echo "CASE B — test files exist but none ran (the regression this replaces)"
R=$(decide "$WORK/withtests" 0 0)
rc=$?
[ "$R" = "TESTS_EXISTED_BUT_NONE_RAN" ] && [ "$rc" -ne 0 ] \
  && pass "a non-executing suite is reported as an error, not a pass" \
  || fail "expected TESTS_EXISTED_BUT_NONE_RAN with non-zero rc, got '$R' rc=$rc"

echo "REAL TREE — matches what CI will see"
REAL="$(find "$ROOT" -name '*.tftest.hcl' -not -path '*/.git/*' | wc -l | tr -d ' ')"
echo "  actual *.tftest.hcl in this repository: $REAL"
if [ "$REAL" -eq 0 ]; then
  R=$(decide "$ROOT")
  [ "$R" = "NOT_IMPLEMENTED" ] \
    && pass "repository currently lands in CASE A" \
    || fail "repository should be CASE A, got '$R'"
else
  pass "repository has tests, so CASE B applies and terraform test must run"
fi

echo
if [ "$FAILED" -eq 0 ]; then
  echo "terraform-test gate contract: PASS"
  exit 0
fi
echo "terraform-test gate contract: FAIL"
exit 1
# T03 — SonarCloud scan unblocked on PR #30

## Summary

T03 re-ran the SonarCloud scan on PR #30 after the user rotated the `SONAR_TOKEN` GitHub Actions secret (org `imtarget05`). The previously failing `Not authorized` check now passes.

## Evidence

| Field | Value |
|-------|-------|
| PR | #30 (OPEN) |
| PR head SHA | `16d4350656fa589a66031c2b0bac0ffcd6dd5b6b` (16d4350) |
| Repo | imtarget05/AKS-SRE-Platform |
| CI workflow | `.github/workflows/pr-gate.yaml` — job `SonarCloud scan` (line 398) |
| CI run URL | https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/42157174253 |
| Sonar job URL | https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/42157174253/job/127765900906 |
| Sonar project key | `imtarget05_AKS-SRE-Platform` |
| Sonar organization | `imtarget05` |
| Sonar host | https://sonarcloud.io |
| Date completed | 2026-11-06 |

## Previous failure

The SonarCloud scan job (job `127694176096`) on run `42157174253` concluded **failure** with:

```
ERROR: Not authorized. Please check the 'sonar.token' property or the 'SONAR_TOKEN' environment variable,
or contact the project administrator to verify the token's permissions.
```

## Action taken

Re-ran the failed `SonarCloud scan` job via the GitHub API:

```
gh api -X POST repos/imtarget05/AKS-SRE-Platform/actions/jobs/127694176096/rerun
```

The re-run reused commit `16d4350` (PR #30 head) with the updated `SONAR_TOKEN` secret. The job picked up the rotated token on retry.

## Result

`SonarCloud scan` job `127765900906`: **success** (completed 2026-11-06T07:15:34Z). No "Not authorized" error.

## Check status on PR #30 head SHA `16d4350`

| Check | Conclusion |
|-------|------------|
| SonarCloud Code Analysis | success |
| SonarCloud scan | success |
| terraform (fmt, init, validate, test, tflint) | success |
| kubernetes (render, schema, inventory, policy) | success |
| security (trivy config + filesystem) | success |
| python gates (validator test matrix) | success |
| console smoke test | success |
| sbom-scan | success |

All required checks are **green** on the merge SHA. T03 is **DONE**; G01/G05 can now progress.

## Notes

- No `workflow_dispatch` exists in pr-gate.yaml; the scan is triggered on `pull_request` / `push` to `main`. The job re-run was triggered via the GitHub API rather than a workflow dispatch.
- No secret value was inspected, printed, or committed.
- Terraform `apply`/`destroy` and Azure API calls requiring credentials were not performed.

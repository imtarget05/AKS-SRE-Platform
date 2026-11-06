# T03 — SonarCloud unblock for PR #30 (commit 16d4350) — BLOCKED

Status: **BLOCKED**. PR #30 is OPEN at commit `16d4350` (`docs(evidence): record PR CI results`), ancestor of current HEAD. The SonarCloud scan cannot be completed because the `SONAR_TOKEN` GitHub secret is not authorized for the Sonar project.

## What is blocked

PR #30's PR-gate run (candidate SHA `25b8e9f`) passed the Kubernetes, security, Python, Terraform, and console jobs. **SonarCloud failed with `Not authorized`.** No token value was inspected, read, or injected. The SonarCloud check must not be represented as a code pass.

Sonar project identity (from `sonar-project.properties`):
- `sonar.projectKey = imtarget05_AKS-SRE-Platform`
- `sonar.organization = imtarget05`
- `sonar.host.url = https://sonarcloud.io`

The `sonar` job in `.github/workflows/pr-gate.yaml` reads `SONAR_TOKEN` from GitHub repository secrets and runs `sonar-scanner` with `-Dsonar.login="$SONAR_TOKEN"`. A `Not authorized` failure means the token lacks permission to analyze project `imtarget05_AKS-SRE-Platform` in organization `imtarget05`.

## What you (the user) need to provide

SonarCloud project admin action via the SonarCloud admin UI (not something this session can do):

1. Sign in to SonarCloud as an admin of organization `imtarget05`.
2. Open project `imtarget05_AKS-SRE-Platform` (or create it if it does not exist).
3. Bind/authorize the token used by the GitHub secret `SONAR_TOKEN`:
   - Option A: regenerate a project/user token on SonarCloud with permission to analyze `imtarget05_AKS-SRE-Platform`, and set it as the GitHub repository secret `SONAR_TOKEN` (repository Settings → Secrets and variables → Actions).
   - Option B: if the token is valid but the repo isn't bound to the project, add repository `imtarget05/AKS-SRE-Platform` to the Sonar project (Administration → General Settings → GitHub binding) or grant the token's owning user the project's `Execute Analysis` permission.
4. Re-run the `sonar` job on PR #30 (re-trigger the PR or push to the PR branch).

Do not share the token value with this session. No secret may be committed to the repo.

## Offline evidence already ready (6 of 7 checks green; Sonar is the 7th, blocked)

All verified locally in this session (no Azure, no secrets):

| Check | Command | Result | Exit code |
|---|---|---|---|
| Terraform formatting | `terraform fmt -check -recursive` | PASS | 0 |
| Terraform validate | `terraform validate` for 5 roots | PASS, all valid | 0 |
| Terraform native tests | `terraform test` for 5 roots | PASS, 16 passed / 0 failed | 0 |
| Python tests | `python3 -m pytest -q tests` | PASS, coverage 86.74% (min 75%) | 0 |
| GitOps gate matrix | `python3 tests/test_gates.py` | PASS, 62 passed / 0 failed (G1–G16) | 0 |
| Kustomize render | `kubectl kustomize` for 10 roots | PASS, all rendered | 0 |
| Trivy config (HIGH/CRITICAL) | `trivy config --severity HIGH,CRITICAL --exit-code 1 ... .` | PASS, clean | 0 |
| Trivy fs secrets | `trivy fs --scanners secret --severity HIGH,CRITICAL --exit-code 1 ... .` | PASS, clean | 0 |
| SonarCloud scan | `sonar-scanner ...` (CI `sonar` job) | BLOCKED: `Not authorized` | — |

CI URLs for the base SHA (recorded in `docs/evidence/2026-11-06-offline-validation.md`):
- pr-gate: https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/42070399687
- gitops-validate: https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/42070399926
- Source SBOM scan: https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/42070399700
- oidc-azure: https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/42070399516

PR #30 candidate-SHA CI:
- PR-gate run: https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/42157000452 (Sonar failed `Not authorized`; all other jobs passed)
- Source SBOM scan: https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/42157000461

## Status

T03 = **BLOCKED** until Sonar project admin authorization is provided. Offline evidence is complete and ready to present once the scan is unblocked. No fake/green Sonar result will be claimed.

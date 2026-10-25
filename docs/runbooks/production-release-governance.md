# Production Release Governance

This document defines the release governance model for the AKS-SRE-Platform repository.
It covers infrastructure (Terraform), application (LegacyApp), and GitOps releases.

---

## 1. Governance Principles

1. **Two-Reviewer Minimum**: Every production release requires at least two distinct reviewers.
2. **No Self-Review**: The person triggering a release cannot approve it.
3. **Branch Protection**: `main` branch requires review from CODEOWNERS.
4. **Evidence-Based**: Gates verify live configuration, not just local state.
5. **Traceability**: Every release is tied to a Git SHA with immutable artifacts.

---

## 2. GitHub Environment Configuration

### Production Environment (Required for All Releases)

In **Settings → Environments → production**, configure:

| Setting | Value | Rationale |
|---------|-------|-----------|
| Required reviewers | ≥ 2 distinct users/teams | Ensures independent review |
| Prevent self-review | **Enabled** | Dispatcher cannot approve own release |
| Allow administrators to bypass | **Disabled** | No exceptions to review policy |
| Wait timer | 0 minutes | No artificial delays; review is the gate |
| Deployment branches | `main` only | Only protected branch can deploy |

**Verification**: Run `scripts/check-production-environment.py` against the live GitHub API:
```bash
gh api repos/imtarget05/AKS-SRE-Platform/environments/production | python3 scripts/check-production-environment.py
```
Exit code 0 = configured correctly. Any other code = misconfigured.

---

## 3. Branch Protection Rules

### `main` Branch

In **Settings → Branches → Branch protection rules → Add rule for `main`**:

| Rule | Setting | Notes |
|------|---------|-------|
| Require a pull request before merging | **Enabled** | All changes via PR |
| Required approvals | **2** | Two distinct reviewers |
| Dismiss stale approvals on new commits | **Enabled** | Force re-review on changes |
| Require review from CODEOWNERS | **Enabled** | Enforces ownership |
| Require status checks to pass before merging | **Enabled** | See Required Checks below |
| Require branches to be up to date before merging | **Enabled** | Prevent stale merges |
| Require conversation resolution before merging | **Enabled** | All comments addressed |
| Require signed commits | **Enabled** | GPG/Sigstore verification |
| Require linear history | **Enabled** | No merge commits on main |
| Include administrators | **Enabled** | No bypass for admins |
| Restrict who can push to matching branches | **Enabled** | Only via PR merge |
| Allow force pushes | **Disabled** | History is immutable |
| Allow deletions | **Disabled** | Branch cannot be deleted |

### Required Status Checks (must pass before merge)

1. `pr-gate` / `terraform (fmt, init, validate, test, tflint)`
2. `pr-gate` / `kubernetes (render, schema, inventory, policy)`
3. `pr-gate` / `security (trivy config + filesystem)`
4. `pr-gate` / `python gates (validator test matrix)`
5. `pr-gate` / `cloud cutover guard unit tests`
6. `pr-gate` / `Azure origin renderer unit tests`
7. `pr-gate` / `origin mTLS positive and negative controls`
8. `pr-gate` / `protected Terraform destroy contract`
9. `pr-gate` / `Cloudflare API edge contract`
10. `legacyapp-ci` / `test-and-scan` (when legacy paths changed)
11. `legacyapp-ci` / `docker-build-scan` (when legacy paths changed)
12. `legacyapp-ci` / `manifest-validation` (when legacy paths changed)

---

## 4. CODEOWNERS

File: `.github/CODEOWNERS` (must exist at repository root)

```
# Platform infrastructure - requires platform team review
/terraform/                       @platform-team
/kubernetes/                      @platform-team
/deploy/                          @platform-team
/gitops/                          @platform-team
/platform/                        @platform-team
/scripts/bootstrap.sh             @platform-team
/scripts/check-production-environment.py @platform-team

# Legacy application - requires legacy team review
/apps/legacy-inventory/           @legacy-team

# Observability & SRE - requires SRE team review
/deploy/base/observability/       @sre-team
/docs/slo.md                      @sre-team
/scripts/log_scale_events.py      @sre-team
/scripts/alert_drill_simulator.py @sre-team

# Security - requires security team review
/.trivyignore                     @security-team
.github/workflows/                @security-team

# Documentation - requires docs team review
/docs/                            @docs-team
```

**Rule**: Any PR touching files matching a pattern requires approval from the listed team(s). A single reviewer cannot satisfy multiple team requirements.

---

## 5. Release Workflows & Gates

### 5.1 AKS Infrastructure Release (`aks-deploy.yml`)

**Trigger**: `workflow_dispatch` with `action: apply` or `destroy`

**Jobs**:
1. `plan` — Terraform plan with fingerprint (reviewable artifact)
2. `sbom-scan` — **NEW**: Verify image digest, generate SBOM, Trivy CRITICAL scan
3. `apply` / `destroy` — Gated by `production` environment + manual approval

**Pre-conditions for `apply`/`destroy`**:
- [ ] `plan` job completed with fingerprint recorded
- [ ] `sbom-scan` job passed (image digest verified, no CRITICAL vulns)
- [ ] Production environment approval granted by **independent reviewer**
- [ ] `check-production-environment.py` passes (live config verified)
- [ ] Current plan fingerprint matches reviewed fingerprint

### 5.2 Legacy Application Release (`legacyapp-ci.yml`)

**Trigger**: Push to `main` with changes under `apps/legacy-inventory/**`

**Jobs**:
1. `test-and-scan` — npm test + Trivy fs (secrets, HIGH/CRITICAL vulns)
2. `docker-build-scan` — Build image + Trivy image scan (HIGH/CRITICAL)
3. `detect-changes` — Skip release for docs-only changes
4. `release-push` — OIDC → ACR push `<sha>` → digest verify
5. `gitops-update` — Pin prod overlay to `<sha>` → bot commit

**Pre-conditions for `release-push`**:
- [ ] All quality gates passed (`ci-gate` aggregate)
- [ ] Changes are runtime changes (not docs-only)
- [ ] Not triggered by `github-actions[bot]`

**Pre-conditions for `gitops-update`**:
- [ ] `release-push` succeeded (image digest verified)
- [ ] Production environment approval granted by **independent reviewer**
- [ ] `check-production-environment.py` passes (live config verified)

### 5.3 PR Gate (`pr-gate.yml`)

**Trigger**: Pull request or push to `main`

**Jobs** (all must pass):
- Terraform validation (fmt, init, validate, test, tflint)
- Kubernetes manifest validation (render, schema, inventory, policy)
- Security scans (Trivy config + filesystem)
- Python validator test matrix (G1-G16)
- Contract tests (cloud cutover, Azure origin, mTLS, destroy workflow)

---

## 6. Release Artifacts & Evidence

### Required for Every Production Release

| Artifact | Source | Retention |
|----------|--------|-----------|
| Terraform plan fingerprint | `aks-deploy.yml` / `plan` job | 90 days (GitHub Actions) |
| Terraform plan summary | `aks-deploy.yml` / `plan` job | 90 days |
| Image digest (SHA256) | `legacyapp-ci.yml` / `release-push` job | Permanent (ACR) |
| SBOM (SPDX JSON) | `aks-deploy.yml` / `sbom-scan` job | 90 days |
| Trivy SARIF results | `aks-deploy.yml` / `sbom-scan` job | GitHub Security tab |
| GitOps commit SHA | `legacyapp-ci.yml` / `gitops-update` job | Git history |
| Production approval record | GitHub Environment audit log | Permanent |

### Evidence Checklist (attach to release PR)

- [ ] Terraform plan reviewed and fingerprint recorded
- [ ] SBOM generated and uploaded as artifact
- [ ] Trivy scan: **0 CRITICAL vulnerabilities**
- [ ] Image digest matches released SHA
- [ ] Production environment approval by **reviewer ≠ dispatcher**
- [ ] `check-production-environment.py` passes at release SHA
- [ ] GitOps overlay pinned to correct digest
- [ ] Argo CD sync verified (if applicable)

---

## 7. Emergency Override Procedure

**Use only for production incidents requiring immediate remediation.**

1. **Incident Commander** declares emergency in `#incidents` channel
2. **Two reviewers** (one must be from `@platform-team`) approve via GitHub Environment
3. Dispatch `aks-deploy.yml` with `action: apply` using **hotfix SHA**
4. Document in `docs/incidents/YYYY-MM-DD-<slug>.md` within 24 hours:
   - Incident timeline
   - Why normal process was bypassed
   - What changed
   - Follow-up actions
5. Post-incident review within 5 business days

**Never**: Disable branch protection, bypass CODEOWNERS, or skip Trivy scans.

---

## 8. Compliance & Auditing

### Quarterly Review
- Verify production environment configuration matches this document
- Verify branch protection rules match this document
- Verify CODEOWNERS covers all critical paths
- Review last 10 releases for governance compliance
- Update this document if processes change

### Audit Trail
All release evidence is discoverable via:
- GitHub Actions run history (`aks-deploy.yml`, `legacyapp-ci.yml`)
- GitHub Environment deployment history (`production`)
- Git commit history (`main` branch, bot commits)
- ACR manifest metadata (image digests)
- GitHub Security tab (Trivy SARIF uploads)

---

## 9. References

- [GitHub Environment Protection Rules](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)
- [GitHub Branch Protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/managing-branch-rulesets)
- [GitHub CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- `scripts/check-production-environment.py` — validation logic
- `tests/test_production_environment_gate.py` — contract tests
- ADR-015: Argo CD AppProject canonical location
- ADR-017: SBOM/Provenance gate for production releases
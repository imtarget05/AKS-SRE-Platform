# T11c — GitHub Actions mapping + read-only inventory script (read-only)

## Existing GitHub Actions workflows (present)

| Workflow file | Trigger | Present? | Maps to (JD tooling equivalent) | JD equivalent present? |
|---|---|---|---|---|
| `.github/workflows/pr-gate.yaml` | PR + push to main | YES | Azure DevOps pipeline (`pr-gate`) / GitLab CI (`pr-gate` job) / Jenkins (`pr-gate` job) | NOT_YET (no ADO/GitLab/Jenkins pipeline definition exists in this repo) |
| `.github/workflows/gitops-validate.yaml` | PR (gitops/platform/argocd paths) + push main + dispatch | YES | ADO GitOps validation stage / GitLab `gitops-validate` job / Jenkins GitOps validation job | NOT_YET |
| `.github/workflows/oidc-azure.yaml` | PR (self path) + dispatch + push main | YES | ADO OIDC service connection / GitLab OIDC / Jenkins Azure OAuth | NOT_YET (contract only; `OIDC_LIVE_LOGIN = NOT_VERIFIED`) |
| `.github/workflows/aks-deploy.yml` | — | YES | ADO AKS deploy stage / GitLab deploy job / Jenkins AKS deploy job | NOT_YET |
| `.github/workflows/sonobuoy-sbom.yml` | — | YES | ADO SBOM stage / GitLab dependency scanning / Jenkins SBOM job | NOT_YET |

All five workflows are GitHub Actions-native. No Azure DevOps (`azure-pipelines.yml`), GitLab (`.gitlab-ci.yml`), or Jenkins (`Jenkinsfile`) pipeline definition exists in this repo, so every JD-tooling mapping is `NOT_YET`. This is stated accurately; no mapping is claimed as implemented.

## Mapping notes (state accurately)

- `pr-gate.yaml`: Terraform fmt/validate/test/tflint, kustomize render, kubeconform, manifest inventory, policy gate, Trivy config+fs, Python gate matrix (G1–G16), SRE agent coverage, SonarCloud scan (blocked: `Not authorized`, see T03). `permissions: contents: read`.
- `gitops-validate.yaml`: repo-owned GitOps validation at pinned Application revisions, external-repo honesty gate, gate test matrix (G1–G15), negative control (M-B1). Read-only; cannot deploy/sync. `permissions: contents: read`.
- `oidc-azure.yaml`: OIDC contract (static, no Azure), unbound-token negative control fixture, live job gated on `vars.AZURE_CLIENT_ID` (skipped → `NOT_VERIFIED`), status summary. Workflow-level `contents: read`; `id-token: write` scoped to the `live` job only. No client secret referenced.
- `aks-deploy.yml` / `sonobuoy-sbom.yml`: present in `.github/workflows/`; not detailed in this slice.
- SonarCloud: `sonar-project.properties` (`imtarget05_AKS-SRE-Platform`, org `imtarget05`). Scan blocked on `SONAR_TOKEN` authorization (T03).

## Read-only inventory/validation script: `scripts/t11_inventory.py`

Single script (T11c deliverable). Modes:

- `tf-resources`: inventories Terraform resources in `terraform/`, classifies each into T11a/T11b category with `TERRAFORM_ONLY` / `NOT_DECLARED` / `NOT_LIVE` label. Never labels anything live. No Azure API, no credentials.
- `manifests`: lists `kubernetes/` manifests and validates each parses as YAML.
- `syntax`: `py_compile` every Python file under `scripts/` and `tests/`.
- `all`: runs every mode; non-zero exit on any failure.

Verification (this session, local):
- `python3 scripts/t11_inventory.py tf-resources`: exit 0; zero `live_resources`.
- `python3 scripts/t11_inventory.py manifests`: exit 0; all manifests valid YAML.
- `python3 scripts/t11_inventory.py syntax`: exit 0; all Python files compile.
- `python3 scripts/t11_inventory.py all`: exit 0.
- `python3 -m pytest tests/test_t11_inventory.py`: passes (category assertions + no-live assertion).

No Azure API calls are made; no secrets or credentials are read or emitted.

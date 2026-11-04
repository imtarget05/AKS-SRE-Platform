# Three-repository cloud acceptance baseline — 2026-11-04 UTC

This is a read-only inventory, not a deployment or production acceptance. The
three working trees contain pre-existing uncommitted work, so no current release
SHA or cross-repository score can be certified yet. Health responses are recorded
as reachability only. Sanitized command output is retained in
[`2026-11-04-cloud-inventory.log`](2026-11-04-cloud-inventory.log).

## Frozen scoring rule

| Repository | Denominator | Frozen source |
| --- | ---: | --- |
| AKS-SRE-Platform | 14 | A01–A16 excluding A09/A10 in `2026-11-03-verification-checkpoint.md` |
| QuanLyKho | 21 | QLK IDs in its `docs/qa/2026-11-03-verification-checkpoint.md` |
| CreditFlow | 22 | 14 implemented controls and 8 open acceptance gates in its `docs/qa/ENTERPRISE_READINESS_2026-11-03.md` |

For each repository, score = accepted gate count / frozen denominator. Portfolio
score = `(AKS score + QuanLyKho score + CreditFlow score) / 3`. A gate counts only
when the expected behavior has raw, dated evidence in its required environment
and the evidence identifies the same immutable release SHA and cloud image
digest/revision. An untested gate, a skipped test without accepted reason, an old
release, or a mere health check counts as OPEN. Do not change a denominator to
raise the score. Production go-live decisions are recorded separately by the
system's owners; a portfolio score above 90% alone does not authorize go-live.

## Read-only observations

| System | Observation | Acceptance implication |
| --- | --- | --- |
| AKS | Azure CLI reports `aks-portfolio-dev` Running, Kubernetes 1.36, Free control-plane tier, one 3-node `Standard_D2s_v6` pool. `kubectl --context aks-portfolio-dev-admin get nodes -o wide` returned 3/3 Ready at v1.36.5. | A live cluster exists, but application runtime and policy enforcement remain OPEN. Free tier does not make the nodes free. |
| AKS | `kubectl --context aks-portfolio-dev-admin get deploy -A` showed system deployments only; `get applications.argoproj.io -A` reported that the resource type does not exist. The normal `aks-portfolio-dev` context cannot authenticate on this host because `kubelogin` is missing. | No Argo CD or maintained application is verified on Azure. The admin context was used for read-only inventory only. |
| AKS | The remote blob `stakssre/tfstate/aks-sre/validation.terraform.tfstate` exists (34,429 bytes, last modified 2026-11-03 15:08 UTC, unlocked). | State ownership and reconciliation with the local backend remain OPEN; existence alone does not establish which state is authoritative. |
| QuanLyKho | `GET` to the documented Modal API `/api/v1/health/live` returned HTTP 200; the documented Cloudflare web root returned HTTP 200. | Reachability only. The 21 MVP journeys, migration, release identity, device UAT and rollback remain OPEN. |
| CreditFlow | Azure CLI reports Container App `creditflow-api` revision `creditflow-api--mbcr9yc`, created 2026-11-03 08:56 UTC, with FQDN `creditflow-api.proudstone-70150af3.southeastasia.azurecontainerapps.io`. `/health/live` returned HTTP 200 on one probe, timed out after 15 seconds on another, then returned 200 on retry. | Reachability is intermittent and is not a readiness verdict. The live image is `crportfolioa3deec.azurecr.io/creditflow-api:latest`, so it cannot be traced to an immutable source SHA. |
| CreditFlow | Azure Container App environment variable names include OIDC fields but do not include `CREDITFLOW_ENV`. At inventory time, the published CD and documentation still named an older `blackisland` FQDN; the local workflow and docs have since been corrected but are not deployed. | Production mode, current frontend/API alignment and bank integration acceptance remain OPEN. Do not send real applicant data. |
| CreditFlow | GitHub repository secrets list includes `AZURE_CREDENTIALS` and `CREDITFLOW_API_KEY`, but no `CREDITFLOW_OIDC_ISSUER`, `CREDITFLOW_OIDC_AUDIENCE`, `CREDITFLOW_OIDC_JWKS_URL` or `CREDITFLOW_OIDC_ROLE_MAP_JSON`. Only secret names were inspected. | The production deploy script's required IdP gate cannot pass yet; do not substitute fictional IdP values in production. |

The earlier AKS `pr-gate` and SBOM runs failed on SHA `0dac76e`. Draft
[AKS PR #18](https://github.com/imtarget05/AKS-SRE-Platform/pull/18) now has
green PR-gate, source SBOM, SonarCloud, Terraform, Kubernetes, security and
Python jobs on its committed branch; this is CI evidence, not Azure workload
acceptance. QuanLyKho CI and S11 E2E failed on SHA `7b602e3`; CreditFlow's
successful `verify-azure` job on SHA `c5a1893` was read-only. Their local fixes
still need CI evidence on immutable release candidates.
CreditFlow already has 14 fictional `/predict` cases in `data/demo/app_cases.json`;
the fixture validator and its test passed locally. These cases are synthetic
contract evidence only and cannot close bank-owned acceptance gates.

## Release evidence required next

1. Identify and review the existing uncommitted changes, then select one
   immutable candidate SHA for each repository. Record its image digest,
   frontend release identity, CI run URLs and rollback target.
2. Run each frozen gate against that candidate in its required environment;
   retain sanitized raw output with UTC timestamp, command, expected and actual
   result, owner and environment. Record PASS, FAIL or OPEN by ID.
3. Recompute the three percentages and portfolio mean from those ID rows.
   Publish the numerical result only after evidence is linked; collect separate
   production approvals for AKS, QuanLyKho and CreditFlow.

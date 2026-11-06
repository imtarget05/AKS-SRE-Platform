# Wave 3 live reconciliation — 2026-11-06T11:13Z

This snapshot supersedes the status claims in the external Wave 3 summary where they conflict with live checks. It does not replace the underlying logs or owner approval.

| System | Candidate local HEAD | Current evidence | Release status |
| --- | --- | --- | --- |
| AKS-SRE | `e8d99a0d07604bf5bb1b628ca0a99595d9f84f32` | `pr-gate` and SBOM workflows succeeded on this SHA. AKS has 3 Ready nodes. Argo CD application is `Synced` at older revision `7633cad`, health `Degraded`; `flashsale/order-worker` uses a placeholder image and is `ImagePullBackOff`. Prometheus and Alertmanager pods are `Pending` because the user node has reached its pod limit and system nodes are tainted. | **NO-GO** |
| QuanLyKho | `4e812ba42d88dba0a538b8d02e293f7e8a2552ff` | CI succeeded. Latest Render staging deploy `dep-dbmqs80u01pc739duhbg` is `build_failed`: service is configured as Python with repository root, so `poetry install --with dev` cannot find `pyproject.toml` under `backend/`. Public health request timed out after 30 seconds. The repository `render.yaml` specifies Docker, but the existing service does not match it. | **NO-GO** |
| FlashSale | `332859c5456bb53ef639d7bd6d02535f7e44933e` | Java CI succeeded; preview/production deploy workflow failed. Latest Render preview deploy `dep-dbmqqc68bjmc73dvsu7g` is `update_failed`: application logs show PostgreSQL `UnknownHostException: postgres`, the Compose hostname. Public health request timed out after 30 seconds. Render PostgreSQL and Redis preview resources exist, but this does not prove application configuration or a working RabbitMQ dependency. | **NO-GO** |

## Cloud and cost checks

- Azure subscription is enabled. Budget `portfolio-validation-100usd-202611` exists at **USD 100 monthly**, with actual-spend notifications at 80% and 100% and a forecasted notification at 100%. Azure reported current spend **USD 58.35** when queried. A budget is an alert, not an enforced spending cap.
- `rg-aks-validation-t13` returned `ResourceGroupNotFound` at 2026-11-06T11:13Z. The validation resource group teardown has completed.
- A Cost Management export destination was not verified in this check. Keep C1 export OPEN until there is a named owner, destination, schedule, and successful export artifact.
- GitHub secret **names** are present across the three repositories. This does not verify that their values are valid, scoped correctly, or rotated after exposure.

## Release blockers

1. Rotate/revoke the credentials and deploy hooks exposed in the conversation, then update their consumers. Treat existing values as compromised. Do not place replacement values in chat, source, logs, or this document.
2. Repair the two Render preview deployments and run health plus business-flow checks against the actual deployed SHA. The Render CLI session is authenticated, but its `services update` command refuses switching an existing service from Python to Docker; the QuanLyKho service needs a Render API/dashboard reconfiguration or a replacement service.
3. Restore monitoring/alerting and remove the placeholder workload or provide a real immutable image; verify Argo CD health and revision against the candidate.
4. Run measured backup/restore, rollback, UAT, and production smoke evidence. Documentation of a drill is not evidence that the drill ran.
5. Obtain named release/security/system owners, cost-export ownership, UAT/security sign-off, and separate human go/no-go decisions. Demo payment cannot be described as real PSP production processing.

Commands used: `gh run list`, `render deploys list`, `render logs`, `render services`, `az account show`, `az consumption budget show`, `az group show`, `kubectl get/describe`, and public `curl` health probes. No credential values were read into this file.

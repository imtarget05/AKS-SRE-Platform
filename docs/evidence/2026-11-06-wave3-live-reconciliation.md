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

## Follow-up — 2026-11-06T12:10Z

- Render deploy `dep-dbmrhurm8hqs73b8l140` for `sre-demo-api` is `live` at older SHA `f064ad3`; public `/health/live` returned HTTP 200. This is not the current AKS local HEAD.
- Render deploy `dep-dbmrhv49v7es73ail6v0` for the separate Docker service `kho-tra-sua-fastapi` is `live` at QuanLyKho SHA `4e812ba`; public `/api/v1/health/live` returned HTTP 200 after the free-tier instance woke. An empty login request returned HTTP 422, establishing that the endpoint responds without a 503 for this negative case. Valid login and 21 UAT journeys remain untested. The older Python staging service remains a separate failed configuration.
- FlashSale preview deploy `dep-dbmrnc6i0phs73clta20` is `update_failed` at SHA `332859c`; logs still show `UnknownHostException: postgres`. A Render PostgreSQL database and Redis instance for preview already exist and are `available`; their existence does not establish that the app uses their connection settings. No verified RabbitMQ or approved OIDC configuration was found.
- FlashSale PR #20 was reduced to the F04 evidence file plus removal of `JWT_SIGNING_KEY` from the two production-profile Render service declarations. Its blueprint `verify` check passed on head `ac3d575`; Java CI was still running at this snapshot. An unsigned, unchecked approval template is in draft PR #21. Neither PR is a go-live approval.

## Later FlashSale deploy check — 2026-11-06T12:13Z

- Render preview deploy `dep-dbms7cdckfvc738vq740` at `469ee7dd760db5e8d7a097b35beadc4836bcbf12` finished `update_failed`. Application logs again show `java.net.UnknownHostException: postgres`. GitHub's FlashSale Preview and Production Deploy workflow for this SHA also failed. This is a configuration blocker at the current remote `main`, not a missing Render PostgreSQL resource.

## Follow-up — 2026-11-06T13:00Z

- QuanLyKho native Python staging service `srv-dbmpm5e7bikc73bmk0gg` used Python 3.14.10 when `pyarrow==19.0.1` lacked a compatible wheel; source build failed because Arrow C++ `ArrowConfig.cmake` was absent. Render `PYTHON_VERSION=3.11.11` and a main-only Poetry install let deploy `dep-dbmsjpijnfac73bc85dg` build successfully. It then failed at startup with `RuntimeError: JWT signing key must be set via BANKOPS_SIGNING_KEY environment variable`. That is a runtime secret gate, not a pyarrow failure. PR #19 merged; `backend/.python-version` on remote `main` contains `3.11.11`. The separate Docker service remains the only proven live QuanLyKho path.
- FlashSale PR #22 merged a corrected signed approval: GO for portfolio demo and HOLD for production, with unverified gates unchecked. PR #23 contains Flyway migrations for empty and existing PostgreSQL schemas. Local `mvn -B -f src/payment-service-java/pom.xml verify` passed 137/137 tests with Docker available; remote PR CI was pending when recorded. Neither PR establishes a working Render preview deployment or production GO.

## FlashSale PR #23 result — 2026-11-06T13:02Z

- PR #23 passed `verify`, `build-and-unit`, `integration-tests`, `java-build-and-test`, and `docker-build-scan`; it was squash-merged to remote `main` as `2cd79c425678ada0811b01435339bc73e5276052`. Preview and production deploy jobs were skipped on the PR. No Render deployment or payment flow was verified at this new SHA; production remains HOLD.
- QuanLyKho auto-deploy `dep-dbmss00u01pc739ghbqg` on merged Python-pin SHA `935aac8` finished `update_failed`. Its 12:56Z Render log says `BANKOPS_SIGNING_KEY` is required. This confirms the source pin is deployed but the native staging service remains unavailable until its signing key is set in Render.

## Azure and PR recheck — 2026-11-06T13:04Z

- FlashSale PRs #20, #21, #22 and #23 are all merged. Remote `main` is `2cd79c4`; the corrected `APPROVAL.md` on `main` says portfolio demo GO and production HOLD. No production deploy was triggered by PR #23.
- `az aks list` reports `aks-portfolio-dev` in `rg-aks-platform-dev` as Running/Succeeded. `rg-aks-validation-t13` currently exists and contains a Basic SKU registry `acrflashsalevalidation`, created 11:26Z. The earlier 11:13Z `ResourceGroupNotFound` observation was true at that time but no longer describes current state. The T13 evidence records successful deletion of the validation cluster and its node resource group by 12:12Z, with this ACR deliberately retained. Do not infer zero Azure cost from cluster teardown; subscription billing can lag and the dev cluster plus retained registry still exist.

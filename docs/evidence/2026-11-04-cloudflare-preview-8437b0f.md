# AKS SRE console Cloudflare preview — 2026-11-04 UTC

| Field | Value |
| --- | --- |
| Source SHA | `8437b0fd1790668b21d171d57374e1546800170a` |
| Environment | Cloudflare Pages **Preview**, branch `codex-portfolio-evidence-20261104` |
| Deployment ID | `f600044d-9ce7-4a2d-9689-9176f6f5b986` |
| URL | https://f600044d.aks-sre-platform.pages.dev |
| CI | [pr-gate](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/41849472078), [GitOps](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/41849472157), [SBOM](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/41849472108), external [SonarCloud PR check](https://sonarcloud.io/dashboard?id=imtarget05_AKS-SRE-Platform&pullRequest=18) green at deployment time |
| Rollback | Production Pages deployment remained `main` source `52c6a64` (read-only Wrangler deployment list). The preview can be replaced by a new preview deployment; production was not changed. |

`npm ci --ignore-scripts && npm run build && python3 smoke_test.py` passed locally. `wrangler pages deploy dist --project-name aks-sre-platform --branch codex-portfolio-evidence-20261104 --commit-hash 8437b0fd1790668b21d171d57374e1546800170a --commit-dirty=false` uploaded 14 assets and created the Preview deployment. The [sanitized raw probe](2026-11-04-cloudflare-preview-8437b0f.log) records UTC time, SHA, deployment ID, 13 HTTP 200 asset responses and the page's matching `release-sha` meta tag. A default Python urllib user agent received HTTP 403; a browser user agent obtained HTTP 200. This is an access-control observation, not an asset failure.

In a real browser, the page loaded without JavaScript errors; Cluster tab, outage simulation and runbook question/answer worked. The page labels metrics as synthetic and does not claim live AKS telemetry. The first preview (`483a8626`) failed browser runtime checks because minified classic scripts collided and CSP blocked inline handlers; [the preview defect record](../incidents/2026-11-04-pages-preview-runtime.md) explains the correction.

**Acceptance scope:** frontend preview reachability and interaction only. This does not close A16 or prove Azure workload, NetworkPolicy, GitOps, backup/restore or production go-live. No new Pages project or paid runtime was created; the actual incremental billed amount was not available in the CLI and remains OPEN for owner billing review.

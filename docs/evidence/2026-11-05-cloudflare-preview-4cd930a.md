# Cloudflare Pages preview — AKS SRE console

- Observed UTC: 2026-11-05 05:10–05:13.
- Environment: Cloudflare Pages **Preview**; project `aks-sre-platform`; branch `codex-portfolio-evidence-20261104`.
- Source SHA embedded in the built page: `4cd930a9abcc1ed8b0a86ad3d7bc023a3606951d`.
- Deployment ID: `e7728690-6d35-4c52-8e2c-248147e9dc43`.
- URL: https://e7728690.aks-sre-platform.pages.dev
- Build and checks: `npm ci --ignore-scripts && npm run build && python3 smoke_test.py` passed; Wrangler uploaded 14 assets using the current OAuth session with `pages (write)`.
- Deploy command: `wrangler pages deploy dist --project-name aks-sre-platform --branch codex-portfolio-evidence-20261104 --commit-hash <source SHA> --commit-dirty=false`.
- Expected/actual: root HTTP 200; HTML `release-sha` meta tag equals source SHA. The preview URL above returned HTTP 200 and the exact SHA.
- Rollback boundary: production Pages remains branch `main`, deployment `67d2f06c-719c-48d3-9df0-12a18542a89a`, source `52c6a64`; this operation did not replace it.

This proves frontend preview delivery only. The external SonarCloud new-code coverage gate remains red, and A16 Azure runtime is open. No actual billing amount was available in the Wrangler deployment output.

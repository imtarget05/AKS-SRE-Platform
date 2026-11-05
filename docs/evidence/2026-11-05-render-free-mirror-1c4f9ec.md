# Render Free mirror — sre-demo-api

- Observed UTC: 2026-11-05 approximately 05:22 UTC.
- Environment: Render `Tan's workspace`, web service `sre-demo-api`, Docker **Free** plan. This is a mirror/demo runtime, not Azure AKS.
- Source repo/branch: `imtarget05/AKS-SRE-Platform`, `codex/portfolio-cloud-evidence-20261104`; deployed source commit `1c4f9ecaa247e2b82dd42dd48391d93b18031e33`.
- Blueprint ID: `exs-dbm14glbedkc73at7jd0`; service ID: `srv-dbm14kpsrm7s73eo9p40`; initial deploy revision: `dep-dbm14l1srm7s73eo9pr0`.
- Dashboard: https://dashboard.render.com/web/srv-dbm14kpsrm7s73eo9p40
- Public URL: https://sre-demo-api.onrender.com
- Build source: root `render.yaml` pins `plan: free`, Dockerfile path/context and `autoDeploy: false`. The initial Blueprint sync created the service and the Dashboard reported the revision **Live** at the source commit above. No payment card was added.
- Expected/actual: `GET /health/live` HTTP 200 with `{"status":"live"}`; `GET /health/ready` HTTP 200 with `{"status":"ready","dependency":true}`; `GET /metrics` HTTP 200, 6,177 bytes, including `sre_api_requests_total` for real requests to the service.
- Rollback boundary: this is the first deploy of the mirror, so there is no earlier Render revision to restore. `autoDeploy: false` prevents later branch commits from changing the running revision automatically. Existing Azure and Cloudflare production resources were not modified by this Blueprint.

Render Free may spin down after inactivity and its filesystem is ephemeral. This evidence proves only that the mirror was deployed and answered the listed probes; it does not close A16, prove an image digest or authorize production traffic. The Dashboard showed Free plan, and no actual billed amount was available at this checkpoint.

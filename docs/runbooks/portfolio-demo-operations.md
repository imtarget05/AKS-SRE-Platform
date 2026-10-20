# Portfolio demo operations

This runbook describes the public, synthetic-data portfolio environment. It is
not evidence that an Azure environment is currently running.

## Public boundary

- Cloudflare owns DNS, TLS, WAF/rate limits, maintenance responses, and the
  public portfolio landing page.
- Azure AKS hosts only container/stateful workloads. Argo CD, Grafana,
  Prometheus, Kubernetes APIs, and metrics endpoints are never public routes.
- Demo accounts and seed data are synthetic. Do not copy local `.env` files,
  production exports, payment data, or tokens into a deployment artifact.

## Preflight before an Azure run

1. Confirm the Azure subscription, budget alert, required tags, and current
   vCPU quota. Use the documented Southeast Asia profile; use East Asia only
   when the quota check records that the primary region is unavailable.
2. Confirm GitHub Actions uses Azure OIDC and Key Vault/managed identities;
   reject client secrets, kubeconfigs, and Cloudflare tokens in Git.
3. Save a reviewed Terraform plan and a GitOps revision for every workload.
   A branch name or `latest` image tag is not an immutable deployment input.
4. Ensure Cloudflare maintenance mode is enabled before a scheduled AKS stop.

## Start, validate, stop

1. Apply only the reviewed Terraform plan, then bootstrap the canonical Argo CD
   applications.
2. Validate workload readiness, external HTTPS, a synthetic transaction, logs,
   metrics, alert firing/resolution, and rollback before publishing an
   `AZURE_CLOUD_VERIFIED` evidence record.
3. Before stopping the cluster, enable Cloudflare maintenance mode and verify
   it answers without proxying to the stopped origin.
4. Stop or destroy according to the approved cost profile; record the command,
   timestamp, observed cost, and final Azure resource inventory in evidence.

## Incident rule

If a public endpoint exposes an administrative surface, a secret, non-synthetic
data, or an unredacted internal error, disable the route at Cloudflare first,
preserve sanitized evidence, rotate the affected credential, and reopen only
after a reviewed fix and synthetic health check.

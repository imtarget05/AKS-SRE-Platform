# AKS / SRE Platform Blueprint

This repository is the platform-engineering blueprint for a shared Azure Kubernetes Service stack used to host multiple portfolio workloads. It contains the infrastructure code, GitOps manifests, bootstrapping automation, and the recorded validation evidence used to judge whether the platform is ready to move beyond prototype status.

## What is in this repo

- Terraform for the AKS foundation and cluster configuration
- bootstrap automation for Argo CD and KEDA
- GitOps manifests under `kubernetes/` and `platform/`
- deployment and validation notes in `docs/`
- portfolio integration points for Azure, Cloudflare, and Render

## What is proven

The strongest evidence in this repository is the real AKS validation completed on 2026-09-21. The validation covered:

- system pool setup with Azure-managed control and workload isolation
- user pool placement for application workloads
- private ACR pull by digest without a stored image pull secret
- Workload Identity token exchange and scoped access validation
- full teardown with the temporary validation cluster removed

Evidence is stored in:

- `docs/evidence/phase7a/`
- `docs/adr/014-azure-first-verification.md`
- `docs/adr/021-three-project-azure-rollout.md`

This repo also includes local kind-based validation for GitOps, Gateway API, and observability. Those results are valid as pre-Azure dry runs, not as proof of production Azure runtime behavior.

## Important boundaries

This is not a claim that the platform is already running as a persistent production cluster. The current repository is intentionally evidence-gated:

- no persistent Azure cluster is claimed as live
- no HPA proof is claimed as completed
- no NetworkPolicy enforcement proof is claimed as completed
- no live Azure CI login or production SLO history is claimed

The project status and remaining gaps are tracked in `tasks/current.md`.

## Quick start

```bash
# review the Terraform and platform model
cd terraform && ls

# inspect the bootstrap flow
bash scripts/bootstrap.sh --help 2>/dev/null || bash scripts/bootstrap.sh

# review the validation evidence
ls docs/evidence/phase7a/
```

## Evidence and portfolio links

- `docs/INTERVIEW_RELEASE.md` — interview-ready summary and boundaries
- `docs/architecture/cloud-deploy-targets.md` — target architecture across Azure/Cloudflare/Render
- `docs/adr/014-azure-first-verification.md` — proof standard for Azure vs local validation

This repository should be presented as a platform blueprint with real evidence, not as a fully deployed production system.

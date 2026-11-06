# T13 — AKS Validation Live Requirements

**Task:** T13 — AKS validation live requirements (documentation only, BLOCKED without Azure)
**Branch:** `codex/wave3-t12-t14`
**SHA (AKS-SRE-Platform):** `f064ad3`
**Date:** 2026-11-06
**Status:** BLOCKED — no Azure subscription, no live cluster, no deploy rights available

---

## Summary

T13 is **BLOCKED**. It cannot be executed without Azure credentials, a live AKS cluster, and deploy rights. This document states exactly what is required to unblock it.

### Current state (stated, not claimed as evidence)

- AKS cluster `aks-portfolio-dev` in `rg-aks-platform-dev` (eastasia) was destroyed after Phase 7A (2026-09-21) and again after teardown (2026-10-21).
- The 2026-11-01 read-only inventory found `aks-portfolio-dev` running with 3/3 Ready nodes but only system namespaces/pods — no Argo CD, no application workloads. Current owner, billing, and quota are unverified.
- The most recent known state (2026-11-05, per `tasks/current.md`): the AKS cluster and both AKS resource groups are absent (destroyed via terraform destroy). The shared ACR (`acrflashsalep6`), Terraform state resource group, and `rg-portfolio-prod` remain.
- **Conclusion:** No live cluster is available today. Nothing can be deployed to AKS validation without a new apply.

---

## Prerequisites to deploy digest-pinned Java demo to AKS validation

### 1. Azure identity and subscription

| Item | Required | Notes |
|---|---|---|
| Azure subscription ID | Yes | Needed for `az account set`, terraform backend, ACR, AKS |
| Resource group | Yes | e.g. `rg-aks-platform-dev` or `rg-portfolio-prod` |
| AKS cluster name | Yes | e.g. `aks-portfolio-dev` |
| Azure region | Yes | eastasia (per ADR-012, SE-Asia SKUs subscription-blocked) |
| `az login` / service principal with OIDC federation | Yes | CI needs workload identity federation to Azure |

### 2. Container registry (ACR)

| Item | Required | Notes |
|---|---|---|
| ACR registry name | Yes | e.g. `acrflashsalep6` (existing shared ACR) |
| ACR resource group | Yes | e.g. `rg-flashsale-release` |
| FlashSale image pushed to ACR | Yes | Java payment-service image |
| Image digest (sha256:...) | Yes | Digest-pinned deployment, no `:latest` |
| `AcrPull` role assignment for AKS kubelet identity | Yes | Enables private ACR pull without `imagePullSecret` |

### 3. Kubernetes access

| Item | Required | Notes |
|---|---|---|
| kubeconfig access | Yes | `az aks get-credentials --admin` or non-admin context |
| Namespace | Yes | Dedicated namespace for the FlashSale demo workload |
| kubectl context | Yes | Must point to the AKS cluster (not kind, not destroyed Azure cluster) |

### 4. Data infrastructure endpoints

| Item | Required | Notes |
|---|---|---|
| PostgreSQL endpoint | Yes | Managed (Azure Database for PostgreSQL) or self-hosted on AKS |
| Redis endpoint | Yes | Managed (Azure Cache for Redis) or self-hosted on AKS |
| RabbitMQ endpoint | Yes | Self-hosted on AKS or managed; KEDA scales on QueueLength trigger |
| Connection strings | Yes | Outside Git — Key Vault or GitHub Secrets |

### 5. Secrets (outside Git — never committed)

| Secret | Required | Notes |
|---|---|---|
| `JWT_SIGNING_KEY` | Yes | For FlashSale Java payment service auth |
| DB credentials (username/password) | Yes | PostgreSQL connection |
| RabbitMQ credentials | Yes | For KEDA scaling and app connectivity |
| Any other service connection strings | Yes | Stored in Key Vault / GitHub Secrets, referenced via CSI driver or external-secrets |

**Constraint:** No secrets in the repo (AGENTS.md Rule: "No secrets in the repo — environment variables / Key Vault / GitHub secrets.").

---

## Why T13 is BLOCKED

| Blocker | Detail |
|---|---|
| No live AKS cluster | Cluster destroyed 2026-10-21 and again 2026-11-05; no cluster exists today |
| No Azure subscription/budget | No subscription ID, no cost cap approval, no quota confirmation |
| No deploy rights | No `az login`, no service principal, no OIDC federation configured |
| No ACR image for current SHA | No digest-pinned FlashSale image pushed for the candidate release SHA |
| No kubeconfig | No cluster to generate kubeconfig against |
| No infrastructure endpoints | No PostgreSQL, Redis, or RabbitMQ provisioned |
| No secrets provisioned | JWT signing key, DB credentials, RabbitMQ credentials not in Key Vault |

### Statement

> The AKS cluster from phase7a (2026-09-21) was destroyed. No persistent cluster, no live Azure CI login.
>
> T13 cannot deploy anything to AKS validation without: (1) an Azure subscription with budget and cost cap approval, (2) deploy rights (service principal or federated identity), (3) a live AKS cluster, (4) an ACR with the FlashSale image pushed by digest, (5) PostgreSQL/Redis/RabbitMQ endpoints, and (6) secrets provisioned outside Git. All of the above require Azure credentials which are not available in this session.

---

## Evidence artifacts

None — T13 is documentation only; no Azure resources were created or queried.

---

## What the user needs to provide to unblock T13

| Item | Who provides |
|---|---|
| Azure subscription ID | H0 (account owner) |
| Azure budget / cost cap approval | H0 (account owner) |
| Azure deploy rights (service principal / OIDC federation) | H0 + CI owner |
| Resource group + AKS cluster name | Platform owner (P03) |
| ACR with FlashSale image pushed by digest | FlashSale release owner |
| PostgreSQL / Redis / RabbitMQ endpoints | Platform owner (P03) |
| Secrets: JWT_SIGNING_KEY, DB credentials, RabbitMQ credentials | Security owner (Key Vault / GitHub Secrets) |
| kubeconfig access | Platform owner (P03) |

T13 remains **BLOCKED** until all of the above are provided.

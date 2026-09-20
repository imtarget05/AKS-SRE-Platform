# AKS SRE Platform

Nền tảng vận hành cho hệ thống flash sale: **AKS + GitOps (ArgoCD) + event-driven
autoscaling (KEDA) + Azure Monitor**. Project 01 deploy app lên Container Apps;
project này là bản nâng cấp "platform engineering" — cluster, GitOps và autoscaling
theo backlog hàng đợi.

## Kiến trúc

```text
GitHub (main) ──▶ ArgoCD (self-heal + auto sync) ──▶ AKS namespace flash-sale-prod
                                                        ├── order-api        (Deployment, 2 replicas, probes, PDB)
                                                        └── order-worker     (Deployment, KEDA scale 0..50)

Service Bus queue "orders" ──▶ KEDA ScaledObject (azure-workload-identity, không secret trong cluster)
Azure Monitor / Container Insights (Log Analytics, Terraform provisioned)
```

## SLO (service level objectives)

| SLO | Mục tiêu | Cách đo |
|---|---|---|
| API availability | 99.9% | probe `/healthz`, PDB giữ ≥1 pod khi drain |
| Reservation p95 latency | < 250 ms | k6 threshold (Project 01 `load-tests/k6/`) |
| Order backlog | < 500 messages trong 5 phút | KEDA metric + Service Bus queue length alert |
| Zero oversell | stock luôn ≥ 0 | audit harness của Project 01 (chạy định kỳ) |

## Cấu trúc

```
terraform/            AKS + Log Analytics + KEDA identity (workload identity, OIDC federated)
kubernetes/           namespace, KEDA TriggerAuth + ScaledObject, worker, PDB
gitops/argocd/        Application trỏ về overlays/prod của Project 01 (kustomize)
scripts/bootstrap.sh  Cài ArgoCD + KEDA, apply manifest, đăng ký Application
```

## Triển khai (theo thứ tự)

```bash
# 0. Provision cluster + identity
cd terraform && terraform init && terraform apply \
  -var servicebus_namespace_name=<sb-từ-project-01>
# lấy kubeconfig + client id của KEDA identity (terraform outputs)

# 1. Bootstrap platform
chmod +x ../scripts/bootstrap.sh
../scripts/bootstrap.sh <keda_identity_client_id>

# 2. Secrets cho app (Key Vault CSI là bước nâng cấp tiếp theo)
kubectl -n flash-sale-prod create secret generic flashsale-secrets \
  --from-literal=pg-connection="Host=...;..." \
  --from-literal=redis-connection="...:6380,password=...,ssl=true" \
  --from-literal=servicebus-connection="Endpoint=sb://..."

# 3. Sửa image trong 01-FlashSale-Backend/infrastructure/kubernetes/overlays/prod/kustomization.yaml
#    thành ACR thật, commit & push → ArgoCD tự sync.
```

## Runbook

| Tình huống | Hành động |
|---|---|
| Queue backlog tăng đột biến | KEDA tự scale worker (1 replica/100 msg, max 50). Nếu kẹt ở max → tăng `maxReplicaCount` qua Git |
| Message vào DLQ | Kiểm tra Service Bus DLQ; drift Redis/DB → chạy `POST /internal/resync-stock/{id}` của Project 01 |
| API pod crashed | ArgoCD selfHeal khôi phục; xem Container Insights logs |
| Cluster upgrade | `az aks upgrade`; PDB + probes bảo đảm rolling an toàn |

## Best practices đã áp dụng
- **Workload Identity**: KEDA dùng federated credential — không connection string trong cluster.
- **Scale-to-zero** cho worker (tiết phí, phù hợp flash sale theo đợt).
- **Least privilege**: KEDA chỉ có role `Azure Service Bus Data Receiver`.
- **GitOps**: mọi thay đổi hạ tầng app qua Git; ArgoCD prune + selfHeal.

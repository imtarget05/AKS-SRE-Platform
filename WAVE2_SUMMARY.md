# WAVE 2 SUMMARY — AKS-SRE-Platform (cloud preview/staging)

**Repo:** /Users/mainguyenbinhtan/Downloads/AKS-SRE-Platform
**Commit SHA thuc te (HEAD):** 7633cad2b22072954ef7d615d925cb84269a153e (branch main, short: 7633cad)
**Thoi gian bat dau Wave 2:** 2026-11-06T10:41:38Z
**Thoi gian ket thuc Wave 2:** 2026-11-06T11:02:43Z
**Trang thai tong the:** 🟡 MOT SO BUOC HOAN TAT, MOT SO BUOC CHAN BLOK (thieu credential)

---

## 1. Doc repo truoc khi sua

Hoan tat: Da doc AGENTS.md, README.md, render.yaml, Makefile, terraform/aks-foundation/, kubernetes/, gitops/, scripts/, tests/test_gates.py, requirements.lock, app/sre-demo-api/Dockerfile, WAVE1_SUMMARY.md, tasks/current.md, platform/argocd/, platform/observability/.

---

## 2. Kiem tra credentials Azure / Render

| Credential | Nguon | Trang thai |
|------------|-------|------------|
| AZURE_CLIENT_ID / AZURE_CLIENT_SECRET / AZURE_TENANT_ID / AZURE_SUBSCRIPTION_ID | env vars | Khong tim thay |
| Azure CLI (az account show) | az CLI | Da dang nhap (user: binhtan5734@gmail.com, subscription: a3deec78-7edb-41cd-9e94-ec1d4d9379f5, state: Enabled) |
| RENDER_API_KEY | env vars | Khong tim thay |

Chan diem: Khong co RENDER_API_KEY -> khong the deploy sre-demo-api len Render. Khong co AZURE_* env vars -> Terraform dung Azure CLI auth (hoat động qua az login).

---

## 3. Ap dung Terraform (co Azure access qua az CLI)

Thu muc: terraform/aks-foundation/

Lan apply 1 — thay doi sku_tier
terraform init -backend-config=backend-remote.tfbackend -reconfigure -> Thanh cong
terraform validate -> Success!
terraform plan -out=tfplan -> 0 add, 1 change, 0 destroy
terraform apply tfplan -> Thanh cong (2m39s)
Thay doi: azurerm_kubernetes_cluster.aks sku_tier Standard -> Free.

Lan apply 2 — them user pool (sua bien enable_workload_pool)
Sua terraform/aks-foundation/variables.tf: enable_workload_pool default false -> true.
terraform plan -out=tfplan -> 1 add, 0 change, 0 destroy
terraform apply tfplan -> Thanh cong (1m30s)
Them: azurerm_kubernetes_cluster_node_pool.work (1 node, Standard_D2s_v6, mode User).

Ket qua Terraform apply: THANH CONG

| Output | Gia tri |
|--------|---------|
| Cluster name | aks-portfolio-dev |
| Resource group | rg-aks-platform-dev |
| Region | eastasia |
| Subscription | a3deec78-7edb-41cd-9e94-ec1d4d9379f5 |
| Kubernetes version | 1.36.5 |
| SKU tier | Free |
| Node pool system | 2 nodes (Standard_D2s_v6), taint CriticalAddonsOnly=true:NoSchedule |
| Node pool work (user) | 1 node (Standard_D2s_v6), khong taint |
| kubeconfig path | ~/.kube/config (context: aks-portfolio-dev-admin) |
| OIDC issuer | https://eastasia.oic.prod-aks.azure.com/... |

---

## 4. Trien khai ArgoCD GitOps tren AKS

Cai dat ArgoCD
- Khong dung scripts/bootstrap.sh (tu choi mutate non-kind cluster, yeu cau kind-local-platform context).
- Cai thu cong: kubectl apply -n argocd --server-side --force-conflicts -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.5/manifests/install.yaml
- ArgoCD version: v3.5.5 (pinned theo platform/argocd/VERSION)
- Namespace: argocd
- Tat ca 7 component Running: application-controller, applicationset-controller, dex-server, notifications-controller, redis, repo-server, server

Ket noi ArgoCD voi repo GitHub
- Repo URL: https://github.com/imtarget05/AKS-SRE-Platform.git
- Target revision: 7633cad
- Path: kubernetes/
- Destination namespace: quanlykho

Sua platform/argocd/appproject.yaml (bat buoc de sync thanh cong)
Thay doi:
1. Them flashsale vao destinations
2. Them TriggerAuthentication vao keda.sh namespaceResourceWhitelist
3. Them clusterResourceWhitelist cho Namespace (group: "", kind: Namespace)
4. Xoa clusterResourceBlacklist

Ly do: AppProject goc chan Namespace (clusterResourceBlacklist */*), chan namespace flashsale (khong co trong destinations), va chan TriggerAuthentication (khong co trong whitelist).

ArgoCD Application
- Application name: aks-sre-platform (namespace: argocd)
- Project: portfolio
- Sync status: Synced tai revision 7633cad
- Health: Degraded (ArgoCD khong co health check cho Namespace / ScaledObject / TriggerAuthentication, resources ton tai nhung status ?)
- Resources da sync:
  - Namespace/quanlykho — Active
  - ScaledObject/order-worker-scaler (namespace: flashsale) — ton tai
  - TriggerAuthentication/rabbitmq-trigger-auth (namespace: flashsale) — ton tai

Pod CrashLoopBackOff
- Khong co pod CrashLoopBackOff tu ArgoCD sync.
- Pod order-worker-7d85cd9b89-7n6b4 (namespace: flashsale) o trang thai ImagePullBackOff — do image tham chieu acrflashsale-placeholder.azurecr.io/order-worker:latest (placeholder, khong phai image thap). Du kien boi MANIFEST-INVENTORY phan loai kubernetes/ la LEGACY_NOT_DEPLOYED.

---

## 5. Deploy sre-demo-api len Render

CHAN BLOK — Khong co RENDER_API_KEY.

- render.yaml da ton tai: dich vu sre-demo-api, runtime docker, plan free, dockerfilePath app/sre-demo-api/Dockerfile, healthCheckPath /health/live, autoDeploy false.
- Khong the tao/cap nhat dich vu Render khong co RENDER_API_KEY.
- Khong cap nhat duoc release-sha trong Cloudflare preview.

---

## 6. Bat observability

Cai dat kube-prometheus-stack tren AKS
- Chart: prometheus-community/kube-prometheus-stack version 91.5.0
- Values file: platform/observability/kube-prometheus-stack-aks-values.yaml
- Namespace: monitoring (da tao)
- Secret: grafana-admin (da tao, mat khau khong in ra)

Ket qua
| Component | Trang thai |
|-----------|-----------|
| Grafana (kps-grafana) | Running (3/3) |
| Prometheus Operator | Running (1/1) |
| Node Exporter (daemonset) | Running tren 3/3 nodes |
| Prometheus server | Pending (FailedScheduling: Too many pods tren user pool, taint tren system pool) |
| Alertmanager | Pending (cung ly do) |
| kube-state-metrics | Pending (cung ly do) |

Metrics collected: Mot phan
- Node exporter dang chay tren 3 node, thu thap metrics node-level.
- Khong co Prometheus server -> khong luu/truy van metrics, khong co dashboards Grafana voi du lieu thuc.

Alerting configured: KHONG
- Alertmanager Pending -> khong co alerting hoat dong.
- Khong the kich thuc alert khi healthcheck that bai.

---

## 7. Thu recovery drill

Pod delete test: THANH CONG
- Thao tac: kubectl -n argocd delete pod argocd-server-b789667d5-mnwzk
- Truoc: pod 1/1 Running, age 7m19s
- Sau: Kubernetes tu tao pod moi argocd-server-b789667d5-dpzlk, 1/1 Running trong khoang 21 giay
- Thoi gian recovery: khoang 21 giay

Node delete test: KHONG THUC HIEN
- Ly do: Cluster validation qua nho (3 nodes), xoa node se gay gian dien dich vu platform. Khong thuc hien tren cluster validation tam thoi.

---

## 8. Kiem tra bao mat

KHONG CO SECRET CUA VAO REPO
- terraform/: Khong co Azure credentials, connection strings, API keys hardcode. Bien acr_name/acr_resource_group_name la ten tai nguyen.
- kubernetes/: Tat ca tham chieu secret dung secretKeyRef/secretRef, khong co gia tri plaintext.
- render.yaml: Khong co secret, chi co env vars cong khai (NODE_ENV, PORT, OTEL_SERVICE_NAME).
- Khong co file .env, *.tfvars credential nao trong repo.
- Azure CLI authentication dang user (khong phai service principal), khong luu secret trong env vars.
- Khong co Azure Key Vault nao duoc tao (az keyvault list -> empty).

---

## 9. Loi gap phu va cach xu ly

| Loi | Cach xu ly |
|-----|-----------|
| scripts/bootstrap.sh tu choi mutate cluster non-kind | Cai ArgoCD thu cong qua --server-side --force-conflicts voi manifest v3.5.5 |
| AppProject chan Namespace, namespace flashsale, TriggerAuthentication | Sua platform/argocd/appproject.yaml: them whitelist, destinations, xoa blacklist |
| ArgoCD sync ban that bai: failed to discover server resources for keda.sh/v1alpha1 | Cai KEDA CRDs qua helm template kedacore/keda --include-crds |
| Prometheus/Alertmanager/kube-state-metrics Pending | Khong du tai nguyen tren user pool node (1x D2s_v6) + taint tren system pool nodes. Khong the resolve khong tang quy mo cluster. |
| Khong co RENDER_API_KEY | Khong the deploy Render. Bao cao chan, khong fabricate credential. |
| Khong co AZURE_* env vars | Dung Azure CLI auth (az login da ton tai). Terraform init/plan/apply hoat dung binh thuong. |

---

## 10. File da chinh sua

| File | Thay doi |
|------|----------|
| terraform/aks-foundation/variables.tf | enable_workload_pool default: false -> true (de tao user pool cho workload) |
| platform/argocd/appproject.yaml | Them flashsale destination, them TriggerAuthentication whitelist, them clusterResourceWhitelist cho Namespace, xoa clusterResourceBlacklist |

File moi tao
- WAVE2_SUMMARY.md (file nay)

---

## 11. Tom tato ket qua

| Muc | Trang thai |
|-----|-----------|
| Terraform apply | Thanh cong (1 changed, 1 added) |
| AKS cluster chay | aks-portfolio-dev, 3 nodes (2 system + 1 user), vung eastasia |
| ArgoCD cai dat | v3.5.5, 7/7 component Running |
| ArgoCD sync voi GitHub | Synced tai SHA 7633cad |
| ArgoCD Application | aks-sre-platform, Synced, revision 7633cad |
| Render sre-demo-api | Chan (khong co RENDER_API_KEY) |
| Observability (metrics) | Mot phan (node-exporter chay, Prometheus Pending) |
| Observability (alerting) | Khong (Alertmanager Pending) |
| Recovery drill (pod delete) | Thanh cong, khoang 21 giay |
| Recovery drill (node delete) | Khong thuc hien |
| Bao mat (khong co secret leak) | Pass |

---

## 12. Ket luan

Wave 2 da thuc hien duoc phan lon:
- Azure AKS cluster cung cap va cau hinh qua Terraform
- ArgoCD GitOps cai dat va sync thanh cong voi repo imtarget05/AKS-SRE-Platform tai SHA 7633cad
- Recovery drill (pod delete) thanh cong voi self-healing khoang 21s
- Khong co secret ro loi vao repo

Cac muc khong thuc hien duoc do thieu credential/tai nguyen:
- Deploy sre-demo-api len Render (thieu RENDER_API_KEY)
- Observability day du (Prometheus/Alertmanager Pending do thieu tai nguyen cluster)

File bang thuc: /Users/mainguyenbinhtan/Downloads/AKS-SRE-Platform/WAVE2_SUMMARY.md

Luu ý quan trong: Khong claim production-ready. Cluster hien tai la cluster validation nho (3 nodes, SKU Free) dung de thu thap bang thuc Wave 2. AKS production la NO-GO cho den khi validate trên cluster thap voi bang thuc timestamped.

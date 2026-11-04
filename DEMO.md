# AKS-SRE-Platform — Interview Demo Script (5–10 phút, chạy hoàn toàn local)

Mục đích: minh họa Terraform + AKS + ArgoCD + policy gates, không cần Azure private link.

## Yêu cầu trước khi demo

- Python 3.x, `pip install -r requirements.txt` (hoặc `.venv` đã có)
- `kubectl` (để render kustomize, không cần cluster)
- `terraform` (để validate + test, không cần apply)

## Bước 1: Terraform validate (5 root)

```bash
cd /Users/mainguyenbinhtan/Downloads/AKS-SRE-Platform

for root in terraform/aks-foundation \
  terraform/modules/acr_attachment terraform/modules/aks_cluster \
  terraform/modules/networking terraform/modules/observability; do
  echo "=== $root ==="
  (cd "$root" && terraform init -backend=false -input=false 2>&1 | tail -1)
  (cd "$root" && terraform validate 2>&1 | tail -3)
done
```

Kết quả mong đợi: Tất cả 5 root pass, 0 errors.

## Bước 2: Terraform test (16/16)

```bash
for root in terraform/aks-foundation \
  terraform/modules/acr_attachment terraform/modules/aks_cluster \
  terraform/modules/networking terraform/modules/observability; do
  echo "=== $root ==="
  (cd "$root" && terraform test 2>&1 | tail -3)
done
```

Kết quả mong đợi: 16 tests passed, 0 failed.

## Bước 3: GitOps validator (42/42)

```bash
python3 gitops/validate-gitops.py --repo-map gitops/repo-map.local.yaml
```

Kết quả mong đợi: 42 passed, 0 failed (hoặc có external repo NOT_PRESENT).

## Bước 4: Policy gate (PASS)

```bash
python3 scripts/policy-gate.py
```

Kết quả mong đợi: PASS, 0 failed.

## Bước 5: Test gates (62/62)

```bash
python3 tests/test_gates.py
```

Kết quả mong đợi: 62 passed, 0 failed.

## Bước 6: Kustomize render (6 root)

```bash
for root in deploy/base deploy/base/observability \
  deploy/overlays/aks-observability deploy/overlays/dev \
  deploy/overlays/prod deploy/overlays/validation; do
  echo "=== $root ==="
  kubectl kustomize "$root" >/dev/null 2>&1 && echo "OK" || echo "FAIL"
done
```

Kết quả mong đợi: Tất cả OK.

## Các điểm nhấn để trình bày phỏng vấn

| Điểm | Nơi chứng minh |
|---|---|
| Terraform reviewed before apply | `terraform/`, `backend-remote.tfbackend`, `versions.tf` |
| ArgoCD GitOps | `platform/argocd/`, `gitops/` |
| Policy gates (image pin, probes, resources, securityContext) | `scripts/policy-gate.py` |
| GitOps validation | `gitops/validate-gitops.py` |
| Negative controls (invalid manifests, duplicate AppProjects) | `tests/test_gates.py` |
| Manifest rendering (kustomize) | `deploy/base/`, `deploy/overlays/` |
| Terraform test | `terraform test` trên 5 root |

## Giới hạn trung thực (không claim)

- Cluster Azure nằm private-link, không thể kubectl từ máy local.
- ArgoCD sync/apply chưa được verify từ môi trường hiện tại.
- Không claim live Azure deployment.
- Hai external repository báo NOT_PRESENT (chưa checkout).
- Không claim NetworkPolicy enforcement (kindnet không hỗ trợ).
- Không claim HPA/cluster-autoscaler proof, SLO history, DR exercise trên Azure.

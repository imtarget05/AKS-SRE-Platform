# AKS-SRE-Platform — kế hoạch chứng minh Senior DevOps / Platform Engineer

**Trạng thái:** đề xuất, chưa triển khai. **Baseline:** `main@33ad234` ngày 23/10/2026. Checkout hiện có WIP ở `terraform/aks-foundation/versions.tf`, `scripts/rebuild-aks.sh` và generated docs-site; không sửa/ghi đè chúng khi thực thi kế hoạch. Đọc `AGENTS.md`, `tasks/current.md`, `docs/engineering/CURRENT_STATE.md`, ADR-014/015 và `docs/evidence/portfolio-audit-2026-10-21.md` trước mọi mutation.

## Sở hữu platform

Repo này sở hữu Terraform/state, OIDC/identity, Argo CD/AppProject/Application, namespace isolation, Gateway, policy, shared observability, runbook/DR và cost guardrail. Logic FlashSale/OpsBridge và QuanLyKho nằm trong repo workload của chúng. LegacyApp `/sync` là no-op reference; không dùng nó làm bằng chứng tích hợp nghiệp vụ. Một ứng dụng trên kind chứng minh local GitOps; nó không chứng minh Azure runtime.

## P0 — State, identity và CI trước cloud apply

**Bằng chứng hiện tại:** `pr-gate`, `gitops-validate`, `oidc-azure` pass ở `main@33ad234`, nhưng [AKS Deploy fail](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/39898623765) tại `Azure Login (OIDC)` vì thiếu `client-id`/`tenant-id`. `CURRENT_STATE.md` mô tả Azure cluster cũ đã teardown và remote Terraform state từng bị orphan; file này là lịch sử, phải đối chiếu với state hiện tại trước apply.

1. Lập inventory read-only: subscription, resource group/backend, state key, identities/federated credentials, quota và chi phí hiện tại. So sánh Terraform local/remote state và saved plan; xác định một owner/state key trước khi chạy init/apply. Không dùng một backend cũ chưa đối chiếu.
2. Phân loại Azure workflow: PR/test gate chạy không cần Azure secret; deploy phải chỉ chạy khi GitHub environment/OIDC values hợp lệ và có điều kiện rõ. Không lấp missing values bằng long-lived client secret. Ghi lại bằng chứng negative gate khi giá trị thiếu và smoke OIDC có quyền tối thiểu khi đủ.
3. Chạy `terraform fmt/validate/test`, tflint/security, `tests/test_gates.py`, `scripts/verify-gitops-all.sh` với exact external source refs. Nếu repo map thiếu workload, không báo toàn hệ thống xanh. Giữ mỗi run gắn SHA, output và môi trường.

**Gate P0:** test/render/security gate xanh; Terraform state owner, OIDC identity và budget/cost envelope có chứng cứ. Cloud apply là bước riêng sau gate này.

## P1 — Golden path cho hai workload thực

1. **OpsBridge/FlashSale:** tiêu thụ overlay của workload từ `infrastructure/kubernetes/overlays/`; kiểm tra `platform/argocd/applications/flashsale.yaml` hiện theo `main` và `local`. Tách profile local/Azure, pin release ref/digest sau khi workload CI xanh. Kiểm tra migration hook, health/readiness, image pull và Argo sync. Không cho platform sửa logic order/payment.
2. **QuanLyKho:** chỉ sau Gate R0 của repo QuanLyKho, thêm Argo Application + namespace/project/route/policy ở repo này trỏ tới `infra/k8s/overlays/staging` hoặc overlay release đã chuẩn hóa. Overlay hiện dùng `staging-latest` và hostname placeholder: workload owner phải thay bằng digest/host theo môi trường; platform gate phải reject floating image/placeholder ở release. Giữ Flutter Pages và FastAPI API boundary như ADR workload; không deploy Cloudflare Worker legacy làm business API.
3. Dùng repo-map validator với checkout/ref chính xác của **cả hai** workload, kustomize render, manifest schema, AppProject allowlist và negative fixtures. Chứng minh một golden path tái dùng: PR → gates → immutable image → GitOps sync → health → rollback. Workload owner cung cấp contract/probes/metrics; platform cung cấp policy và vận hành.

**Gate P1:** hai workload render từ source thật; local kind self-heal và policy được đo lại trên exact SHA. Azure riêng: chỉ ghi `AZURE_CLOUD_VERIFIED` nếu có AKS/ACR identity pull, Argo sync, app health và rollback thực, không suy từ kind.

## P2 — SRE, bảo mật và FinOps với bằng chứng vận hành

1. Chọn SLI/SLO tối thiểu cho API success/latency và một business journey mỗi workload; Prometheus/Grafana/alert rule phải có test fire/resolve và runbook. Dùng metric cardinality, retention và storage budget phù hợp demo. Alert phải dẫn tới hành động chẩn đoán cụ thể.
2. Chạy failure drill có kiểm soát: pod/worker mất, dependency tạm lỗi, Argo drift, NetworkPolicy deny/allow, PDB drain, backup/restore. Ghi detection, timeline, recovery, data loss, môi trường và giới hạn. RTO/RPO ghi số đo của drill, không thay cho SLA production.
3. Policy-as-code cho non-root, resource limits, image digest, namespace boundary, secret source và quyền Argo; test cả case hợp lệ và case bị chặn. CI cần SBOM/image vulnerability scan và artifact provenance trước release claim.
4. Budget alert, ownership tags, quota check, schedule stop/start, teardown và restart verification là phần bắt buộc của Azure demo. Không tái tạo cluster chỉ để có URL portfolio nếu chi phí/state chưa rõ.

**Gate P2:** có evidence package versioned cho một vòng deploy → monitor → fault → restore/rollback → teardown, với SHA/digest và chi phí. README/site chỉ phản ánh trạng thái môi trường hiện tại, không quảng cáo cluster đã xóa là live.

## Giao diện với hai repo ứng dụng

Workload repo phát hành image, Kustomize overlay, migration contract, `/health` và metrics; platform repo nhận release ref/digest, áp policy và triển khai. Không merge lịch sử ba repo. Không đặt SRE/incident automation agent có quyền tự `kubectl apply`, rollback hay sửa Terraform trong đợt này; nếu thử agent sau Gate P2, bắt đầu bằng read-only triage, đánh giá trên incident synthetic và yêu cầu người vận hành duyệt mọi action.

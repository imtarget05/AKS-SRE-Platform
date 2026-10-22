# QA Plan — AKS-SRE-Platform

**Kho:** `/Users/mainguyenbinhtan/Downloads/AKS-SRE-Platform`  
**Người viết:** QA lead / test architect  
**Ngôn ngữ:** tiếng Việt (thuật ngữ kỹ thuật giữ tiếng Anh khi thích hợp)  
**Mục tiêu:** Kế hoạch kiểm thử chuyên ngành, production-grade, căn cứ bằng chứng thực trong repo.

---

## 1. Test Strategy (thuật ngữ Việt Nam)

### 1.1 Mục tiêu QA
- Xác minh toàn bộ invariant GitOps qua `gitops/validate-gitops.py` và cổng ma trận `tests/test_gates.py` (nhóm G1–G14, 47 assertions), đảm bảo CI không bị thu hẹp lại.
- Đảm bảo workload `app/sre-demo-api/` tuân thủ mô hình tách probe: `/health/live` độc lập dependency, `/health/ready` phụ thuộc dependency; xuất RED metrics; không có failure injection trong sản xuất.
- Xác minh Terraform IaC (`terraform/aks-foundation`, `modules/aks_cluster`, `modules/acr_attachment`) qua `terraform test` với `mock_provider "azurerm"` — offline, không cần Azure credential.
- Xác minh sự nhất quán giữa bằng chứng AKS live (`docs-site/docs/evidence/aks-live.md`) và đầu ra `kubectl` thực tế; phân rõ telemetry có nhãn "mô phỏng" và telemetry thực.
- Khám phá và chặn rò rỉ mật thấu client-side JS (ví dụ hardcoded Cloudflare token trong `apps/sre-console/index.html`).
- Không làm hỏng 4 cổng CI hiện hành: `pr-gate.yaml`, `gitops-validate.yaml`, `legacyapp-ci.yml`, `oidc-azure.yaml`.

### 1.2 Phạm vi (in-scope / out-of-scope)

**In-scope:**
- `gitops/validate-gitops.py` + `tests/test_gates.py` (G1–G14, 47 assertions)
- `app/sre-demo-api/` (Node.js/Express, 7 unit tests, probes, RED metrics, `/api/fail`, `/api/work`, 404)
- `terraform/` (aks-foundation, modules/aks_cluster, modules/acr_attachment, `*.tftest.hcl`, mock_provider)
- `kubernetes/` (kustomize roots, manifests, NetworkPolicy, PDB)
- `apps/sre-console/index.html` (bảo mật client-side: không hardcoded secret)
- `scripts/` (validate-gitops, policy-gate, drill scripts)
- CI gates: `.github/workflows/{pr-gate,gitops-validate,legacyapp-ci,oidc-azure}.{yaml,yml}`
- By chứng: `docs/evidence/`, `docs-site/docs/evidence/aks-live.md`, `MANIFEST-INVENTORY.md`

**Out-of-scope:**
- Ứng dụng legacy .NET (`01-FlashSale-Backend`) — có kế hoạch QA riêng.
- Ứng dụng legacy Node.js (`apps/legacy-inventory`) — có `legacyapp-ci.yml` riêng.
- Terraform apply thật trên Azure (Phase C, chưa có OIDC/identity, cluster AKS đã destroy).
- OIDC live login (`OIDC_LIVE_LOGIN = NOT_VERIFIED` cho đến khi Phase C tạo identity).
- E2E trên cụm AKS live (chưa có cụm; cần rebuild để verify runtime).
- Thư mục `mlruns/` (ML/tracking, không thuộc phạm vi SRE platform này).

### 1.3 Pyramide kiểm thử
Từ đáy (rẻ, nhanh) đến đỉnh (đắt, chậm):

| Tầng | Công cụ / ví dụ | Mục đích | Cluster cần? |
|---|---|---|---|
| **Unit** | `app/sre-demo-api/test/server.test.js` (7 tests, `node --test`), logic từng hàm của `validate-gitops.py`, `state.js` | Xác minh đơn vị code, không cần cluster | Không |
| **Integration** | `tests/test_gates.py` (47 assertions, G1–G14) chạy validator dưới dạng subprocess trong repo tách biệt (isolated fixture); `gitops-validate.yaml` negative control (M-B1) | Xác minh sự hợp tác giữa validator, workflow, manifest | Không (fixture/CI) |
| **E2E** | kind dry-run (`PRE_AZURE_DRY_RUN`): triển khai manifests lên kind, curl `/health/live`, `/health/ready`, `/metrics`. Real AKS (`AZURE_VALIDATION`): chỉ khi cluster được rebuild | Xác minh runtime thực tế | kind có; AKS chưa (đã destroy) |
| **Contract** | `kubeconform` (K8s v1.36.0), Argo CD AppProject/Application contract, version pin (`platform/argocd/VERSION`), OpenTelemetry trace context propagation | Xác minh hợp đồng API và phiên bản | Không / kind |
| **Security** | Trivy config (HIGH/CRITICAL), Trivy fs (secret), tflint AzureRM ruleset, quét hardcoded secret trong client-side JS, OIDC contract (không `AZURE_CLIENT_SECRET` trong workflow) | Phát hiện lỗ hổng bảo mật và cấu hình sai | CI |
| **Performance** | SLO burn rate, `/api/work` xác định (deterministic), traffic burst mô phỏng, HPA burst | Xác minh hiệu năng và ngân sách lỗi | Local process / kind |

### 1.4 Loại kiểm thử

- **Functional:** GitOps validation, probe split, readiness dependency-gating, `/api/fail` injection, `/api/work`, render manifest (`kustomize`), assertions `terraform plan`.
- **Non-functional:**
  - *Reliability:* graceful shutdown (SIGTERM), PDB drain drill, node eviction, pod zero-restart khi drain.
  - *Cost:* AKS Free tier, node auto-provisioning Manual, teardown cụm theo FinOps.
  - *Security:* không hardcoded secret, OIDC contract secretless, NetworkPolicy `azure`, Workload Identity, Trivy chặn HIGH/CRITICAL.
  - *Observability:* RED metrics, OTel traces, structured logs với trace correlation, SLO/SLI burn rate.
- **Chaos / drill:** SLO burn rate, node eviction/drain (`scripts/pdb-drain-drill.sh`, `disaster_recovery_drill.sh`), NetworkPolicy violation (`--simulate` mode), dependency outage (`sre-demo-api` `/api/dependency` + `scripts/aiops_incident_triage.py`).

---

## 2. Môi trường kiểm thử

| Môi trường | Mục đích | Biến số / cờ | Trạng thái hiện tại |
|---|---|---|---|
| **Local kind cluster** | Dry-run manifests, probes, Argo CD local profile, drill local | `PRE_AZURE_DRY_RUN` | Có sẵn, có bằng chứng local (`docs/evidence/local-platform/`) |
| **Real AKS** | Verify runtime (control plane, node pool, ACR digest pull, workload identity) | `AZURE_VALIDATION` | Cluster `aks-portfolio-dev` đã destroy 2026-10-21; cần rebuild để verify runtime |
| **Isolated test repo** (gitops validator) | Fixture repo tách biệt cho `tests/test_gates.py`, validator chạy dưới dạng subprocess | — | Có sẵn |
| **CI gates** (GitHub Actions) | `pr-gate.yaml`, `gitops-validate.yaml`, `legacyapp-ci.yml`, `oidc-azure.yaml` | — | Có sẵn, chạy `ubuntu-latest` |

Chi tiết từng cổng CI:
- `pr-gate.yaml`: terraform (fmt/init/validate/test/tflint), kubernetes (kubeconform, kustomize, inventory, policy-gate), security (Trivy config + fs secret), python (test_gates.py G1–G14).
- `gitops-validate.yaml`: GitOps semantics, assert external repos là `EXTERNAL_REPO_NOT_PRESENT`, negative control M-B1 (mutate → validator phải bịt → restore byte-identical → xanh lại).
- `legacyapp-ci.yml`: test-and-scan, docker-build-scan, manifest-validation, sonarqube (skip cho đến khi cấu hình), ci-gate tổng hợp.
- `oidc-azure.yaml`: contract (static, không Azure), live (điều kiện `AZURE_CLIENT_ID`, positive + negative control), status (không bao giờ là quiet pass; `NOT_VERIFIED` nếu chưa có identity).

---

## 3. Danh sách test case ưu tiên (P0/P1/P2)

Dưới đây là **24 test case** (vượt quá yêu cầu tối thiểu 15), mỗi case có: ID, tên, mô tả, input, expected result, priority, environment, automation.

### 3.1 Nhóm GitOps gate

| ID | Tên | Mô tả | Input | Expected result | Priority | Môi trường | Automation |
|---|---|---|---|---|---|---|---|
| TC-01 | Valid manifest | Repo-owned resources hợp lệ → validator xanh | Repo tách biệt với AppProject + Application đúng chuẩn | `rc == 0`, không có dòng `FAIL` | P0 | Isolated test repo + CI (`gitops-validate.yaml`) | Automated (`test_gates.py` G1) |
| TC-02 | Orphan manifest detection | Phát hiện manifest mồ côi dưới `kubernetes/` | Thêm `kubernetes/orphan.yaml` không có trong `MANIFEST-INVENTORY.md` | `rc != 0`, tệp mồ côi được ghi tên | P0 | Isolated test repo + CI | Automated (`test_gates.py` G8) |
| TC-03 | Duplicate AppProject | Hai file khai báo cùng tên AppProject → FAIL, ghi cả 2 đường dẫn | `platform/argocd/appproject.yaml` + `gitops/projects/portfolio.yaml` cùng `metadata.name: portfolio` | `rc != 0`, cả 2 đường dẫn bị chỉ ra | P1 | Isolated test repo + CI | Automated (`test_gates.py` G11) |
| TC-04 | Version pinning | Argo CD version g chốt ở 1 nơi | `platform/argocd/VERSION` phải là tag `vMAJOR.MINOR.PATCH`; `bootstrap.sh` đọc file này, không có tham chiếu floating (`stable`/`latest`/`main`); docs phải trùng pin | Pin đúng định dạng, không có floating ref, docs trùng `v3.5.5` | P0 | CI | Automated (`test_gates.py` G12) |
| TC-05 | External repo not supplied | Ứng dụng trỏ repo ngoài không được checkout | Không truyền `--repo-map` | `EXTERNAL_REPO_NOT_PRESENT` (advisory, không phải pass); `--require-external` → `rc != 0` | P1 | Isolated test repo + CI | Automated (`test_gates.py` G4) |
| TC-06 | Machine-specific path prevention | Chặn đường dẫn máy chủ trong `--repo-map` | `--repo-map` chứa `~/...` hoặc `/absolute/...` | `rc == 2` (usage error), giải thích từ chối | P1 | Isolated test repo + CI | Automated (`test_gates.py` G3) |
| TC-07 | Negative control (M-B1) | Biến đảo invariant GitOps, validator phải từ chối | Mutate `platform/argocd/applications/flashsale.yaml`, `destination.namespace` → `kube-system` | Validator `rc != 0`; restore byte-identical → xanh lại; `git diff --exit-code` sạch | P1 | CI (`gitops-validate.yaml` negative-control) | Automated |

### 3.2 Nhóm sre-demo-api (Node.js Express)

| ID | Tên | Mô tả | Input | Expected result | Priority | Môi trường | Automation |
|---|---|---|---|---|---|---|---|
| TC-08 | Liveness độc lập dependency | `/health/live` trả về 200 không cần dependency | `GET /health/live` với dependency nằm xuống | `200`, `{ status: "live" }`, pod không restart | P0 | Local (`npm test`) | Automated (`server.test.js`) |
| TC-09 | Readiness phụ thuộc dependency | `/health/ready` trả về 503 khi dependency chết; mode độc lập trả về 200 | `READINESS_REQUIRES_DEPENDENCY=true`, dependency URL không tới; flip readiness qua `/internal/ready?ready=false` | `503` khi phụ thuộc; `200` khi không cấu hình phụ thuộc | P0 | Local (`npm test`) | Automated (`server.test.js`) |
| TC-10 | RED metrics endpoint | `/metrics` xuất các chỉ số RED | Gọi một số endpoint rồi đọc `/metrics` | Có `sre_api_requests_total`, `sre_api_errors_total`, `sre_api_request_duration_seconds`, `sre_api_requests_in_flight`, `sre_api_readiness`; định dạng Prometheus | P0 | Local (`npm test`) | Automated (`server.test.js`) |
| TC-11 | Failure injection | `/api/fail` không được kích hoạt trừ khi được armed | `FAILURE_INJECTION_ARMED` không set → `404`; `=true` → `500` `{ error: "injected" }` | Không thể inject trong sản xuất (physically cannot be armed without env flag) | P1 | Local (`npm test`) | Automated (`server.test.js`) |
| TC-12 | Unknown route 404 | Route không xác định trả về 404 | `GET /nope` | `404`, `{ error: "not found" }` | P1 | Local (`npm test`) | Automated (`server.test.js`) |
| TC-13 | `/api/work` deterministic | Tương tự input n → output checkpoint giống nhau | `GET /api/work?n=500` hai lần | `checksum` và `iterations` bằng nhau, lặp lại được | P1 | Local (`npm test`) | Automated (`server.test.js`) |
| TC-14 | Entrypoint regression guard | `npm start` và Dockerfile CMD chạy cùng entrypoint thực, gọi `server.listen()` | `app/sre-demo-api/package.json` `scripts.start`, `Dockerfile` `CMD` | Cả hai trỏ đến cùng file tồn tại và file đó có `.listen(` | P0 | CI | Automated (`test_gates.py` G14) |

### 3.3 Nhóm Terraform (offline, mock_provider)

| ID | Tên | Mô tả | Input | Expected result | Priority | Môi trường | Automation |
|---|---|---|---|---|---|---|---|
| TC-15 | aks-foundation tftest | Xác minh foundation module offline | `terraform/aks-foundation/tests/aks_foundation.tftest.hcl` với `mock_provider "azurerm"` | 2 run block pass, `rc == 0` (cluster name, RG, K8s 1.36, OIDC, workload identity, VM size) | P0 | CI (`pr-gate.yaml` terraform job) / local | Automated (`terraform test`) |
| TC-16 | modules/aks_cluster tftest | Xác minh cluster module offline | `terraform/modules/aks_cluster/tests/aks_cluster.tftest.hcl` | 2 run block pass: only_critical_addons, vm_size `Standard_D2s_v6`, OIDC, workload identity, network plugin `azure`, network policy `azure`, Free tier, manual provisioning | P0 | CI / local | Automated (`terraform test`) |
| TC-17 | modules/acr_attachment tftest | Xác minh module ACR attachment offline | `terraform/modules/acr_attachment/tests/acr_attachment.tftest.hcl` | `rc == 0`, assertions về gán vai trò ACR | P1 | CI / local | Automated (`terraform test`) |
| TC-18 | tflint recursive lint | Lint tất cả root Terraform từ `terraform/` root, config tuyệt đối | `tflint --recursive --config "$(pwd)/.tflint.hcl"`, `--init` trước recursive | `rc == 0`, 0 vấn đề; AzureRM ruleset được nạp ở mọi thư mục con | P1 | CI (`pr-gate.yaml`) | Automated (`test_gates.py` G10) |
| TC-19 | CI executes every test root | CI phải chạy mọi root sở hữu `*.tftest.hcl` | So sánh hệ thống tệp với `TERRAFORM_TEST_ROOTS` trong workflow | Mọi root (3 root, 5 run block) được thực thi; guard tổng bằng 0 → fail job | P0 | CI | Automated (`test_gates.py` G10) |

### 3.4 Nhóm drill simulation (chaos / DR)

| ID | Tên | Mô tả | Input | Expected result | Priority | Môi trường | Automation |
|---|---|---|---|---|---|---|---|
| TC-20 | SLO burn rate | Tính tỷ lệ tiêu thụ ngân sách lỗi theo SLO | `--simulate` mode, SLO 99,9% trong 30 ngày, tiêu thụ 2% ngân sách trong 1 giờ | Burn rate được tính đúng công thức (tham khảo Google SRE Workbook), ngưỡng cảnh báo rõ ràng | P1 | Local / scripts | Automated hoặc manual |
| TC-21 | Node eviction / drain drill | Dịch node với PDB, zero-downtime, graceful termination | `scripts/pdb-drain-drill.sh`, `disaster_recovery_drill.sh` | Pod bị gracefully terminate, không có request thất bại trong lúc drain, replica đủ | P1 | Local kind / scripts | Automated hoặc manual |
| TC-22 | NetworkPolicy violation (`--simulate`) | Xác minh NetworkPolicy drop gói tin đúng | Chạy probe từ pod được phép và pod bị chặn, `--simulate` mode | Pod được phép kết nối, pod bị chặn bị từ chối; kết quả probe được lưu | P2 | Local kind | Manual |

### 3.5 Nhóm evidence consistency

| ID | Tên | Mô tả | Input | Expected result | Priority | Môi trường | Automation |
|---|---|---|---|---|---|---|---|
| TC-23 | Evidence consistency: aks-live.md ↔ kubectl | By chứng AKS live phải khớp với đầu ra `kubectl` thực tế | `docs-site/docs/evidence/aks-live.md` vs `kubectl get nodes`, `kubectl get pods -n argocd` | Node `Ready`, K8s v1.36.4, system pool đúng; telemetry được gắn nhãn rõ ràng "mô phỏng" vs thực | P0 | Docs review (manual) | Manual |

### 3.6 Nhóm Security

| ID | Tên | Mô tả | Input | Expected result | Priority | Môi trường | Automation |
|---|---|---|---|---|---|---|---|
| TC-24 | Không hardcoded Cloudflare token / secret trong client-side JS | Quét `apps/sre-console/index.html` và toàn bộ client-side JS | Trivy fs secret scanner, grep regex token/secret | Không có hardcoded token/API key; `cdnjs.cloudflare.com` chỉ là CDN link (không phải token); Trivy fs `rc == 0` trên secret HIGH/CRITICAL | P0 | CI (`pr-gate.yaml` security job) / local | Automated (Trivy fs secret) |

**Tóm ắt ưu tiên:** P0 = TC-01, TC-02, TC-04, TC-08, TC-09, TC-10, TC-14, TC-15, TC-16, TC-19, TC-23, TC-24 (12 case); P1 = TC-03, TC-05, TC-06, TC-07, TC-11, TC-12, TC-13, TC-17, TC-18, TC-20, TC-21 (11 case); P2 = TC-22 (1 case).

---

## 4. Test data management

- **Sample traffic burst payloads:** `/api/work?n=<1..200000>` để mô phỏng CPU burst; mô hình console mô phỏng burst 5.000 QPS (chỉ để minh họa, không lấy từ cụm live).
- **Dependency outage scenarios:** `DEPENDENCY_URL` không tới, dependency trả về HTTP 500, `READINESS_REQUIRES_DEPENDENCY=true` với timeout ngắn (`DEPENDENCY_TIMEOUT_MS=200`), mock dependency chậm (10.000 ms).
- **Health probe configs:** tách cấu hình liveness (không chạm dependency) và ready (phụ thuộc dependency); cờ `FAILURE_INJECTION_ARMED` chỉ bật trong môi trường kiểm thử.
- **Mock telemetry vs real telemetry separation:** dữ liệu trên `apps/sre-console/index.html` là mô phỏng client-side (có nhãn "mô phỏng", "Illustrative synthetic model"); telemetry thực chỉ lấy từ `kubectl` / Prometheus trên cụm kind hoặc AKS. Kết quả kiểm thử phải ghi rõ loại telemetry dùng.

---

## 5. Tự động hóa & CI/CD integration

### 5.1 Lệnh chạy tests
| Mục đích | Lệnh | Độ phủ |
|---|---|---|
| GitOps invariant gate matrix | `python3 tests/test_gates.py` | 47 assertions (G1–G14) |
| Demo workload unit tests | `cd app/sre-demo-api && npm test` | 7 tests (`node --test 'test/**/*.test.js'`) |
| GitOps semantic validation | `python3 gitops/validate-gitops.py` | Orphan, AppProject, Application, inventory |
| Static policy + image gate | `python3 scripts/policy-gate.py` | Kustomize roots, objects |
| Terraform native tests | `terraform test` trong mỗi root sở hữu `*.tftest.hcl` | 5 run block (aks-foundation 2, acr_attachment 1, aks_cluster 2) |
| Lint IaC | `tflint --recursive --config "$(pwd)/.tflint.hcl"` từ `terraform/` root | AzureRM ruleset, rc=0 |
| Security scan | `trivy config` (HIGH/CRITICAL) + `trivy fs --scanners secret` (HIGH/CRITICAL) | IaC/config và secret client-side |

### 5.2 Gate pass/fail criteria
- `tests/test_gates.py`: 47/47 assertions pass, `rc == 0`; bất kỳ nhóm G nào đỏ → job đỏ.
- `npm test`: 7/7 tests pass.
- `terraform test`: tổng assertions trên mọi root > 0 và mọi root `rc == 0`; tổng bằng 0 → fail job (NOT_IMPLEMENTED).
- `tflint`: `rc == 0`, 0 vấn đề sau `--init` với AzureRM ruleset.
- Trivy config/fs: `--exit-code 1` trên HIGH/CRITICAL → bất kỳ tìm thấy nào fail job.
- `gitops-validate.yaml` negative control (M-B1): mutation phải bị từ chối (`rc != 0`), restore byte-identical, còn lại xanh.

---

## 6. Tiêu chí xuất bản (exit criteria)

Một bản được coi là đạt yêu cầu xuất bản khi tất cả điều kiện sau đúng:

1. **Tất cả test case P0 pass** (TC-01, TC-02, TC-04, TC-08, TC-09, TC-10, TC-14, TC-15, TC-16, TC-19, TC-23, TC-24).
2. **Regression xanh:** `tests/test_gates.py` 47/47, `npm test` 7/7, `terraform test` tất cả root xanh, `tflint` rc=0.
3. **Evidence nhất quán:** `docs-site/docs/evidence/aks-live.md` khớp với đầu ra `kubectl` thực tế; telemetry được gắn nhãn rõ ràng "mô phỏng" vs thực, không tin dùng dữ liệu mô phỏng như bằng chứng live.
4. **Không hardcoded secret trong client-side JS:** Trivy fs secret scan sạch, không có Cloudflare token / API key cứng trong `apps/sre-console/index.html`.

---

## 7. Rủi ro & kế hoạch khắc phục

| Rủi ro | Mức độ | Kế hoạch khắc phục |
|---|---|---|
| **AKS cluster `aks-portfolio-dev` đã destroy (2026-10-21)** | Cao | Cần rebuild cluster để verify runtime (`AZURE_VALIDATION`). Nếu không thể rebuild ngay, accept đánh dấu các khẳng định runtime AKS là `AZURE_CLOUD_APPLY_NOT_VERIFIED` / `NOT_VERIFIED`, không được upscale thành "verified"; chỉ dựa vào bằng chứng local kind (`PRE_AZURE_DRY_RUN`) và Terraform test offline. |
| **Hardcoded API token / Cloudflare token trong client-side JS** | Cao (bảo mật) | Xác minh qua Trivy fs secret scan + grep. Nếu tìm thấy: xoá token, thay bằng biến môi trường / GitHub Secret, quét lại trước khi xuất bản. Điều này là điều kiện chặn xuất bản (P0 TC-24). |
| OIDC live login chưa có identity | Trung bình | `oidc-azure.yaml` chỉ chạy `contract` (static) và `status` báo `NOT_VERIFIED`; không bao giờ hiển thị green ảo. Phase C tạo Entra app + federated credential rồi mới bật `live`. |
| Local kind cluster không ổn định dưới tải (Docker Desktop crash) | Trung bình | Không chạy song song nhiều cluster kind trên cùng VM 7.75 GiB; đo lường lại sau khi daemon khởi động lại; không công bố "restarts = 0" nếu đã có sự cố host. |
| Terraform remote-state backend NXDOMAIN | Trung bình | Backend đã chuyển sang `local` (`terraform.tfstate`); keep offline `mock_provider` cho `terraform test`; không dépend Azure để gate CI. |

---

**Liên quan:**
- `tests/test_gates.py` — ma trận cổng G1–G14.
- `gitops/validate-gitops.py` — validator GitOps.
- `app/sre-demo-api/test/server.test.js` — 7 unit tests workload demo.
- `.github/workflows/pr-gate.yaml`, `gitops-validate.yaml`, `legacyapp-ci.yml`, `oidc-azure.yaml` — 4 cổng CI.
- `docs-site/docs/evidence/aks-live.md` — bằng chứng AKS lịch sử (cluster đã destroy).
# Portfolio Master Cheatsheet & Interview Defense Guide

> **Cặp đôi dự án thực chiến (Production-Grade Dual Portfolio):**
> 1. **`AKS-SRE-Platform`**: Cloud-Native Platform Engineering, GitOps, SRE, FinOps & Zero-Trust Infrastructure trên Azure.
> 2. **`MAIA`**: Enterprise Agentic RAG Platform, LangGraph HITL, Model Context Protocol (MCP) & PromptOps.

---

## 1. Kiến Trúc Tổng Thể (System Architecture)

### Sơ đồ 1A: AKS-SRE-Platform — `VERIFIED_TRANSIENT` (thực sự đã chạy trên Azure)

> **Chỉ gồm những thứ đã được chứng minh bằng log thật trên Azure** (run 2026-10-02,
> đã teardown về `0/10` vCPU). Nguồn:
> [`docs/evidence/transient-aks-run-PASS.md`](file:///Users/mainguyenbinhtan/Downloads/Projects/AKS-SRE-Platform/docs/evidence/transient-aks-run-PASS.md).
> **Không có Gateway, Argo CD, Prometheus hay Grafana trong sơ đồ này** — chúng
> không từng chạy trên AKS.

```mermaid
flowchart TD
    subgraph AZURE_CLOUD["Microsoft Azure (Region: eastasia) — VERIFIED_TRANSIENT"]
        subgraph IDENTITY_LAYER["Zero-Trust: Secretless — ĐÃ CHỨNG MINH"]
            ENTRA["Microsoft Entra ID (OIDC Federation)"]
            UAMI["User-Assigned MI: mi-aks-wi-proof-dev"]
            FIC["Federated Identity Credential"]
            KUBELET["Kubelet Managed Identity (AcrPull)"]
        end
        ACR["Private ACR: digest pull, imagePullSecrets: [] — ĐÃ CHỨNG MINH"]
    end

    subgraph AKS_CLUSTER["AKS aks-portfolio-dev (Free tier, K8s v1.36.4) — ĐÃ CHỨNG MINH"]
        subgraph SYSTEM_POOL["System Pool: 1x D2s_v6 — chỉ system components"]
            CORE_DNS["CoreDNS / Azure CNI / Metrics Server"]
        end
        subgraph USER_POOL["User Pool: 1x D2s_v6 — chỉ tenant workloads"]
            APP["sre-demo-api (Node.js non-root UID 10001, readOnlyRootFs)"]
            MOCK["mock-dependency"]
            WIPROOF["wi-proof pod (SA token -> Entra)"]
        end
    end

    APP -.->|Scoped Token Read — ĐÃ CHỨNG MINH| ENTRA
    WIPROOF -->|Federated exchange -> ARM read| ENTRA
    FIC -->|Token Exchange| ENTRA
    KUBELET -->|AcrPull by digest — ĐÃ CHỨNG MINH| ACR
    MOCK -->|DNS + HTTP :8080| APP
```

**Bằng chứng cụ thể cho từng node:** workload identity token exchange, ARM
read bằng service principal, image pull theo digest không cần pull secret,
0 tenant workload nằm trên system pool.

---

### Sơ đồ 1B: Target Platform Architecture — `IMPLEMENTED_TESTED_LOCAL` / `NOT_VERIFIED` trên AKS

> **Phần này KHÔNG phải bằng chứng Azure.** Đây là kiến trúc đã viết manifest
> trong repo, chứng minh trên **kind cục bộ**, **chưa từng chạy trên AKS**.
> Nếu interviewer hỏi "show me Argo CD reconcile trên Azure" — câu trả lời
> đúng là: *"chưa chạy trên Azure, mới chỉ PASS trên kind."*

```mermaid
flowchart TD
    subgraph TARGET["Target Platform — KHÔNG verified trên AKS"]
        subgraph LOCAL_PROOF["IMPLEMENTED_TESTED_LOCAL (kind) — xem docs/evidence/local-platform/"]
            ARGO["Argo CD: sync + git revert rollback + drift detect"]
            GW["Gateway API + Envoy Gateway (north-south)"]
            OBS["Prometheus + Grafana + 1 alert fire/resolve cycle"]
        end
        subgraph NOTVER["NOT_VERIFIED trên AKS"]
            CIL["Cilium + Azure CNI Overlay (NetworkPolicy enforcement)"]
            HPA["HPA / AKS Cluster Autoscaler (chưa quan sát scale-out)"]
            PDB["PDB / drain / topology spread"]
        end
        subgraph APPLIEDONLY["IMPLEMENTED — chỉ apply, chưa enforce"]
            NETPOL["NetworkPolicy objects (default-deny + allow rules)"]
        end
    end
    ARGO -.->|target sync| GW
    OBS -.->|target scrape| GW
    CIL -.->|required for enforcement| NETPOL
```

**Bảng trạng thái — dùng để trả lời "cái nào đã chạy thật?":**

| Thành phần | Trạng thái | Bằng chứng |
|---|---|---|
| AKS cluster, node pools, placement | `VERIFIED_TRANSIENT` | `transient-aks-run-PASS.md` §2 |
| ACR digest pull, không pull secret | `VERIFIED_TRANSIENT` | §4 |
| Workload Identity → ARM read | `VERIFIED_TRANSIENT` | §3 |
| Probes + failure injection | `VERIFIED_TRANSIENT` | §5 |
| Teardown về `0/10` vCPU | `VERIFIED_LIVE` | §6 |
| NetworkPolicy **objects** | `VERIFIED_TRANSIENT` (applied) | §5 |
| NetworkPolicy **enforcement** | `NOT_VERIFIED` | classic Azure CNI, không Cilium |
| NetworkPolicy negative control | `INCONCLUSIVE` | test bị kill, không có kết quả |
| Cilium / CNI Overlay | `TARGET` / `NOT_VERIFIED` | — |
| Argo CD | `IMPLEMENTED_TESTED_LOCAL` | `docs/evidence/local-platform/` |
| Gateway API + Envoy | `IMPLEMENTED_TESTED_LOCAL` | `l3-envoy-gateway-PASS.md` |
| Prometheus + Grafana | `IMPLEMENTED_TESTED_LOCAL` | `docs/evidence/local-platform/` |
| HPA / Cluster Autoscaler | `NOT_VERIFIED` | chưa từng quan sát scale-out |

> **Quy tắc sắt:** mọi câu trong cheatsheet này phải trả lời được
> *"Bây giờ tôi show evidence ở đâu?"*. Nếu không, nói rõ đó là
> target/design/local proof — **không** phải live Azure proof.

---

### Sơ đồ 2: MAIA (Enterprise Agentic AI Application)

```mermaid
flowchart TD
    subgraph USER_LAYER["Client & Presentation"]
        BROWSER["Streamlit UI / Web Client"]
        SSE_CLIENT["SSE Stream Listener (Tokens/Citations)"]
    end

    subgraph MAIA_CORE["MAIA Core Engine (FastAPI + LangGraph)"]
        ROUTER{"Intent Router / Classifier"}
        
        subgraph RETRIEVAL["Hybrid RAG Data Plane"]
            DENSE["FastEmbed / Qdrant Dense Vector Search"]
            SPARSE["BM25Okapi Lexical Search"]
            RRF["Reciprocal Rank Fusion (k=60)"]
            GATE{"Evidence Gate"}
        end

        subgraph AGENTIC["LangGraph HITL State Machine"]
            PROPOSE["Node: Propose Action"]
            INTERRUPT{{"Interrupt: Awaiting Human Approval"}}
            CONFIRM["Endpoint: /actions/confirm"]
            EXEC["Node: Execute Tool (Idempotent)"]
        end

        subgraph MCP_PLANE["Model Context Protocol (JSON-RPC 2.0)"]
            MCP_BRIDGE["MCP Bridge (Stdio / In-Process)"]
            DWH["SQL Analytics Server (Read-Only Guard)"]
            INTEG["Airtable / MS Teams / Email Integrations"]
        end
    end

    BROWSER --> ROUTER
    ROUTER -->|Policy Q&A| RETRIEVAL
    DENSE --> RRF
    SPARSE --> RRF
    RRF --> GATE
    GATE -->|Pass| BROWSER
    GATE -->|Fail| REFUSE["Honest Refusal (has_evidence=false)"]

    ROUTER -->|Action Request| PROPOSE
    PROPOSE --> INTERRUPT
    INTERRUPT -->|Approval Card| CONFIRM
    CONFIRM -->|Human Approved| EXEC
    EXEC --> MCP_PLANE
```

---

## 2. Kịch Bản Demo 3 Phút (3-Minute Live Interview Walkthrough)

| Thời gian | Trọng tâm demo | Thao tác / Lệnh thực hiện | Kết quả hiển thị (Showcase) |
|---|---|---|---|
| **0:00 - 1:00** | **MAIA: Grounded RAG & Honest Refusal** | Chạy `scripts/run_demo_e2e.sh` hoặc truy cập Azure endpoint:<br>`POST /chat` `"Chính sách nghỉ phép?"`<br>`POST /chat` `"Thưởng tiền Bitcoin?"` | • Câu hỏi 1: Trả về câu trả lời kèm trích dẫn chuẩn `[S1]`, `[S2]`.<br>• Câu hỏi 2: `has_evidence: false`, hệ thống từ chối lịch sự và trung thực. |
| **1:00 - 2:00** | **MAIA: LangGraph HITL & MCP Tools** | `POST /agent/chat` `"Xin nghỉ 2 ngày từ 15/09"`<br>$\to$ Nhận thẻ chờ duyệt `needs_approval`<br>$\to$ Duyệt qua `{"resume": {"approved": true}}` | • Agent dừng tại interrupt, không tự ý ghi dữ liệu.<br>• Sau khi duyệt: Trừ phép thành công (12 $\to$ 10 ngày).<br>• Chạy `python3 -m maia.mcp.bridge --list-tools` hiển thị các công cụ chuẩn JSON-RPC 2.0. |
| **2:00 - 3:00** | **AKS-SRE: Platform Credibility & FinOps** | Mở GitHub Actions của `AKS-SRE-Platform` hoặc review file [`.github/workflows/pr-gate.yaml`](file:///Users/mainguyenbinhtan/Downloads/Projects/AKS-SRE-Platform/.github/workflows/pr-gate.yaml) | • CI 100% xanh: `terraform test` chạy offline không mock dối trá, Trivy scan nhị phân có checksum SHA256.<br>• Giải thích FinOps Envelope: Quota 10 vCPU, sizing hệ thống $\le 8$ vCPU, transient validation kiểm chứng Workload Identity rồi teardown về 0 vCPU. |

---

## 3. Ma Trận Phòng Thủ Phỏng Vấn (Hardest Questions Defense)

### ❓ Nhóm Câu Hỏi 1: Cloud & Platform Engineering (AKS-SRE)

**Q1: Tại sao bạn không dùng Ingress-Nginx mà lại dùng Gateway API?**
> *"Ingress-Nginx đã vào bảo trì ở upstream và hạn chế khả năng chia sẻ multi-tenant. Tôi chọn **Gateway API + Envoy Gateway** vì đây là mô hình tách quyền rõ ràng (GatewayClass → Gateway → HTTPRoute) của CNCF.*
>
> *Nhưng tôi nói rõ mức độ chứng minh: **cấu hình này mới PASS trên kind cục bộ**, chưa deploy lên AKS. Trên Azure tôi mới chứng minh được Workload Identity, ACR digest pull, node placement và NetworkPolicy *objects*. Nếu anh muốn xem bằng chứng runtime cho Gateway, tôi show `docs/evidence/local-platform/l3-envoy-gateway-PASS.md` và nói thẳng đó là local proof, không phải Azure proof."*

**Q1b: NetworkPolicy của bạn có thực sự chặn traffic không?**
> *"**Chưa — và tôi không claim là có.** Policy objects đã được apply và API server accept, nhưng run Azure đó dùng classic Azure CNI (`network_plugin = "azure"`) không có Cilium, nên enforcement không xảy ra. Negative control tôi còn chạy dở đã bị kill nên kết quả là `INCONCLUSIVE`, không phải pass.*
>
> *Đây là điểm tôi cố ý ghi `NOT_VERIFIED` thay vì đoán. Repo tôi có sẵn ghi chú trong chính file NetworkPolicy và ADR-014 nói rõ enforcement cần Azure CNI Overlay + Cilium. Muốn prove thì phải deploy Overlay + Cilium rồi chạy lại negative control cho tới khi có kết quả blocked/allowed dứt khoát — tôi chưa làm bước đó, nên không claim."*

**Q2: Làm sao hệ thống của bạn đảm bảo Zero-Trust mà không bị rò rỉ Service Account Key?**
> *"Chúng tôi loại bỏ 100% private keys hay passwords tĩnh. Thay vào đó, chúng tôi triển khai **Azure Workload Identity** với Entra ID OIDC Federation. ServiceAccount trong cluster ánh xạ trực tiếp sang Federated Identity Credential. Pod xin JWT token cục bộ từ kubelet, sau đó trao đổi lấy Entra token ngắn hạn để truy cập tài nguyên Azure. Ngoài ra, Kubelet Managed Identity kéo private container image từ ACR bằng **digest**, không cần bất kỳ `imagePullSecret` nào."*

**Q3: Bạn giải quyết bài toán chi phí (FinOps) và hạn mức quota trên Cloud như thế nào?**
> *"Tôi thực hiện đo đạc thực tế trước khi cấu hình: Subscription bị giới hạn trần 10 regional vCPU. Thay vì yêu cầu tăng quota vô tội vạ hoặc chọn bừa VM to, tôi thiết kế cụm theo **Transient Envelope (tối đa 8 vCPU)**: System pool `1 × D2s_v6` (2 vCPU) + User pool `max 3 × D2s_v6` (6 vCPU), luôn dư 2 vCPU an toàn.
>
> *Run validation gần nhất (2026-10-02) dùng đúng **4 vCPU** (1 system + 1 user), và tôi **đã teardown ngay trong phiên làm việc**. Kiểm chứng lại sau teardown: `Total Regional vCPUs = 0/10`.*
>
> *Về con số tiền: tôi **ước tính** dưới $0.15 cho khoảng 25 phút compute trong control plane Free tier — tôi **không có** bản export từ Azure Cost Management, nên không đưa ra con số do đo lường. Cái tôi **đo được** là envelope compute: đỉnh 4 vCPU.*
>
> *Quy trình lặp lại được: Apply → kiểm chứng bằng log thật → Teardown → đo lại quota. Lần Phase 7A trước (2026-09-21) chạy 19 gate kiểm chứng và cũng kết thúc bằng teardown về 0 vCPU.*"*

---

### ❓ Nhóm Câu Hỏi 2: AI & LLM Systems (MAIA)

**Q4: Tại sao Gate 8B của MAIA lại fail, và tại sao bạn không chỉnh threshold để cho nó pass?**
> *"Đó là quyết định kiến trúc quan trọng nhất của tôi (ghi rõ trong **ADR-006**). Khi kiểm thử trên tập Golden Dataset (98 test cases), tôi đo được `max(no-answer)` đạt 0.6957 trong khi `min(answerable)` là 0.3140. Hai phân phối này chồng lấn lên nhau vì Cosine Similarity chỉ đo **Topical Relevance (độ gần gũi về chủ đề)** chứ không đo **Answerability (tính trả lời được)**. Một câu hỏi về lương hưu vẫn kéo về đoạn văn chính sách nhân sự với điểm 0.70 dù đoạn văn không hề có thông tin lương hưu. Nếu tôi chỉnh threshold lên $>0.70$ để pass bài test từ chối, tôi sẽ vô tình từ chối luôn các câu hỏi hợp lệ. Tôi chọn công bố lỗi đo đạc này một cách trung thực và tách kiến trúc thành 2 tầng: Tầng 1 lọc chủ đề qua RRF, và Tầng 2 dùng NLI Entailment verification."*

**Q5: Làm sao để đảm bảo Agent không tự ý thực thi các hành động nguy hiểm (destructive actions)?**
> *"Chúng tôi áp dụng mô hình **Human-in-the-Loop (HITL)** với LangGraph StateGraph và durable checkpointer (SQLite/Postgres). Bất kỳ công cụ nào gây side-effect (tạo IT ticket, trừ ngày phép, cập nhật CRM) đều đi qua node `propose_action` và kích hoạt hàm `interrupt()`. Trạng thái thực thi được đóng băng an toàn thành một `pending_action` card và trả về mã HTTP `needs_approval`. Chỉ khi con người gửi request phê duyệt tường minh vào endpoint `/actions/confirm`, đồ thị mới tiếp tục chạy từ điểm ngắt."*

**Q6: Hệ thống của bạn đã thực sự chạy trên Cloud chưa?**
> *"Đã chạy và được kiểm chứng trực tiếp trên **Azure Container Apps** tại endpoint `https://ca-maia-api.wittysand-b748274c.eastasia.azurecontainerapps.io`. Script kiểm chứng `scripts/deploy_check.py` chạy qua 5 bước nghiêm ngặt: Health/Ready probe, JWT Auth, RAG Query với trích dẫn `[S1]`, và Ingestion động vào Qdrant Cloud. Toàn bộ 16/16 checks đều đạt PASS với thời gian phản hồi 17.5s, chạy trên Consumption Tier với chi phí duy trì $\approx \$0.00$ khi nhàn rỗi."*

---

## 4. Bảng Tra Cứu Minh Chứng Kỹ Thuật (Evidence Index)

| Chủ đề kiểm chứng | Vị trí file mã nguồn / bằng chứng |
|---|---|
| **AKS Hardened CI & Test** | [`.github/workflows/pr-gate.yaml`](file:///Users/mainguyenbinhtan/Downloads/Projects/AKS-SRE-Platform/.github/workflows/pr-gate.yaml), [`terraform/aks-foundation/tests/aks_foundation.tftest.hcl`](file:///Users/mainguyenbinhtan/Downloads/Projects/AKS-SRE-Platform/terraform/aks-foundation/tests/aks_foundation.tftest.hcl) |
| **AKS Modularity & Decoupling** | [`terraform/modules/aks_cluster/`](file:///Users/mainguyenbinhtan/Downloads/Projects/AKS-SRE-Platform/terraform/modules/aks_cluster), [`terraform/modules/acr_attachment/`](file:///Users/mainguyenbinhtan/Downloads/Projects/AKS-SRE-Platform/terraform/modules/acr_attachment) |
| **AKS Remote State Foundation** | [`terraform/aks-foundation/versions.tf`](file:///Users/mainguyenbinhtan/Downloads/Projects/AKS-SRE-Platform/terraform/aks-foundation/versions.tf) (`rg-aks-tfstate` / `stakssre`) |
| **MAIA Live Azure Proof** | [`docs/evidence/MAIA_AZURE_LIVE_PROOF.md`](file:///Users/mainguyenbinhtan/Downloads/Projects/MAIA/docs/evidence/MAIA_AZURE_LIVE_PROOF.md) (16/16 checks PASS) |
| **MAIA One-Command E2E Demo** | [`scripts/run_demo_e2e.sh`](file:///Users/mainguyenbinhtan/Downloads/Projects/MAIA/scripts/run_demo_e2e.sh) |
| **MAIA Gate 8B Decision & ADR** | [`docs/adr/0006-answerability-vs-topical-similarity-gate.md`](file:///Users/mainguyenbinhtan/Downloads/Projects/MAIA/docs/adr/0006-answerability-vs-topical-similarity-gate.md) |
| **MAIA MCP Protocol Implementation** | [`src/maia/mcp/`](file:///Users/mainguyenbinhtan/Downloads/Projects/MAIA/src/maia/mcp) (`protocol.py`, `bridge.py`, `servers/`) |

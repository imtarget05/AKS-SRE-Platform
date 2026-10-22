# ADR-016: Terraform CI Gate Discipline & Confirmed Accepted Risks

- **Status:** **ACCEPTED** (2026-10-22)
- **Requirement Reference:** Closes **G12** from the Gap Register.
- **Related Documents:**
  - [.trivyignore](../../.trivyignore)
  - [.github/workflows/pr-gate.yaml](../../.github/workflows/pr-gate.yaml)
  - [ADR-012: AKS Foundation Cost-Safe](012-aks-foundation-cost-safe.md)
  - [ADR-014: Azure-First Verification](014-azure-first-verification.md)

---

## 1. Context & Business Problem

Infrastructure as Code (IaC) regressions can cause cloud configuration drift, silent syntax errors, or security misconfigurations that bypass downstream Kubernetes policies. 

In `AKS-SRE-Platform`, a multi-stage Terraform CI gate was established in `.github/workflows/pr-gate.yaml` to guarantee that all Terraform declarations are syntactically sound, conformant to AzureRM best practices, and covered by native unit tests before merging.

However, certain security scanner findings and architectural trade-offs require formal documentation as **confirmed accepted risks** to ensure that exemptions in `.trivyignore` and `.tflint.hcl` are conscious engineering decisions rather than unmonitored technical debt.

---

## 2. Decision: Four-Pillar Terraform CI Gate

The PR gate in `.github/workflows/pr-gate.yaml` executes five sequential controls on every push and pull request:

```text
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  terraform fmt  │ ──> │  terraform init  │ ──> │ terraform validate │ ──> │     tflint      │ ──> │  terraform test  │
│   (recursive)   │     │ (-backend=false) │     │   (syntax & schema)│     │(pinned AzureRM) │     │ (all 3 modules)  │
└─────────────────┘     └──────────────────┘     └────────────────────┘     └─────────────────┘     └──────────────────┘
```

1. **Format Enforcement (`terraform fmt -check -recursive`)**:
   Runs across the whole repository root so no nested module or root can evade formatting standards.
2. **Offline Hermetic Initialization (`terraform init -backend=false -input=false`)**:
   Enables fast, isolated PR validation without remote state locking or live Azure credentials.
3. **Schema Validation (`terraform validate`)**:
   Validates internal module references, type constraints, and resource arguments.
4. **Linting with Signature Verification (`tflint v0.64.0` + Pinned AzureRM Ruleset)**:
   Installs `tflint-ruleset-azurerm` with Sigstore TUF cryptographic verification (resilient against network blips with a 3-attempt retry loop).
5. **Native Unit Tests (`terraform test` across all 3 test roots)**:
   Mandatory assertions executed against:
   - `terraform/aks-foundation`
   - `terraform/modules/acr_attachment`
   - `terraform/modules/aks_cluster`  
   CI fails if total passing assertions equal 0.

---

## 3. Confirmed Accepted Risks & Exclusions

The following findings are explicitly accepted under strict scope boundaries:

### 3.1 Accepted Risk: Public API Server / Ingress IP Ranges (`AVD-AZU-0041`)
- **Scanner ID**: `AVD-AZU-0041` ("AKS has no API Server Authorized IP Ranges", Severity: CRITICAL).
- **Accepted Rationale**:
  - The production architectural target specified in ADR-014 requires a fully private cluster accessible via a dedicated Jumpbox or VPN gateway.
  - The validation cluster deployed in this repository is designed for **transient, automated CI verification** within a strictly constrained regional budget of **10 vCPUs** (`StandardDsv5/Dsv6` family).
  - Provisioning a dedicated private bastion VM would permanently consume 2 to 4 vCPUs (20–40% of the subscription quota), preventing the dual-node validation cluster from scheduling all application pods.
  - Therefore, the validation profile permits a public API server endpoint secured via Azure AD RBAC and mutual TLS, deliberately omitting static IP range restrictions during CI runs.
- **Retirement Trigger**: Must be removed and replaced with private endpoint configuration when deploying to a permanent dedicated production environment with standard vCPU limits (> 50 vCPUs).

### 3.2 Accepted Risk: External Secrets & Key Vault CSI Decoupling
- **Scope**: Azure Key Vault Secret Provider / External Secrets Operator manifests.
- **Accepted Rationale**:
  - Hermetic CI runs in GitHub Actions must execute offline without requiring developer credentials or live Azure Key Vault access.
  - Static analysis tools that evaluate secret references cannot resolve live Key Vault identities at validate time.
  - To prevent false-positive build failures, external secret synchronization is decoupled from PR linting and validated instead via runtime integration probes (`scripts/test-network-policy-probe.sh`).

### 3.3 Accepted Risk: Legacy Proof Backend Security Contexts (`AVD-KSV-0014`, `AVD-KSV-0118`)
- **Scanner IDs**:
  - `AVD-KSV-0014`: "Root file system is not read-only" (HIGH)
  - `AVD-KSV-0118`: "Default security context configured" (HIGH)
- **Accepted Rationale**:
  - These findings hit only external proof artifacts classified in `MANIFEST-INVENTORY.md` as `EXTERNAL_WORKLOAD_REFERENCE` (`kubernetes/order-worker.yaml` and `platform/envoy-gateway/proof-backend/`).
  - These manifests are historical proof artifacts not deployed to production from this repository.
  - In contrast, all repo-owned production workloads under `deploy/` enforce `readOnlyRootFilesystem: true`, non-root execution (`runAsNonRoot: true`), and full Linux capability drops (`capabilities.drop: ["ALL"]`), enforced by `scripts/policy-gate.py`.

---

## 4. Consequences & Verification

- **Enforcement**: Gate is enforced on GitHub Actions branch protection via `pr-gate.yaml`.
- **Auditability**: Every accepted risk is codified in `.trivyignore` with explicit reference to this ADR.
- **Gate Test**: `python tests/test_gates.py` asserts that all test roots are registered and that CI env variables match repository reality.

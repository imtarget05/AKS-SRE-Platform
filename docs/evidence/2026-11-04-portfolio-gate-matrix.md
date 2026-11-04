# Portfolio cloud gate matrix — 2026-11-04 UTC

**Decision: >90% with cloud evidence is not established. No production go-live.** This matrix uses the frozen denominators and strict PASS rule in [the baseline](2026-11-04-portfolio-cloud-baseline.md). Local gates count only when their required environment is LOCAL and the run identifies the immutable source SHA. Cloud gates require deployed release identity and cloud evidence; a public health response alone does not certify them. The three draft branches have green CI, but no complete cloud release has a matching image digest, frontend revision and verified rollback target.

| Repository | PASS | FAIL | OPEN | Denominator | Accepted score |
| --- | ---: | ---: | ---: | ---: | ---: |
| AKS-SRE-Platform | 11 | 0 | 3 | 14 | 78.57% |
| QuanLyKho | 0 | 0 | 21 | 21 | 0% |
| CreditFlow | 0 | 0 | 22 | 22 | 0% |

`portfolio = (11/14 + 0/21 + 0/22) / 3 = 26.19%` under the acceptance rule at this checkpoint. This is an evidence score, not a measure of code completeness. The AKS local checks below were rerun or proved by CI on source SHA `8437b0fd1790668b21d171d57374e1546800170a`, the same SHA as its [Cloudflare Pages preview](2026-11-04-cloudflare-preview-8437b0f.md). Preview reachability does not close Azure runtime gate A16.

## AKS-SRE-Platform

| ID | Gate | Status | Evidence / closure |
| --- | --- | --- | --- |
| A01 | Platform Python tests / LOCAL | PASS | [Raw local output](2026-11-04-A01-python-8437b0f.txt) and [timestamped CI Python job](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/41849472078): 59 tests passed locally, 89.82% coverage; CI passed on `8437b0f`. |
| A02 | G1–G16 invariants / LOCAL | PASS | [PR gate Python job](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/41849472078): gate matrix command passed on source SHA `8437b0f`. |
| A03 | Five Terraform test roots / LOCAL | PASS | [PR gate Terraform job and uploaded per-root logs](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/41849472078): all five roots passed, nonzero test guard enforced. |
| A04 | Terraform validate / LOCAL | PASS | [Raw run](2026-11-04-A04-terraform-validate-8437b0f.txt): all five roots valid, exit 0, current SHA. |
| A05 | Terraform format / LOCAL | PASS | [PR gate Terraform job](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/41849472078): recursive whole-repo format check passed. |
| A06 | GitOps external source validation / LOCAL | PASS | [Raw run](2026-11-04-A06-gitops-external-8437b0f.txt): 42 PASS, 0 FAIL, 0 NOT_PRESENT; all three mapped checkouts supplied on current SHA. |
| A07 | Static policy gate / LOCAL | PASS | [PR gate Kubernetes job](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/41849472078): static policy and image gate passed. |
| A08 | Maintained manifest render / LOCAL | PASS | [PR gate Kubernetes job](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/41849472078): all maintained Kustomize roots rendered and schema-checked. |
| A11 | HIGH/CRITICAL config scan / LOCAL | PASS | [PR gate security job](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/41849472078): Trivy config HIGH/CRITICAL scan passed; archive excluded from maintained scope. |
| A12 | Local kind health / LOCAL | PASS | [Raw run](2026-11-04-A12-kind-health-8437b0f.txt): 3/3 kind nodes Ready, kindnet 3/3; no NetworkPolicy inference. |
| A13 | NetworkPolicy enforcement / LOCAL capable-CNI proof | OPEN | Previous local proof exists; rerun on the immutable candidate and retain raw output, or for A16 verify live Azure state/workloads/cost and ownership. |
| A14 | Full platform/Compose integration / LOCAL | OPEN | Previous local proof exists; rerun on the immutable candidate and retain raw output, or for A16 verify live Azure state/workloads/cost and ownership. |
| A15 | tflint recursive / LOCAL | PASS | [PR gate Terraform job](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/41849472078): pinned AzureRM plugin and recursive lint passed. |
| A16 | Current Azure runtime, cost, state and production promotion / AZURE_VALIDATION | OPEN | [Private AKS Run Command evidence](2026-11-04-A16-private-aks-runcommand-8437b0f.txt): two tainted System nodes cannot schedule the transient command pod. Cluster workload/GitOps, state ownership, actual cost and rollback remain unverified. Cloudflare frontend preview is separate. |

## QuanLyKho

| ID | MVP journey | Status | Evidence / closure |
| --- | --- | --- | --- |
| QLK-CATALOG | See [frozen acceptance definition](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md) | OPEN | API/UI cloud journey, role/account and device proof on one release still required. |
| QLK-RECEIPT | See [frozen acceptance definition](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md) | OPEN | API/UI cloud journey, role/account and device proof on one release still required. |
| QLK-APPROVAL | See [frozen acceptance definition](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md) | OPEN | API/UI cloud journey, role/account and device proof on one release still required. |
| QLK-FEFO | See [frozen acceptance definition](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md) | OPEN | API/UI cloud journey, role/account and device proof on one release still required. |
| QLK-SHIFT-OPEN | See [frozen acceptance definition](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md) | OPEN | API/UI cloud journey, role/account and device proof on one release still required. |
| QLK-SHIFT-COUNT | See [frozen acceptance definition](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md) | OPEN | API/UI cloud journey, role/account and device proof on one release still required. |
| QLK-SHIFT-HANDOFF | See [frozen acceptance definition](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md) | OPEN | API/UI cloud journey, role/account and device proof on one release still required. |
| QLK-SHIFT-LOCK | See [frozen acceptance definition](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md) | OPEN | API/UI cloud journey, role/account and device proof on one release still required. |
| QLK-DAMAGE | See [frozen acceptance definition](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md) | OPEN | API/UI cloud journey, role/account and device proof on one release still required. |
| QLK-ADJUST | See [frozen acceptance definition](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md) | OPEN | API/UI cloud journey, role/account and device proof on one release still required. |
| QLK-ALERT-LOW | See [frozen acceptance definition](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md) | OPEN | API/UI cloud journey, role/account and device proof on one release still required. |
| QLK-ALERT-EXPIRY | See [frozen acceptance definition](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md) | OPEN | API/UI cloud journey, role/account and device proof on one release still required. |
| QLK-ALERT-VARIANCE | See [frozen acceptance definition](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md) | OPEN | API/UI cloud journey, role/account and device proof on one release still required. |
| QLK-ALERT-STREAM | See [frozen acceptance definition](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md) | OPEN | API/UI cloud journey, role/account and device proof on one release still required. |
| QLK-REPORT-XNT | See [frozen acceptance definition](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md) | OPEN | API/UI cloud journey, role/account and device proof on one release still required. |
| QLK-REPORT-TOP | See [frozen acceptance definition](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md) | OPEN | API/UI cloud journey, role/account and device proof on one release still required. |
| QLK-REPORT-HISTORY | See [frozen acceptance definition](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md) | OPEN | API/UI cloud journey, role/account and device proof on one release still required. |
| QLK-RBAC | See [frozen acceptance definition](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md) | OPEN | API/UI cloud journey, role/account and device proof on one release still required. |
| QLK-AUDIT | See [frozen acceptance definition](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md) | OPEN | API/UI cloud journey, role/account and device proof on one release still required. |
| QLK-OFFLINE-NATIVE | See [frozen acceptance definition](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md) | OPEN | API/UI cloud journey, role/account and device proof on one release still required. |
| QLK-PLATFORMS | See [frozen acceptance definition](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-03-verification-checkpoint.md) | OPEN | API/UI cloud journey, role/account and device proof on one release still required. |

## CreditFlow

| ID | Control or gate | Status | Evidence / closure |
| --- | --- | --- | --- |
| SEC-01 | No built-in operator accounts or signing secret | OPEN | Local synthetic test support exists; rerun security/CI on immutable candidate, verify deployed revision and required environment. |
| SEC-02 | Applicant workflow requires identity | OPEN | Local synthetic test support exists; rerun security/CI on immutable candidate, verify deployed revision and required environment. |
| SEC-03 | Production separates human and machine identity | OPEN | Local synthetic test support exists; rerun security/CI on immutable candidate, verify deployed revision and required environment. |
| SEC-04 | Runtime user revocation blocks bearer tokens | OPEN | Local synthetic test support exists; rerun security/CI on immutable candidate, verify deployed revision and required environment. |
| SEC-05 | Production application reads are scoped to the staff queue | OPEN | Local synthetic test support exists; rerun security/CI on immutable candidate, verify deployed revision and required environment. |
| PRIV-01 | Browser does not persist applicant profiles | OPEN | Local synthetic test support exists; rerun security/CI on immutable candidate, verify deployed revision and required environment. |
| WF-01 | Review task creation and controlled actions | OPEN | Local synthetic test support exists; rerun security/CI on immutable candidate, verify deployed revision and required environment. |
| WF-05 | Business-calendar deadline calculations | OPEN | Local synthetic test support exists; rerun security/CI on immutable candidate, verify deployed revision and required environment. |
| WF-02 | Missing-document metadata check | OPEN | Local synthetic test support exists; rerun security/CI on immutable candidate, verify deployed revision and required environment. |
| WF-03 | Repeated profile review signal | OPEN | Local synthetic test support exists; rerun security/CI on immutable candidate, verify deployed revision and required environment. |
| WF-04 | Staff pilot queue and in-app reminders | OPEN | Local synthetic test support exists; rerun security/CI on immutable candidate, verify deployed revision and required environment. |
| MON-01 | One source of truth for drift | OPEN | Local synthetic test support exists; rerun security/CI on immutable candidate, verify deployed revision and required environment. |
| MON-02 | Loan outcome tracking and portfolio metrics | OPEN | Local synthetic test support exists; rerun security/CI on immutable candidate, verify deployed revision and required environment. |
| SAFE-01 | Demo decision path is closed in production | OPEN | Local synthetic test support exists; rerun security/CI on immutable candidate, verify deployed revision and required environment. |
| CF-G01 (P0) | Bank IdP and user lifecycle | OPEN | Bank/system owner, approved artifact and dated integration/UAT evidence required; synthetic data does not close this gate. |
| CF-G02 (P0) | Real-data rights and independent model validation | OPEN | Bank/system owner, approved artifact and dated integration/UAT evidence required; synthetic data does not close this gate. |
| CF-G03 (P0) | Decision and core banking contract | OPEN | Bank/system owner, approved artifact and dated integration/UAT evidence required; synthetic data does not close this gate. |
| CF-G04 (P0) | Privacy and security review | OPEN | Bank/system owner, approved artifact and dated integration/UAT evidence required; synthetic data does not close this gate. |
| CF-G05 (P0) | Disaster recovery | OPEN | Bank/system owner, approved artifact and dated integration/UAT evidence required; synthetic data does not close this gate. |
| CF-G06 (P1) | Complete daily staff workflow | OPEN | Bank/system owner, approved artifact and dated integration/UAT evidence required; synthetic data does not close this gate. |
| CF-G07 (P1) | Portfolio monitoring with delayed outcomes | OPEN | Bank/system owner, approved artifact and dated integration/UAT evidence required; synthetic data does not close this gate. |
| CF-G08 (P1) | Operational quality bar | OPEN | Bank/system owner, approved artifact and dated integration/UAT evidence required; synthetic data does not close this gate. |

## Evidence and release decision

- AKS: [initial cloud inventory](2026-11-04-cloud-inventory.log) observed 3 Ready nodes at that time; the later [Azure Run Command recheck](2026-11-04-A16-private-aks-runcommand-8437b0f.txt) found a 2-node tainted System pool and could not inspect workloads. Terraform state ownership and actual cost remain open. [pr-gate](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/41849472078), [GitOps](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/41849472157), [SBOM](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/41849472108) and external SonarCloud passed on `8437b0f`; [Pages Preview](2026-11-04-cloudflare-preview-8437b0f.md) was browser tested on that SHA. This does not close A16.
- QuanLyKho: migration from an empty isolated PostgreSQL database reaches `034_general_ledger_coa`; the full backend suite ended with **975 passed, 8 skipped, 1 xfailed, 0 failed** after fixing the idempotency collision. [CI](https://github.com/imtarget05/QuanLyKho/actions/runs/41848609393), [S9 kind](https://github.com/imtarget05/QuanLyKho/actions/runs/41848609354) and external SonarCloud passed on `18bd344`; Flutter web build and Worker typecheck passed. The current public API and web HTTP 200 are reachability only; no 21-ID cloud/device UAT is recorded.
- CreditFlow: [CI](https://github.com/imtarget05/CreditFlow/actions/runs/41846011816), [gateway checks](https://github.com/imtarget05/CreditFlow/actions/runs/41846011762) and external SonarCloud passed on `b5b69ea`; Python dependency audit, Gitleaks, Trivy and the 14 fictional demo prediction cases passed. ACA still serves image `:latest` at revision `creditflow-api--mbcr9yc`, so no source SHA can be proven for the live service. Azure deploy failed before rollout because required OIDC inputs are absent. The bank-input [handoff template](/Users/mainguyenbinhtan/Downloads/CreditFlow/docs/qa/SACOMBANK_INPUTS_FOR_PILOT.md) exists; no owner approvals supplied.
- Go-live: **AKS OPEN, QuanLyKho OPEN, CreditFlow OPEN.** The respective cloud, product and bank owners must approve the release after their evidence is collected. No approval signature is recorded here. No production deploy or real applicant data use is authorized by this checkpoint.

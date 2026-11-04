# Portfolio cloud gate matrix — 2026-11-04 UTC

**Decision: >90% with cloud evidence is not established. No production go-live.** This matrix uses the frozen denominators and strict PASS rule in [the baseline](2026-11-04-portfolio-cloud-baseline.md). A local test or public health response supports investigation but does not certify a gate against a single immutable release deployed to its required environment. The three working trees still contain uncommitted work. No release candidate SHA, image digest, frontend revision or verified rollback target has been locked.

| Repository | PASS | FAIL | OPEN | Denominator | Accepted score |
| --- | ---: | ---: | ---: | ---: | ---: |
| AKS-SRE-Platform | 0 | 1 | 13 | 14 | 0% |
| QuanLyKho | 0 | 0 | 21 | 21 | 0% |
| CreditFlow | 0 | 0 | 22 | 22 | 0% |

`portfolio = (0/14 + 0/21 + 0/22) / 3 = 0%` under the acceptance rule at this checkpoint. This is an evidence score, not a measure of code completeness. The earlier AKS 13/14 local result remains local-only.

## AKS-SRE-Platform

| ID | Gate | Status | Evidence / closure |
| --- | --- | --- | --- |
| A01 | Platform Python tests / LOCAL | OPEN | Previous local proof exists; rerun on the immutable candidate and retain raw output, or for A16 verify live Azure state/workloads/cost and ownership. |
| A02 | G1–G16 invariants / LOCAL | OPEN | Previous local proof exists; rerun on the immutable candidate and retain raw output, or for A16 verify live Azure state/workloads/cost and ownership. |
| A03 | Five Terraform test roots / LOCAL | OPEN | Previous local proof exists; rerun on the immutable candidate and retain raw output, or for A16 verify live Azure state/workloads/cost and ownership. |
| A04 | Terraform validate / LOCAL | OPEN | Previous local proof exists; rerun on the immutable candidate and retain raw output, or for A16 verify live Azure state/workloads/cost and ownership. |
| A05 | Terraform format / LOCAL | OPEN | Previous local proof exists; rerun on the immutable candidate and retain raw output, or for A16 verify live Azure state/workloads/cost and ownership. |
| A06 | GitOps external source validation / LOCAL | FAIL | Current local GitOps validator reports 47 PASS, 2 FAIL, 1 NOT_PRESENT for uncommitted FlashSale application source/project mapping; fix and rerun on a candidate SHA. |
| A07 | Static policy gate / LOCAL | OPEN | Previous local proof exists; rerun on the immutable candidate and retain raw output, or for A16 verify live Azure state/workloads/cost and ownership. |
| A08 | Maintained manifest render / LOCAL | OPEN | Previous local proof exists; rerun on the immutable candidate and retain raw output, or for A16 verify live Azure state/workloads/cost and ownership. |
| A11 | HIGH/CRITICAL config scan / LOCAL | OPEN | Previous local proof exists; rerun on the immutable candidate and retain raw output, or for A16 verify live Azure state/workloads/cost and ownership. |
| A12 | Local kind health / LOCAL | OPEN | Previous local proof exists; rerun on the immutable candidate and retain raw output, or for A16 verify live Azure state/workloads/cost and ownership. |
| A13 | NetworkPolicy enforcement / LOCAL capable-CNI proof | OPEN | Previous local proof exists; rerun on the immutable candidate and retain raw output, or for A16 verify live Azure state/workloads/cost and ownership. |
| A14 | Full platform/Compose integration / LOCAL | OPEN | Previous local proof exists; rerun on the immutable candidate and retain raw output, or for A16 verify live Azure state/workloads/cost and ownership. |
| A15 | tflint recursive / LOCAL | OPEN | Previous local proof exists; rerun on the immutable candidate and retain raw output, or for A16 verify live Azure state/workloads/cost and ownership. |
| A16 | Current Azure runtime, cost, state and production promotion / AZURE_VALIDATION | OPEN | Previous local proof exists; rerun on the immutable candidate and retain raw output, or for A16 verify live Azure state/workloads/cost and ownership. |

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

- AKS read-only Azure inventory and commands: [raw cloud log](2026-11-04-cloud-inventory.log). Cluster has 3 Ready nodes, but no verified application workload or Argo CD CRD. Terraform state ownership and cost approval remain open. Previous [pr-gate](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/41284254764) and [SBOM](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/41284254830) runs failed on `0dac76e`; draft [PR #18](https://github.com/imtarget05/AKS-SRE-Platform/pull/18) has green Terraform, Kubernetes, security, Python, source SBOM and SonarCloud jobs on its committed branch. This does not close A16.
- QuanLyKho: migration from an empty isolated PostgreSQL database reaches `034_general_ledger_coa`; Ruff and Flutter analysis pass; Flutter unit/widget suite has 355 passes. A full backend recheck is in progress following the idempotency collision fix. Current public API and web HTTP 200 are reachability only.
- CreditFlow: 597 passed, 1 skipped, 23 deselected in the CI subset; Python dependency audit found no known vulnerabilities; 14 fictional demo prediction cases validated. ACA currently serves image `:latest` at revision `creditflow-api--mbcr9yc`, so no source SHA can be proven for the live service. Azure OIDC secret names needed by the production deploy are absent. The bank-input [handoff template](/Users/mainguyenbinhtan/Downloads/CreditFlow/docs/qa/SACOMBANK_INPUTS_FOR_PILOT.md) exists; no owner approvals supplied.
- Go-live: **AKS OPEN, QuanLyKho OPEN, CreditFlow OPEN.** The respective cloud, product and bank owners must approve the release after their evidence is collected. No approval signature is recorded here. No production deploy or real applicant data use is authorized by this checkpoint.

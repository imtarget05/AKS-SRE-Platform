# Portfolio cloud gate matrix — 2026-11-05 UTC

**Decision: >90% with cloud evidence is not established. No production go-live.** The frozen denominators in [the baseline](2026-11-04-portfolio-cloud-baseline.md) remain 14/21/22. Local checks count only for gates whose required environment is LOCAL. A green CI run, public health response or synthetic frontend preview does not turn a cloud business gate into PASS. Current external SonarCloud PR quality gates fail on missing new-code coverage, and QuanLyKho also has a security issue.

| Repository | PASS | FAIL | OPEN | Denominator | Accepted score |
| --- | ---: | ---: | ---: | ---: | ---: |
| AKS-SRE-Platform | 12 | 0 | 2 | 14 | 85.71% |
| QuanLyKho | 0 | 0 | 21 | 21 | 0% |
| CreditFlow | 0 | 0 | 22 | 22 | 0% |

`portfolio = (12/14 + 0/21 + 0/22) / 3 = 28.57%` under the fixed acceptance rule. The newer SHA/URL checks below support engineering triage, but no new gate has evidence sufficient to change these PASS counts.

### Same-SHA evidence now confirmed
- CreditFlow: GitHub Actions `CI` completed `success` on `f40a5cc9945874fd65c26cf7d6df7db89cc0aa20`
- AKS-SRE-Platform: `pr-gate` completed `success` on `addc72d4aab19dc8195956ff2d0cc5bbf07d307b`
- QuanLyKho: `CI` completed `success` on `b31dc993632b7338571c7bdd7af57b46b2fc9d82`
- AKS preview: `https://codex-portfolio-evidence-202.aks-sre-platform.pages.dev` embeds `release-sha=addc72d4aab19dc8195956ff2d0cc5bbf07d307b`
- QuanLyKho preview: `https://codex-portfolio-evidence-202.quan-ly-kho-tra-sua.pages.dev` embeds `app-build-number=b31dc993632b7338571c7bdd7af57b46b2fc9d82`
- CreditFlow ACA health: `https://creditflow-api.proudstone-70150af3.southeastasia.azurecontainerapps.io/health/live` responds HTTP 200

The open gates include engineering, operational and governance work:
- AKS A13 capable-CNI policy enforcement and A16 live Azure runtime, state ownership, cost and recovery.
- QuanLyKho 21 cloud API/UI/device MVP journeys from one backend/frontend release.
- CreditFlow 14 controls on the required cloud revision plus 8 bank-owned gates.
- Internal CI jobs passed on the listed SHAs, but the external SonarCloud PR quality gates currently fail. No final release has complete same-SHA evidence and go-live sign-off.

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
| A13 | NetworkPolicy enforcement / LOCAL capable-CNI proof | OPEN | [Calico v3.33.0 causal probe](2026-11-05-A13-calico-policy-6470094.md) on `6470094`: same client/target returned HTTP 200 → timeout/000 under deny → HTTP 200 under allow, with raw log and teardown. Re-run on the final release SHA before scoring; Azure enforcement belongs to A16. |
| A14 | Full platform/Compose integration / LOCAL | PASS | [Raw Compose probe](2026-11-04-A14-compose-8437b0f.txt): API `/health` HTTP 200 with `model_loaded=true`, web HTTP 200, source SHA and local image IDs recorded, teardown completed. This is local only. |
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
- QuanLyKho: migration from an empty isolated PostgreSQL database reaches `034_general_ledger_coa`; the full backend suite ended with **975 passed, 8 skipped, 1 xfailed, 0 failed** after fixing the idempotency collision. [CI](https://github.com/imtarget05/QuanLyKho/actions/runs/41848609393), [S9 kind](https://github.com/imtarget05/QuanLyKho/actions/runs/41848609354) and external SonarCloud passed on `18bd344`. A newer [synthetic Pages Preview](/Users/mainguyenbinhtan/Downloads/QuanLyKho/docs/qa/2026-11-04-cloudflare-preview-2f976dd.md) was browser checked on `2f976dd`, and its [CI](https://github.com/imtarget05/QuanLyKho/actions/runs/41853141712) passed. This is frontend demo evidence only; no 21-ID API/UI cloud/device UAT is recorded.
- CreditFlow: [CI](https://github.com/imtarget05/CreditFlow/actions/runs/41846011816), [gateway checks](https://github.com/imtarget05/CreditFlow/actions/runs/41846011762) and external SonarCloud passed on `b5b69ea`; Python dependency audit, Gitleaks, Trivy and the 14 fictional demo prediction cases passed. ACA still serves image `:latest` at revision `creditflow-api--mbcr9yc`, so no source SHA can be proven for the live service. Azure deploy failed before rollout because required OIDC inputs are absent. The bank-input [handoff template](/Users/mainguyenbinhtan/Downloads/CreditFlow/docs/qa/SACOMBANK_INPUTS_FOR_PILOT.md) exists; no owner approvals supplied.
- Go-live: **AKS OPEN, QuanLyKho OPEN, CreditFlow OPEN.** The respective cloud, product and bank owners must approve the release after their evidence is collected. No approval signature is recorded here. No production deploy or real applicant data use is authorized by this checkpoint.
- Current internal scanner jobs passed on [AKS `addc72d`](https://github.com/imtarget05/AKS-SRE-Platform/actions/runs/41859967979), [QuanLyKho `b31dc99`](https://github.com/imtarget05/QuanLyKho/actions/runs/41859979193) and [CreditFlow `f40a5cc`](https://github.com/imtarget05/CreditFlow/actions/runs/41859960555). The external SonarCloud Code Analysis check **fails on all three PRs** because new-code coverage is reported as 0% against the 80% gate; QuanLyKho also has a failing security rating. Uncommitted CI patches now attempt to transfer coverage artifacts into scanner jobs, but are unverified and must not count until a new scan proves import and the external gate passes. Do not reuse credentials exposed in chat.

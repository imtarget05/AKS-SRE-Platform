# 2026-10-20 — Merge note for `recovery/g2-20261020`

**Written:** 2026-10-20 · **Branch:** `recovery/g2-20261020`
**HEAD at the time of writing:** `7801901c213deddd46fd09e7cb1f617f49d3a79f`
**Base (`main`):** `0a92f58cf453ca121993bfe1b111c5308886754f` — **unchanged, and
it is exactly the merge-base.**

> **Nothing was merged, rebased or pushed.** This document is the *proposal*
> for integration. The branch is left exactly as it was found: 7 commits on top
> of `main`, working tree clean, no stash touched, no remote touched.

---

## 1. What the branch contains

7 commits, 16 files, `+1733 / −193`.

```console
$ git log --oneline main..HEAD
7801901 chore(gitops): load order-api image and verify Argo CD sync + self-heal
509d31a docs: clarify cloud evidence and demo operations
9191d3d docs(evidence): 2026-10-20 local platform re-verification
e37c113 chore(argocd): pin Argo CD version
86751b0 fix(gitops): fail on duplicate AppProject names, validate every project file
910cf52 fix(observability): preserve all dashboard definitions
308eba8 fix(gitops): server-side apply for Argo CD CRDs

$ git diff main --stat
 .github/workflows/pr-gate.yaml                     |   2 +-
 MANIFEST-INVENTORY.md                              |   8 +-
 README.md                                          |   7 +-
 docs/EVIDENCE.md                                   |   3 +-
 docs/evidence/local-platform/2026-10-20-reverify.md | 1104 ++++++++++++++++++++
 docs/evidence/local-platform/l4-argocd-PASS.md     |  42 +-
 docs/interview-demo/local-platform.md              |   2 +-
 docs/runbooks/portfolio-demo-operations.md         |  43 +
 gitops/projects/portfolio.yaml                     |  38 -
 gitops/validate-gitops.py                          | 126 ++-
 platform/argocd/README.md                          |  32 +-
 platform/argocd/VERSION                            |   1 +
 platform/observability/dashboards.yaml             | 115 +-
 platform/observability/dashboards/local-platform-dashboard.yaml | 125 ++-
 scripts/bootstrap.sh                               |  72 +-
 tests/test_gates.py                                | 206 ++-
 16 files changed, 1733 insertions(+), 193 deletions(-)
```

### 1.1 The six commits authored in this work

| Commit | Subject | What it changes | Why it exists |
|---|---|---|---|
| `308eba8` | `fix(gitops): server-side apply for Argo CD CRDs` | `scripts/bootstrap.sh` | **F1.** The script applied the Argo CD install manifest **client-side**, which *replaced* the CRDs and destroyed the custom resources already on the cluster. Now `--server-side --force-conflicts`. |
| `910cf52` | `fix(observability): preserve all dashboard definitions` | `platform/observability/dashboards.yaml`, `.../dashboards/local-platform-dashboard.yaml`, `MANIFEST-INVENTORY.md` | **F2.** Two files owned the same `grafana-dashboard-local-platform` ConfigMap and the second overwrote the first, **losing a dashboard**. Now one file is the single owner and the other documents that it no longer owns it — **no dashboard was dropped**. |
| `86751b0` | `fix(gitops): fail on duplicate AppProject names, validate every project file` | `gitops/validate-gitops.py`, `gitops/projects/portfolio.yaml` (deleted), `MANIFEST-INVENTORY.md`, `.github/workflows/pr-gate.yaml`, `tests/test_gates.py` | **F3 + F4.** The validator iterated over *one* project file and silently skipped the rest, and a second `AppProject` with a **wildcard** allowlist existed. Now every project file is validated, duplicate names are a hard failure, and the duplicate file is deleted. |
| `e37c113` | `chore(argocd): pin Argo CD version` | `platform/argocd/VERSION` (**new**), `scripts/bootstrap.sh`, `platform/argocd/README.md`, `docs/EVIDENCE.md`, `README.md`, `docs/interview-demo/local-platform.md`, `docs/evidence/local-platform/l4-argocd-PASS.md`, `tests/test_gates.py` | **F5.** Argo CD was installed from the **floating `stable` branch** while the docs claimed a pin — the installed version and the documented version were different facts. The pin now lives in exactly one file (`platform/argocd/VERSION` = `v3.5.5`), the installer reads it, and it **asserts** the running image matches it. |
| `9191d3d` | `docs(evidence): 2026-10-20 local platform re-verification` | `docs/evidence/local-platform/2026-10-20-reverify.md` (**new**, 1104 lines), `tests/test_gates.py` | The evidence document for F1–F5, with a failing-before / passing-after test per fix. |
| `7801901` | `chore(gitops): load order-api image and verify Argo CD sync + self-heal` | `docs/evidence/local-platform/2026-10-20-reverify.md` | Adds §9: the image load into `local-platform`, the Application reaching `Synced`/`Healthy`, the PreSync hook green, and the self-heal measurements. |

Each of F1–F5 has a **regression gate** in `tests/test_gates.py` (groups
G11, G12, G13), so a future change that reintroduces any of them fails the
test suite rather than the next incident.

### 1.2 The one commit from another actor — `509d31a`

| Field | Value |
|---|---|
| Commit | `509d31a54c88acacf53bb5df95bf19f1fd62b55f` |
| Subject | `docs: clarify cloud evidence and demo operations` |
| Author | `imtarget05 <binhtan5734@gmail.com>` |
| Date | 2026-10-20 22:53:58 +0700 |
| Files | `README.md` (+5/−2), `docs/runbooks/portfolio-demo-operations.md` (**new**, +43) |
| **What it does** | Rewords the README's "what has not happened yet" paragraph (no persistent cluster / no live Azure CI login / no HPA runtime proof / no measured NetworkPolicy enforcement / no SLO history) and adds a demo-operations runbook. |

**This commit was NOT authored by the actor who produced the other six.** It
is already part of the branch's linear history, between `9191d3d` and
`7801901`, and it must be **preserved as-is**:

- It sits **after** `e37c113` in the history, so its `README.md` hunk
  (line ~29) is applied on top of the `e37c113` hunk (line ~77). They do not
  overlap.
- It adds a **new file** (`docs/runbooks/portfolio-demo-operations.md`) that
  nothing else on the branch touches.
- Dropping it would silently remove a runbook and re-introduce the looser
  wording of the README paragraph — i.e. it would **re-open an honesty
  regression** on a branch whose whole point is that the docs do not
  overstate what was verified.

**Also present and deliberately untouched:** a stash entry,
`stash@{0}: On recovery/g2-20261020: preserve-user-wip-before-portfolio-2026-10-20`.
It was left in place by this work and **must not be dropped or applied** as
part of this integration — it belongs to another actor's in-flight work.

---

## 2. Conflict risk with the current `main`

### 2.1 The good news — `main` has not moved

```console
$ git merge-base main HEAD
0a92f58cf453ca121993bfe1b111c5308886754f
$ git rev-parse main
0a92f58cf453ca121993bfe1b111c5308886754f
$ git log --oneline HEAD..main
(empty — main has no commit that the branch does not contain)
```

`main` **is** the merge-base. The branch is a strict, linear descendant — so
the integration is a **fast-forward**, with **zero merge conflict** and no
merge commit required.

### 2.2 This was tested, not assumed

Both scenarios were rehearsed in a **throwaway clone** (`git clone
--no-hardlinks . /tmp/mr-clone`), so the source repository was never
mutated. The clone was deleted afterwards; the source repo's `git status`
was re-checked and only the intended documentation edits were present.

**Test 1 — merge the branch into `main`:**

```console
$ git checkout main && git merge --no-commit --no-ff recovery/g2-20261020
Automatic merge went well; stopped before committing as requested
MERGE_RC=0
```

**Test 2 — cherry-pick only the six own commits, skipping the foreign
`509d31a`** (the scenario where a reviewer wants to integrate only the
F1–F5 work):

```console
$ git cherry-pick -x 308eba8 910cf52 86751b0 e37c113 9191d3d 7801901
  OK   308eba8
  OK   910cf52
  OK   86751b0
  OK   e37c113
  OK   9191d3d
  OK   7801901

$ git diff --stat recovery/g2-20261020 HEAD
 README.md                                  |  5 ++--
 docs/runbooks/portfolio-demo-operations.md | 43 ------------------------------
```

All six apply **cleanly, with no conflict and no manual resolution**. The
resulting tree differs from the branch in exactly the two files the foreign
commit owns — which is the expected and correct result, not a defect.

### 2.3 The risk that *does* exist

| Risk | Severity | Assessment |
|---|---|---|
| **`main` moves before the integration** | **Low–Medium** | The fast-forward is only valid while `main` is still `0a92f58`. If `main` advances, the fast-forward becomes a real merge and the files below are the ones to re-check. They are the files most likely to be edited by other actors' work. |
| Files to re-check if `main` moves | — | `README.md` (edited by **both** this branch and `509d31a`), `MANIFEST-INVENTORY.md`, `docs/EVIDENCE.md`, `scripts/bootstrap.sh`, `gitops/validate-gitops.py`, `tests/test_gates.py`, `platform/observability/dashboards.yaml`, `platform/observability/dashboards/local-platform-dashboard.yaml`, `.github/workflows/pr-gate.yaml`, `gitops/projects/portfolio.yaml` (**deleted** by `86751b0` — a delete/modify conflict is the most likely symptom). |
| **The deleted `gitops/projects/portfolio.yaml`** | **Medium** | `86751b0` deletes it because it duplicated the canonical `platform/argocd/appproject.yaml` and carried a **wildcard** allowlist (F4). If another actor re-adds or edits that file, the delete must win — otherwise a duplicate `AppProject` name returns, which is exactly what gate **G11** now fails on. |
| **The dashboard split (F2)** | **Medium** | `platform/observability/dashboards.yaml` and `.../dashboards/local-platform-dashboard.yaml` were two owners of one ConfigMap. If another actor edits `dashboards.yaml` expecting it to still own the dashboard, gate **G13** ("no two files declare the same object") will catch it — but the intent has to be reconciled by hand, not by force-push. |
| **The Argo CD version pin (F5)** | **Low** | `platform/argocd/VERSION` is a new file and the single source of truth. If another actor bumps the version in `platform/argocd/README.md` or `docs/EVIDENCE.md` **without** changing `VERSION`, gate **G12** fails ("every document that claims a version claims THE pinned one"). The fix is always to change `platform/argocd/VERSION`, never the docs alone. |
| **The foreign commit `509d31a`** | **Low, but must not be dropped** | §1.2. It is inside the branch's history; a reviewer cherry-picking "only my commits" would remove a runbook and re-open an honesty regression. |
| **The stash `stash@{0}`** | **Low, but must not be touched** | Another actor's in-flight work. Not applied, not dropped. |
| **Runtime risk (not a git conflict)** | **Medium** | Merging this branch changes what `scripts/bootstrap.sh` does — it now installs a **pinned** Argo CD `v3.5.5` and applies it **server-side**. Anyone running the bootstrap against an existing cluster should expect the install to be **reconciled to the pin**, and the Argo CD CRDs to be **preserved** rather than replaced (that is F1). |

---

## 3. Proposed integration order

**Nothing below was executed.** It is the recommended sequence for whoever
owns the integration.

### Step 1 — re-check the base (cheap, and it invalidates everything else if it fails)

```bash
git fetch origin
git log --oneline HEAD..origin/main      # must still be empty
git merge-base --is-ancestor origin/main HEAD && echo "FAST-FORWARD POSSIBLE"
```

If `HEAD..origin/main` is **not** empty, stop and go to Step 4.

### Step 2 — run the gates on the branch tip, before touching `main`

```bash
python3 scripts/policy-gate.py        # → POLICY GATE PASS: 2 kustomize root(s), 26 object(s)
python3 gitops/validate-gitops.py     # → 16 passed, 0 failed, 2 not-present, 18 total
python3 tests/test_gates.py           # → 42 passed, 0 failed, 42 assertions total
```

### Step 3 — fast-forward `main` (the normal path, zero conflicts)

```bash
git checkout main
git merge --ff-only recovery/g2-20261020     # --ff-only makes a non-FF a hard error, not a surprise merge
python3 scripts/policy-gate.py && python3 gitops/validate-gitops.py && python3 tests/test_gates.py
```

`--ff-only` is deliberate: if `main` has moved, it **refuses** rather than
creating a merge commit that would hide the difference.

### Step 4 — if `main` has moved, do it as an explicit merge instead

```bash
git checkout main
git merge --no-ff recovery/g2-20261020 -m "merge: recovery/g2-20261020 (F1-F5 fixes + 2026-10-20 evidence)"
# resolve, in this order of priority:
#   1. gitops/projects/portfolio.yaml  → keep the DELETION (G11 depends on it)
#   2. platform/observability/dashboards*.yaml → keep ONE owner of
#      grafana-dashboard-local-platform (G13 depends on it)
#   3. platform/argocd/VERSION → the single source of truth; if a version is
#      disputed, change VERSION and let G12 point at every doc that must follow
#   4. README.md → keep BOTH hunks (the e37c113 version line AND the 509d31a
#      "what has not happened yet" paragraph)
git rerere status    # if the conflict was resolved once, reuse it
python3 scripts/policy-gate.py && python3 gitops/validate-gitops.py && python3 tests/test_gates.py
```

### Step 5 — the runtime check that only a human can authorise

Merging the branch changes the **installer**, so the cluster must be
re-bootstrapped to prove the new bootstrap still works end to end. That is a
cluster mutation and needs an explicit go-ahead:

```bash
bash scripts/bootstrap.sh        # → installs Argo CD v3.5.5 (pinned), server-side
kubectl -n argocd get applications
```

Expect `flashsale` → `Synced` / `Healthy`. If the branch's `flashsale`
Application is `Degraded`, the usual cause is the **platform Gateway**
missing (see §9.4 (d) of the evidence document) — not a regression.

### Step 6 — record the merge

- Update `docs/EVIDENCE.md` with the new `main` SHA and the branch name.
- Update `tasks/current.md` → point at the merged state.
- Do **not** delete `docs/evidence/local-platform/2026-10-20-reverify.md` or
  this note. They are the record of what was and was not verified.

---

## 4. What merging this branch does **not** bring in

Being explicit, because the whole point of the branch is that the docs do
not overstate what was verified:

- **No Azure verification.** Zero `AZURE_CLOUD_VERIFIED` rows exist in the
  evidence document. Merging does not create any.
- **No `legacyapp` deployment.** `scripts/bootstrap.sh` still refuses
  `legacyapp.yaml` unless `APPLY_LEGACYAPP=1` (ADR-015 source switch not
  approved).
- **No business E2E / concurrency proof.** Only the deployment plane was
  proven.
- **No `sre-demo-api` pod-level RED metrics.** The image reference points at
  a destroyed ACR registry.
- **No fix for the label-drift finding.** It is recorded as a finding
  (§10 of the evidence document), explicitly **not** as a pass.
- **No fix for the second Argo CD install in the `default` namespace.** It is
  pre-existing and needs an explicit decision.

The open items and their owners are listed in §11 of
[`2026-10-20-reverify.md`](2026-10-20-reverify.md).

---

## 5. One-line summary

`recovery/g2-20261020` is **7 commits on top of an unmoved `main`
(`0a92f58`)**, of which **6 are the F1–F5 fixes plus their evidence and
1 (`509d31a`) belongs to another actor and must be preserved**; it merges
**cleanly** (verified in a throwaway clone: `git merge` → "Automatic merge
went well", and a cherry-pick of the 6 own commits → all clean), so the
integration is a **`--ff-only` fast-forward** — but the Argo CD **pin**
(`platform/argocd/VERSION` = `v3.5.5`), the **server-side apply** (F1), the
**single dashboard owner** (F2) and the **duplicate-AppProject deletion**
(F4) must survive the merge, and the runtime bootstrap must be re-proven
after it.

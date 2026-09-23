# L7 — Productionized-LegacyApp (P02) on kind — PASS

Repository: `Productionized-LegacyApp` @ `41ecc9a` (`main`). Namespace: `legacyapp`.

## Spec02 Phase 0 audit (run, not skipped)

| Area | Finding |
|---|---|
| Application | Node/Express-style HTTP service; routes served from `src/`; `/health` + business endpoints exist |
| Dockerfile | Multi-stage, builds for the local architecture; base image is arm64-capable (`node`) |
| CI | Repo CI runs manifest validation; the prod overlay image pin is written by CI (observed: CI pushed `gitops: pin prod overlay to legacy-app:<sha>` twice during this session) |
| Kubernetes base + overlay | `infrastructure/kubernetes/base` + `overlays/prod` only — **no local overlay existed** |
| Legacy Terraform | Superseded/archived by the repo's own decision commit; not applied here |
| Blockers for local runtime | Exactly one: no local overlay, so nothing could reference a locally built image |

## What was added (P02 repo, commit `41ecc9a`)

`infrastructure/kubernetes/overlays/local/`:

* `kustomization.yaml` — namespace `legacyapp`, image renamed to `legacy-app:local` built from this
  repo's Dockerfile for `linux/arm64`, `imagePullPolicy: Never` (the image is preloaded on every kind
  node), `commonLabels: env=local`.
* `httproute.yaml` — hostname route `legacy.local` → `legacy-app:80` attached to the shared portfolio
  Gateway (cross-namespace parentRef, same-namespace backendRef → no ReferenceGrant needed).

`overlays/prod` and its immutable-SHA semantics were **not** modified.

## Runtime verification

| Check | Evidence |
|---|---|
| Image | `legacy-app:local`, arm64, built from source, loaded 3/3 kind nodes |
| Pod | `legacy-app-56bd4dc775-…` **1/1 Running**, `imagePullPolicy: Never` |
| Non-root | `runAsNonRoot: true`, `runAsUser` set in base manifest (unchanged) |
| Read-only root FS | `readOnlyRootFilesystem: true` (unchanged from base) |
| Privilege escalation | `allowPrivilegeEscalation: false` (unchanged) |
| Capabilities | `drop: [ALL]` (unchanged) |
| Requests/limits | present in base manifest (unchanged) |
| Liveness / readiness | both defined and passing (pod is Ready) |
| Health endpoint | `GET /health` → `{"status":"healthy"}` (verified in-cluster and through the Gateway) |
| Business endpoint | served on `/` (verified through the shared Gateway, HTTP 200) |

No secret values are committed: the repo's manifests reference no literal credentials, and no Secret
was needed for this service.

## Security context — untouched, and nothing had to be weakened

The base manifest already carries `runAsNonRoot: true` (with `runAsUser`), container-level
`allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, requests/limits and both probes.
The local overlay changes **only** the image reference and pull policy, so the service runs under the
production security context unchanged. It reaches Ready with a read-only root filesystem and needs no
writable temp mount — verified, not assumed (no `emptyDir` was added, and none was required).

Gate: **L7 PASS**.

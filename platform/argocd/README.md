# `platform/argocd` — local GitOps control plane (L4)

Status: **installed and healthy locally on 2026-09-23.** Evidence:
`docs/evidence/local-platform/l4-argocd-PASS.md` (created with the phase report).

This directory owns the **local** Argo CD installation used to prove real
reconciliation (L9) for both applications. It is deliberately the upstream
bundle — no fork, no custom chart — so the local control plane behaves like the
one documented for AKS.

## Pin (no floating tags)

| Item | Value |
|---|---|
| Version | **v3.5.5** (`https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.5/manifests/install.yaml`) |
| Source of truth | **`platform/argocd/VERSION`** — the one file the pin lives in |
| Mode | **non-HA** multi-tenant bundle (evaluation/demo sizing, single replica per component) |
| Namespace | `argocd` |
| Server exposure | **ClusterIP only** (no LoadBalancer, no NodePort, not routed through Envoy Gateway) |

`stable` / `latest` / `main` are deliberately NOT used: the manifest would then
be whatever upstream happens to have that day, and a local platform whose GitOps
controller changes silently is not reproducible.

**The pin is read from a file, not repeated in prose.** `scripts/bootstrap.sh`
reads `platform/argocd/VERSION`, rejects anything that is not a
`vMAJOR.MINOR.PATCH` tag, installs exactly that tag and then asserts that the
running `argocd-server` image matches it. This directory used to document
`v3.5.3` while the script installed from the floating `stable` branch — which
had already drifted to `v3.5.5`. Two numbers for one thing is one number too
many; the file removes the second one.

## Install / verify

```bash
kubectl config current-context            # expect kind-local-platform
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n argocd --server-side --force-conflicts \
  -f "https://raw.githubusercontent.com/argoproj/argo-cd/$(cat platform/argocd/VERSION)/manifests/install.yaml"
kubectl -n argocd rollout status statefulset/argocd-application-controller --timeout=300s
kubectl -n argocd get pods                # 7 components, all 1/1
```

`--server-side --force-conflicts` is required, not a style choice: a
client-side apply stores the whole object in the
`kubectl.kubernetes.io/last-applied-configuration` annotation, and the
`applicationsets.argoproj.io` CRD schema is larger than the 256 KiB annotation
limit — the CRD is rejected with `metadata.annotations: Too long`, the exit
code is 1, and the ApplicationSet controller never gets its CRD. Measured on a
clean kind cluster on 2026-10-20, the whole upstream manifest applies
server-side with rc=0.

Components verified running: `application-controller` (StatefulSet),
`applicationset-controller`, `dex-server`, `notifications-controller`,
`redis`, `repo-server`, `server`.

## Access (admin stays private)

The admin UI is **not** published. Reach it with a loopback-only port-forward:

```bash
kubectl -n argocd port-forward --address 127.0.0.1 svc/argocd-server 8081:443
# user: admin ; password:
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d ; echo
```

The password is never printed into evidence, never committed, and the CLI
(`argocd`) is intentionally not installed — `kubectl` is enough for a ClusterIP
server, and `--address 127.0.0.1` is required on this machine (without it the
forward binds `[::1]` and an IPv4 client gets "Empty reply from server").

## Measured footprint (2026-09-23, after L4)

| | |
|---|---|
| Kind-cluster memory with Envoy + Argo | control-plane 1.647 GiB, workers 750 / 599 MiB → **≈ 3.0 GiB of the 7.75 GiB VM** |
| Argo CD's share | roughly 0.9 GiB (upstream manifest sets no resource requests; measured, not assumed) |
| Remaining headroom | ≈ 4.75 GiB |

## Uninstall

```bash
kubectl delete -n argocd \
  -f "https://raw.githubusercontent.com/argoproj/argo-cd/$(cat platform/argocd/VERSION)/manifests/install.yaml"
kubectl delete namespace argocd
```

Applications and AppProjects live in `gitops/` (P03-owned desired state), not
here: this directory only describes how the controller is installed. The
AppProject itself is the canonical one in `platform/argocd/appproject.yaml`
(ADR-015) — the former second copy in `gitops/projects/portfolio.yaml` was
deleted on 2026-10-20.

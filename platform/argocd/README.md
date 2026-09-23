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
| Version | **v3.5.3** (`https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.3/manifests/install.yaml`) |
| Mode | **non-HA** multi-tenant bundle (evaluation/demo sizing, single replica per component) |
| Namespace | `argocd` |
| Server exposure | **ClusterIP only** (no LoadBalancer, no NodePort, not routed through Envoy Gateway) |

`stable` / `latest` / `main` are deliberately NOT used: the manifest would then
be whatever upstream happens to have that day, and a local platform whose GitOps
controller changes silently is not reproducible.

## Install / verify

```bash
kubectl config current-context            # expect kind-local-platform
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n argocd --server-side --force-conflicts \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.3/manifests/install.yaml
kubectl -n argocd rollout status statefulset/argocd-application-controller --timeout=300s
kubectl -n argocd get pods                # 7 components, all 1/1
```

`--server-side --force-conflicts` is required because the CRDs
(`applications`, `appprojects`, `applicationsets`) exceed the client-side
annotation limit.

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
kubectl delete -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.3/manifests/install.yaml
kubectl delete namespace argocd
```

Applications and AppProjects live in `gitops/` (P03-owned desired state), not
here: this directory only describes how the controller is installed.

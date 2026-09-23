# `local/kind` — LOCAL portfolio platform cluster (L2)

Status: **L2 created and verified 2026-09-23** on the Apple Silicon workstation.

This directory owns the **local** Kubernetes runtime for the portfolio, so that
interview/portfolio work does not need Azure (the Azure runtime is being torn
down — see `docs/evidence/azure-teardown/`). It is platform tooling, which is
why it lives in P03 (`AKS-SRE-Platform`), next to `kubernetes/` and `gitops/`.

| File | Purpose |
|---|---|
| `cluster.yaml` | Declarative kind config: cluster `local-platform`, 3 nodes, pinned node image |
| `create.sh` | Idempotent create/reuse + preflight (fails fast on missing tooling / Docker down) |
| `destroy.sh` | Deletes the cluster only (never touches compose volumes, backups, or Azure) |
| `load-image.sh` | Loads locally **built** images into every node (works around the verified `kind load` failure — §3c) |

```bash
./local/kind/create.sh     # create (or reuse) the cluster
./local/kind/destroy.sh    # delete it (interactive; -y to skip the prompt)
```

## 1. Preflight — measured, not assumed

| Item | Measured value (2026-09-23) |
|---|---|
| Platform | macOS 27.0, **arm64** (Apple Silicon) |
| Host RAM | 16 GiB (`hw.memsize` = 17 179 869 184 B) |
| Free disk | ~314 GiB free of 460 GiB (`/`) |
| Docker | server **29.6.1**, context `desktop-linux`, driver `overlayfs`, **8 CPUs** |
| Docker VM memory | **7.75 GiB** (`MemTotal` = 8 321 798 144 B) — *this is the binding constraint, see §4* |
| `kubectl` | client **v1.36.1** |
| `kind` | **v0.33.0** (installed via `brew install kind` on 2026-09-23) |
| `helm` | **v4.3.0** (installed via `brew install helm` on 2026-09-23) |
| `argocd` CLI | **not installed** — deliberately: Argo CD stays ClusterIP and is reached with `kubectl port-forward`, so the CLI is optional |
| `az` / `terraform` | present (used for the Azure teardown, not for this cluster) |

Node image: `kindest/node:v1.36.1`, **pinned after probing the registry**
(`v1.36.1` → available; `v1.36.0` → absent; `v1.35.1`/`v1.35.0`/`v1.34.0`/
`v1.33.1`/`v1.32.3`/`v1.31.4` → available). It aligns with the kubectl client
and with the AKS 1.36 line the app manifests target.

## 2. Topology and why

```text
kind cluster: local-platform          (context: kind-local-platform)
├── control-plane   (kindest/node:v1.36.1)
├── worker
└── worker
```

- **3 nodes, not more.** 1 control-plane + 2 workers is exactly enough for
  scheduler/affinity/PDB behaviour to be *real* (a single-node cluster hides
  scheduling bugs) while still fitting the Docker VM budget in §4. More nodes
  means more per-node overhead, and **RAM is the binding constraint here, not
  CPU** (8 CPUs available).
- **Default kindnet CNI kept.** Enough for Envoy Gateway + Argo CD +
  observability, and one fewer moving part. Consequence: **NetworkPolicy is not
  enforced locally** — a documented local limitation, never claimed as tested.
- **No MetalLB, no ingress-nginx.** ingress-nginx is retired upstream and was
  retired in this architecture too (`tasks/current.md`, Phase 7B.0);
  north-south goes through **Gateway API + Envoy Gateway**. Until L3 the proof
  path is `kubectl port-forward`; MetalLB is added only if a real LoadBalancer
  IP becomes materially useful.
- **Host port mappings are pre-wired but inert:**
  `127.0.0.1:8080 -> control-plane:30080`, `127.0.0.1:8443 -> :30443`. They cost
  nothing, are bound to loopback (never the LAN), and let L3 expose the shared
  Gateway as a NodePort **without recreating the cluster**.

Host ports already occupied by the FlashSale compose stack (avoid collisions):
`5432` (Postgres), `6379` (Redis), `5672`/`15672` (RabbitMQ), `5000` (API).
Verified free before creation: `6443`, `8080`, `8443`, `30080`, `30443`.

## 3. Reproducibility

- Cluster name, node image, API server port (6443), pod/service subnets and CNI
  mode are all explicit in `cluster.yaml` — no implicit kind defaults that drift
  between kind releases.
- `create.sh` is **idempotent**: an existing healthy `local-platform` is reused,
  never silently destroyed. Recreating is an explicit `destroy.sh` decision.
- The cluster holds only local state. Nothing here creates or reads Azure
  resources, and it never touches the Azure tfstate backend (which stays
  firewall-restricted to an IP allowlist).

## 3b. Verified state after creation (2026-09-23, live output)

| Check | Result |
|---|---|
| Nodes | `local-platform-control-plane`, `local-platform-worker`, `local-platform-worker2` — **3/3 Ready** |
| Kubernetes | server **v1.36.1**, runtime `containerd://2.3.1`, OS `Debian GNU/Linux 13 (trixie)`, `arm64` |
| System pods | **13/13 Running, 0 restarts** (etcd, kube-apiserver, kube-scheduler, kube-controller-manager, coredns ×2, kube-proxy ×3, kindnet ×3, local-path-provisioner) |
| CNI | `kindnet` DaemonSet 3/3 |
| Storage | StorageClass `standard` (`rancher.io/local-path`, `WaitForFirstConsumer`) — usable for `PVC` manifest parity |
| Idle VM usage | control-plane **606 MiB**, workers **140 / 143 MiB** → **~0.87 GiB** baseline of the 7.75 GiB VM |


## 3c. Image delivery — `kind load` is broken here (verified, and worked around)

This was found by actually running it, not assumed:

```text
$ kind load docker-image alpine:latest --name local-platform
ERROR: failed to load image: command "docker exec --privileged -i
  local-platform-worker ctr --namespace=k8s.io images import --all-platforms
  --digests --snapshotter=overlayfs -" failed with error: exit status 1
Command Output: ctr: content digest sha256:d56c3…395: not found
```

- `kind load image-archive` with a **plain** `docker save` archive fails the same
  way, so the archive's *shape* is the problem, not the load path.
- Measured root cause — `index.json` parsed inside both archives:
  - plain `docker save` → the index references a nested OCI **index**
    (`mediaType: …image.index.v1+json`, no platform), so ctr's `--all-platforms`
    resolution never finds a concrete platform manifest → `content digest …: not
    found`;
  - `docker image save --platform linux/arm64` → the index carries concrete
    `…image.manifest.v1+json` entries → `kind load image-archive` succeeds.
- `load-image.sh` therefore exports **one platform** and imports the archive
  (kind's documented workaround). It does **not** disable the containerd image
  store and does **not** call kind internals (`docker exec … ctr`), and it verifies
  presence on every node with an exact ref match (`grep -Fx`), because BSD
  sed/grep do not handle the regex escaping the first version relied on.
- Verified both ways: image present on all 3 nodes
  (`ctr -n k8s.io images ls -q`) **and** a pod with `imagePullPolicy: Never` ran
  from the loaded image.
- Alternative fixes, if the script is ever replaced: turn off the containerd
  image store in Docker Desktop, or run a local `registry:2` and push/pull.

**Architecture trap for L1 (measured):** the images pulled from the (soon to be
deleted) ACR are `amd64/linux` — `acrflashsalep6.azurecr.io/order-api` and
`order-worker` at the pinned SHA `087731cd…` — while the kind nodes and this host
are `arm64`. Locally built equivalents (`flashsale-backend-order-api:latest`,
`mcr.microsoft.com/dotnet/aspnet:10.0`, `node:22-alpine`, `postgres:15-alpine`,
`redis:7-alpine`, `rabbitmq:3-management-alpine`) are all `arm64/linux`. So L1
must **build from source for arm64** and load with `load-image.sh` — reusing the
ACR-pinned amd64 images would mean emulation and a misleading performance story.

## 4. Capacity — the real constraint

Docker Desktop's VM has **7.75 GiB** while the host has 16 GiB. The L3–L10 stack
(Envoy Gateway + Argo CD + Order API ×2 + worker + PostgreSQL + Redis +
RabbitMQ + Prometheus + Grafana) is a **budget** of roughly 3.5–4 GiB of requests
on top of the ~0.85 GiB idle baseline measured in §3b — it fits, but with little
headroom for the concurrency/oversell proof while Prometheus is scraping.

> The per-component numbers below are an **estimate to be replaced by measured
> values** at L10 (`kubectl top`, `docker stats`). None of them are presented as
> measurements yet.

| Component | Estimated additional request |
|---|---|
| Envoy Gateway (controller + data plane) | ~0.25 GiB |
| Argo CD (non-HA: server, repo-server, controller, redis) | ~0.7 GiB |
| PostgreSQL / Redis / RabbitMQ | ~0.55 GiB |
| Order API ×2 + Order Worker | ~0.6 GiB |
| Prometheus + Grafana | ~0.75 GiB |

**Raising Docker memory is a one-time manual step — it cannot be scripted.**
`~/Library/Group Containers/group.com.docker/settings-store.json` is protected by
macOS and is not readable/writable from a terminal session (verified 2026-09-23:
`plutil -p` → *"couldn't be opened because you don't have permission to view
it"*). Editing it while Docker Desktop runs would also risk clobbering the file.
`create.sh` therefore only **warns**; it never attempts the change.

To raise it: **Docker Desktop → Settings → Resources → Memory → 10 GB → Apply &
Restart**, then re-run `./local/kind/create.sh` (an existing cluster keeps
running and inherits the new limit). 10 GB — not 12 — is deliberate on a 16 GiB
host: it leaves ~6 GiB for macOS, the editor and browsers instead of driving the
machine into swap.

## 5. Not in scope here

L0–L2 deliver **the cluster only**. Everything else lands under its own phase
gate, in order: Gateway API + Envoy Gateway (L3), Argo CD + `AppProject
portfolio` (L4), `overlays/local` for P01/P02 with locally built images (L5/L7),
shared Gateway routes (L8), GitOps forward/revert proof (L9), Prometheus +
Grafana (L10), interview demo doc (L11). Application images get built locally and
loaded with `kind load docker-image` — no registry credentials involved.

**Known local limitations (do not overclaim):** no NetworkPolicy enforcement,
no LoadBalancer IP, no high availability, no cloud-managed data tier — this is a
parity environment for deployment/GitOps/observability behaviour, not a claim of
production equivalence.


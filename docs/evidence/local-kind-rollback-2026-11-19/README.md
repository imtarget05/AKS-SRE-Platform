# Local kind rollback drill — 2026-11-19

Source: `8413e972e7b2ba6c89970a3c0ec54fdee98e5812` (`main` before this evidence-only change). The test built `app/sre-demo-api` as `linux/arm64` image `sha256:a6a68d3a44fde76cfe5899eebd9dfa366481b6b9e8f7c2f6754f7c1eb091e492`, loaded it into a disposable single-node kind cluster, and ran `scripts/kind_rollback_drill.py`. Docker Server was 29.6.1; kind used `kindest/node:v1.37.0`. No Azure resource was used.

```sh
docker build --platform linux/arm64 -t sre-demo-api:local-drill app/sre-demo-api
kind create cluster --name sre-rollback --wait 120s
kind load docker-image sre-demo-api:local-drill --name sre-rollback
python3 scripts/kind_rollback_drill.py --context kind-sre-rollback \
  --image sre-demo-api:local-drill
kind delete cluster --name sre-rollback
```

The test ran at 08:34:47–08:35:01 UTC. It deployed two ready replicas, confirmed `/health/ready` returned HTTP 200, then configured a deliberately missing image. Kubernetes reported `ErrImagePull` after 9.72 seconds; the two old replicas remained ready and the HTTP probe still returned 200. `kubectl rollout undo` restored the original image and two ready replicas in **0.143 seconds** as timed by the script. This is rollback command completion in a failed rolling update, **not** a measured outage recovery time or proof of zero dropped requests under continuous load.

Evidence files: [`result.json`](result.json) has the ordered timestamps and assertions; [`pods.json`](pods.json) and [`events.txt`](events.txt) show pod state and the image pull failure; [`deployment.yaml`](deployment.yaml) records the restored deployment; [`port-forward.log`](port-forward.log) records the local probe path. The drill process exited 0. The disposable `sre-rollback` cluster was deleted and the original `aks-rg-bkpe` kubectl context restored; the existing `nt114-reuse` kind cluster was left untouched.

This proves the repository's own Node workload and Kubernetes rolling-update behavior in local kind. It does not prove an AKS deployment, Argo CD rollback, FlashSale/QuanLyKho workload behavior, or production traffic continuity. For those claims, use separate evidence at the relevant commit.

# A13 local NetworkPolicy causal probe — 2026-11-06 UTC

**Verdict:** PASS for the isolated capable-CNI test only. This does not prove Azure AKS policy enforcement or A16. Re-run on the final release SHA before counting A13 in the final portfolio score.

- Source SHA tested: `3fac87e1ad867940946a36e04d3afb3ffe71722e` (main / `codex/aks-a13-offline`).
- Environment: isolated local kind `portfolio-a13-final`, Kubernetes v1.36.1, Calico v3.33.0; `disableDefaultCNI: true`, `podSubnet: 192.168.0.0/16`.
- CNI image digest: `quay.io/calico/node@sha256:565d8db3200e443955557f8f28ff44ab8a4a456754bc74a19c4f2f3444af9b1c`.
- Raw output with UTC timestamps, pod identity, both policy revisions and teardown: [A13 probe log](2026-11-06-A13-calico-policy-3fac87e.log).
- Installation followed the Calico kind guide, using the pinned `v3.33.0` manifest.

## Reproduction

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: portfolio-a13-final
nodes:
  - role: control-plane
    image: kindest/node:v1.36.1
networking:
  disableDefaultCNI: true
  podSubnet: 192.168.0.0/16
```

```bash
kind create cluster --name portfolio-a13-final --config /tmp/portfolio-a13-final-kind.yaml --wait 180s
kubectl --context kind-portfolio-a13-final create -f https://raw.githubusercontent.com/projectcalico/calico/v3.33.0/manifests/calico.yaml
kubectl --context kind-portfolio-a13-final -n kube-system rollout status daemonset/calico-node --timeout=300s
kubectl --context kind-portfolio-a13-final wait node --all --for=condition=Ready --timeout=120s
```

Run one `curl -sS -o /dev/null -w '%{http_code}' --max-time 3 http://<target-pod-ip>/` command from the same client pod against the same target pod IP for all three stages. Both pods were Ready in namespace `a13-verification`: `nginx:1.27-alpine` labeled `app=a13-target` and `curlimages/curl:8.17.0` labeled `app=a13-client`. First use no policy, then apply a `networking.k8s.io/v1` ingress policy selecting `app=a13-target` with `ingress: []`, then replace its ingress with a rule allowing TCP/80 from `app=a13-client`. Wait six seconds after each policy change before probing. The exact applied policy YAML is in the raw log.

| Stage | Expected | Actual |
| --- | --- | --- |
| Before policy | HTTP 200 | HTTP 200, exit 0 |
| Default deny | Connection blocked | curl timeout, HTTP 000, exit 28 |
| Explicit allow | HTTP 200 | HTTP 200, exit 0 |

The cluster was deleted after collecting image digests. Local kindnet and Azure AKS remain outside this proof. **A13 is LOCAL only — not Azure.**

# Digest-pinned local release and rollback — 2026-11-21

Source baseline: `c9f5e8da524ccd5b7549cb98b00910b01a0c691c`; the drill implementation is included in this branch. This was run on macOS with Docker 29.6.1 and kind `kindest/node:v1.37.0`; no Azure resource was created.

`bash scripts/kind_digest_release_drill.sh` built the repo's `sre-demo-api`, pushed it to a disposable local registry, and obtained `localhost:5002/sre-demo-api@sha256:a60c527f84d9b7d3dd77ba7bcb60879193b2fbcf2b2d7114c2e791eec35ba97b`. The script deployed that immutable reference to a disposable kind cluster, then ran the bad-image rollback drill. Both ready pods reported that same digest in `imageID`. After the deliberate `ErrImagePull`, the Deployment restored the exact digest reference, 2/2 replicas were ready, and the HTTP readiness probe returned 200. The recorded rollback command completed in 0.105 seconds; this is not an outage recovery time.

The [result](result.json), [pod states](pods.json), [restored Deployment](deployment.yaml), and [events](events.txt) are the raw evidence. The script deleted its cluster and registry and restored the previous kubectl context. The GitHub Actions kind rollback workflow now invokes the same digest-pinned path; its own run must pass before making a CI claim.

This proves local build → registry digest → Deployment image → running pod digest → rollback for the repo's demo workload. It does not prove Azure ACR promotion or AKS application deployment. `aks-deploy.yml` still applies infrastructure and does not consume the separate SBOM job's image digest.

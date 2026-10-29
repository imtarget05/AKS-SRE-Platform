# Image Sign & Digest-Pin Policy (P2.9)

## Rule

An image may be deployed to the `overlays/prod` overlay **only if** it is:

1. **Digest-pinned**: referenced as `registry/image@sha256:<digest>`, never a
   mutable tag (`:latest`, `:0.1.0`, `:main`, …).
2. **Signed**: the container image has a valid signature/provenance attestation
   produced by the release (supply-chain) pipeline (SBOM + Trivy CRITICAL scan
   + cosign/signing key), verified before the digest is written to the overlay.

Mutable tags are prohibited in `overlays/prod` because a mutable tag makes a
rollout unreproducible and defeats drift detection (see
`deploy/base/deployment.yaml:66-69`).

## Enforcement

- `deploy/overlays/prod/kustomization.yaml` carries an `images:` digest pin for
  `sre-demo-api`. The placeholder digest
  `sha256:0000000000000000000000000000000000000000000000000000000000000000`
  MUST be replaced by the CI release pipeline with the signed, published digest
  before any prod apply.
- `scripts/gitops-pin-overlay.py` pins cross-repo Application `targetRevision`
  to immutable SHAs (P2.7), so the GitOps source ref and the image digest are
  both immutable at release time.
- `terraform/modules/acr_attachment/` provisions the `AcrPull` role assignment
  so the AKS kubelet identity can pull the private ACR image by digest.

## Release pipeline (summary)

1. Build & push image to ACR.
2. Generate SBOM; Trivy scan (no CRITICAL).
3. Sign image + produce provenance attestation.
4. Record the published `sha256:<digest>`.
5. CI substitutes the digest into `deploy/overlays/prod/kustomization.yaml`
   (replacing the placeholder) and opens the prod promotion PR.
6. Argo CD syncs the pinned Application revision; AKS pulls `image@sha256:<digest>`.

## Evidence

- `docs/evidence/transient-aks-run-PASS.md` — live private ACR pull by immutable
  digest (`acrportfoliodev01.azurecr.io/sre-demo-api@sha256:…`).
- `docs/runbooks/production-release-governance.md` — `sbom-scan` + `release-push`
  release gates with digest verification.

## Caveat

`terraform`, `kubectl`, `kustomize` and an Azure subscription are not available
in this environment, so `terraform validate` and a live prod apply were not
run. The placeholder digest must be replaced with a real signed digest before
prod deployment.

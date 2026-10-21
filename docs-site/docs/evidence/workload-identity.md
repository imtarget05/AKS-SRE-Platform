# Workload Identity and private image pull — historical proof

The Phase 7A run proved two **different** credential paths on real AKS:

1. A proof pod's Kubernetes ServiceAccount token was exchanged through an
   Entra federated credential for a scoped Azure `Reader` operation.
2. The **kubelet managed identity** pulled a private ACR image by digest
   without an `imagePullSecret`.

The pod did not use its Workload Identity to pull the image. The run did not
prove that all workloads use federation, nor that an application pod read a
Key Vault secret. The temporary proof identity, pool and AKS cluster were
deleted after validation.

| Claim | Primary evidence |
|---|---|
| Federated token exchange and scoped read | [Workload Identity runtime report](https://github.com/imtarget05/AKS-SRE-Platform/blob/main/docs/evidence/phase7a/workload-identity-runtime-PASS.md) |
| Kubelet ACR pull by digest, no pull secret | [Private ACR pull report](https://github.com/imtarget05/AKS-SRE-Platform/blob/main/docs/evidence/phase7a/private-acr-pull-PASS.md) |

The demo uses saved, sanitized evidence. Do not run an old `kubectl` command
against an unspecified context: the Azure cluster in that report no longer
exists, and the active local context may be kind.

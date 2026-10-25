# Senior Engineering Portfolio archive

This directory preserves the material unique to `Senior-Engineering-Portfolio`
at commit `86db556` (2026-10-25). It is historical reference material, not an
active deployment or a current verification result. Its `README.md`,
`STATUS.md`, `PHASES.md`, plans, and evidence describe the former monorepo
layout and may refer to repositories or CI runs that have since changed.

The active source of truth is split across three working repositories:

- `AKS-SRE-Platform`: shared platform and the current Agent Hub implementation
  in `apps/agent-hub`.
- `QuanLyKho`: warehouse and simulated financial operations.
- `OpsBridge`: flash-sale order platform.

The former monorepo's copies of those three codebases were omitted here. At
the archive commit, the copies of OpsBridge and QuanLyKho had no files absent
from their primary repositories. The AKS copy had three extra legacy workload
manifests, which remain recoverable from the original monorepo Git history.

`services/retail-finance` is retained here as a historical standalone service.
It is not part of the QuanLyKho product or its release pipeline. The former
monorepo's Agent Hub copy is also historical; use `apps/agent-hub` for active
work.

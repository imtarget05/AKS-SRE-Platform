# Incidents and Postmortems

This directory holds incident postmortems, root-cause analyses (RCAs), and resolution records for platform operations, adhering to the monorepo conventions in [AGENTS.md](../../AGENTS.md) ("failures get a postmortem in `docs/incidents/`").

## Historical Blocked Operations & Evidence

Detailed evidence records for historical blocked operations and gates are documented in `docs/evidence/`:

- [Phase 7A Apply Blocked (2026-09-21)](../evidence/phase7a/apply-2026-09-21-BLOCKED.md)
  - **Issue**: Provisioning blocked by regional quota failure on `standardDASv5Family` (requested 8, remaining 0 in `eastasia`) and transient 403 on state storage account firewall due to residential IP rotation.
  - **Remediation**: Evaluated quota limits across SKU families, updated storage account firewall allowlist, and switched to supported `StandardDsv6Family`.

- [Phase 7B.0 Quota Gate Blocked (2026-09-21)](../evidence/phase7b/quota-7b0-gate.md)
  - **Issue**: Automated quota increase via `az quota update` failed (`ContactSupport` / request failed) when attempting 10 → 16 vCPUs for `StandardDsv6Family` and total regional `cores`.
  - **Status**: Platform gate stopped provisioning 7B.1 user node pool until quota increase is manually approved via Azure Portal.

## Incident Postmortem Standard Format

When recording a postmortem, use the following structure:
1. **Summary & Timeline**: Start time, detection time, mitigation time, total duration.
2. **Impact**: Workloads affected, deployment blockage, financial or SLO impact.
3. **Root Cause**: Deep technical analysis (5 Whys).
4. **Remediation & Recovery**: Immediate fixes and actions taken to restore state.
5. **Action Items & Preventive Measures**: IaC guards, policy updates, alert additions.

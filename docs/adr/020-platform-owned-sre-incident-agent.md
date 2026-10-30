# ADR 020: Platform-Owned Read-Only SRE Incident Agent

## Status
Accepted

## Context
The AKS-SRE-Platform repository owns the observability stack (Prometheus,
Alertmanager), GitOps revisions (Argo CD AppProjects), and SRE runbooks. When an
alert fires, platform SRE needs a deterministic, read-only incident triage and
briefing workflow that consumes these platform artifacts without mutating cluster
state.

`apps/agent-hub` is an experimental, opt-in Agent Hub (ADR-019) and is NOT a
required dependency of the platform or any workload. Placing the SRE incident
agent inside `apps/agent-hub` would couple platform incident response to an
experimental cross-domain tool, violate the platform/workload boundary defined in
ADR-019, and introduce write-capable agent tooling (LLM, shell, credentials)
into the hot path.

## Decision
1. The SRE incident workflow (Alert Triage -> Diagnostics -> Incident Critic/Brief)
   is a platform-owned read-only automation workload in this repository
   (AKS-SRE-Platform), implemented under `app/sre_incident_agent/`.
2. It is independent of the cross-domain `apps/agent-hub`; agent-hub is not a
   dependency and is not required for the incident workflow to operate.
3. The agent is read-only: no kubectl write (apply/scale/delete/rollout/patch/
   create), no Argo CD sync/rollback, no Terraform, and no secret access.
4. The agent holds no write credential and has no shell command execution path.
5. The agent consumes platform artifacts read-only: Prometheus rules/alerts and
   Alertmanager active alerts via kubectl proxy, `kubectl get` workload status,
   Argo CD application revision/image digest, and runbook markdown from
   `docs/runbooks/`.
6. Operation is feature-flag gated (`SRE_INCIDENT_AGENT_ENABLED`) and offline by
   default: deterministic code only, no LLM calls, no API keys, no network.

## Rationale
- The platform repository already owns observability, GitOps revisions, and
  runbooks; the SRE agent is a consumer of these read-only artifacts.
- Keeping the agent in the platform repo (not agent-hub) preserves the
  Platform-as-Product vs Workloads boundary defined in ADR-019.
- Read-only by design eliminates blast radius during incident response.

## Consequences
Positive:
- Incident response can triage and brief without risking cluster mutation.
- Independent of agent-hub; works whether or not agent-hub is installed.
- Offline default: deterministic, auditable, no secret surface.
Negative:
- No automated remediation (rollback/scale) by design; remediation remains a
  separate, human-gated, change-controlled operation.
- Dependent on kubectl proxy and cluster availability for live evidence.

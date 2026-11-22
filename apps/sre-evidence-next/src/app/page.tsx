import React from 'react';
import Link from 'next/link';
import { MetricCard } from '../components/MetricCard';
import { StatusBadge } from '../components/StatusBadge';
import {
  getCalculatedSloSummary,
  getRollbackSummary,
  getDigestVerificationSummary,
} from '../lib/evidence';

export default function HomePage() {
  const slo = getCalculatedSloSummary();
  const rollback = getRollbackSummary();
  const digest = getDigestVerificationSummary();

  return (
    <div className="space-y-10">
      {/* Header section */}
      <div className="space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-950/50 border border-blue-800/50 text-blue-400 text-xs font-mono">
          <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
          Production-Grade SRE Platform Verification
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-100">
          Reliability & Evidence Dashboard
        </h1>
        <p className="text-slate-400 max-w-3xl text-sm sm:text-base leading-relaxed">
          Comprehensive, auditable evidence collected from live Kubernetes drills,
          Prometheus TSDB telemetry, and fail-closed GitOps validation gates across
          the AKS SRE Platform.
        </p>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        <MetricCard
          title="Availability (30-Day)"
          value={`${slo.calculatedAvailabilityPct}%`}
          unit="SLI"
          subtitle={`Over ${slo.totalRequests.toLocaleString()} requests, 0 5xx errors`}
          badge={{ text: 'PASS', variant: 'success' }}
          note="Baseline from docs/evidence/2026-10-26/slo-baseline-2026-10-26.json"
        />

        <MetricCard
          title="Baseline p95 Latency"
          value={slo.opsbridgeP95LatencyMs}
          unit="ms"
          subtitle="Target < 500ms (OpsBridge probe)"
          badge={{ text: 'PASS', variant: 'success' }}
          note="BankOps API ready probe p95: 15.21ms"
        />

        <MetricCard
          title="Rollback Drill Exec"
          value={`${rollback.commandDurationSeconds}s`}
          unit="duration"
          subtitle="2/2 ready replicas sustained"
          badge={{ text: 'ZERO DOWNTIME', variant: 'info' }}
          isBoundary={true}
          note="Technical Boundary: Rollback command duration, NOT system MTTR."
        />

        <MetricCard
          title="Image Immutability"
          value="SHA256"
          unit="digest pinned"
          subtitle="GitOps fail-closed gating"
          badge={{ text: 'ENFORCED', variant: 'success' }}
          note="validate-gitops.py precedes release drill"
        />
      </div>

      {/* Deep-Dive Links */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold tracking-tight text-slate-200">
          Core Audit Areas
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Link
            href="/digest"
            className="group block p-6 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-blue-600/60 hover:bg-slate-900/90 transition-all duration-200"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-mono text-blue-400 bg-blue-950/80 px-2 py-0.5 rounded border border-blue-800/40">
                /digest
              </span>
              <StatusBadge status="Immutable" variant="success" />
            </div>
            <h3 className="text-base font-bold text-slate-100 group-hover:text-blue-400 transition-colors">
              Image Digest & GitOps Gating
            </h3>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Fail-closed release drill verifying sha256 pinned container runtime digests
              and pre-deployment semantic validation of ArgoCD AppProjects.
            </p>
          </Link>

          <Link
            href="/slo"
            className="group block p-6 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-blue-600/60 hover:bg-slate-900/90 transition-all duration-200"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-mono text-blue-400 bg-blue-950/80 px-2 py-0.5 rounded border border-blue-800/40">
                /slo
              </span>
              <StatusBadge status="100.0% Avail" variant="success" />
            </div>
            <h3 className="text-base font-bold text-slate-100 group-hover:text-blue-400 transition-colors">
              30-Day Baseline SLO Dashboard
            </h3>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Empirical HTTP SLI baseline measurements (availability, latency percentiles,
              error budgets) across OpsBridge and BankOps services.
            </p>
          </Link>

          <Link
            href="/rollback"
            className="group block p-6 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-blue-600/60 hover:bg-slate-900/90 transition-all duration-200"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-mono text-blue-400 bg-blue-950/80 px-2 py-0.5 rounded border border-blue-800/40">
                /rollback
              </span>
              <StatusBadge status="2/2 Ready" variant="info" />
            </div>
            <h3 className="text-base font-bold text-slate-100 group-hover:text-blue-400 transition-colors">
              Zero-Downtime Rollback Drill
            </h3>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Step-by-step Kind drill timeline proving 2/2 replica availability during bad
              image fault, with explicit technical boundary definitions.
            </p>
          </Link>
        </div>
      </div>

      {/* Real Evidence Artifacts Inventory */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 space-y-4">
        <h2 className="text-lg font-bold text-slate-200">
          Auditable Evidence Sources
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="pb-3 font-semibold">Evidence Artifact</th>
                <th className="pb-3 font-semibold">Source Path</th>
                <th className="pb-3 font-semibold">Verified Measurement</th>
                <th className="pb-3 font-semibold text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              <tr>
                <td className="py-3 font-medium text-slate-200">SLO Baseline Capture</td>
                <td className="py-3 text-slate-400">docs/evidence/2026-10-26/slo-baseline-2026-10-26.json</td>
                <td className="py-3">14,424 total requests, 0 5xx, p95 54.55ms</td>
                <td className="py-3 text-right"><StatusBadge status="PASS" variant="success" /></td>
              </tr>
              <tr>
                <td className="py-3 font-medium text-slate-200">Zero-Downtime Rollback Result</td>
                <td className="py-3 text-slate-400">demo-results/kind-rollback/result.json</td>
                <td className="py-3">2/2 ready replicas, 5.12s command duration</td>
                <td className="py-3 text-right"><StatusBadge status="PASS" variant="success" /></td>
              </tr>
              <tr>
                <td className="py-3 font-medium text-slate-200">Image Digest Immutability</td>
                <td className="py-3 text-slate-400">docs/evidence/local-kind-digest-2026-11-21/result.json</td>
                <td className="py-3">sha256:a60c527f84... pinned runtime ID</td>
                <td className="py-3 text-right"><StatusBadge status="PASS" variant="success" /></td>
              </tr>
              <tr>
                <td className="py-3 font-medium text-slate-200">GitOps Fail-Closed Gating</td>
                <td className="py-3 text-slate-400">gitops/validate-gitops.py</td>
                <td className="py-3">Semantic allowlist & canonical dir validation</td>
                <td className="py-3 text-right"><StatusBadge status="PASS" variant="success" /></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

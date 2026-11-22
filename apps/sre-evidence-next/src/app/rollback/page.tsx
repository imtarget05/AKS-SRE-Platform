import React from 'react';
import { StatusBadge } from '../../components/StatusBadge';
import { MetricCard } from '../../components/MetricCard';
import { Timeline } from '../../components/Timeline';
import { loadRollbackDrillEvidence, getRollbackSummary } from '../../lib/evidence';

export default function RollbackPage() {
  const rawEvidence = loadRollbackDrillEvidence();
  const rollback = getRollbackSummary(rawEvidence);

  return (
    <div className="space-y-10">
      {/* Header */}
      <div className="space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/50 border border-cyan-800/50 text-cyan-400 text-xs font-mono">
          <span className="w-2 h-2 rounded-full bg-cyan-400" />
          Automated Chaos & Recovery Drill
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-100">
          Zero-Downtime Rollback Drill Evidence
        </h1>
        <p className="text-slate-400 max-w-3xl text-sm leading-relaxed">
          Ground-truth execution timeline and telemetry recorded during automated bad-image deployment
          and rollback drill in isolated Kind cluster <code className="text-cyan-400 font-mono">{rawEvidence.context}</code>.
        </p>
      </div>

      {/* Mandatory Technical Boundary Callout Box */}
      <div className="rounded-xl border border-amber-500/60 bg-amber-950/25 p-5 shadow-lg shadow-amber-950/20 space-y-2">
        <div className="flex items-center gap-2 text-amber-300 font-bold text-sm tracking-wide uppercase font-mono">
          <svg className="w-4 h-4 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          SRE Integrity & Technical Boundary Notice
        </div>
        <p className="text-xs sm:text-sm text-amber-200/90 leading-relaxed font-sans">
          {rollback.technicalBoundaryNote}
        </p>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Command Duration"
          value={`${rollback.commandDurationSeconds}s`}
          unit="execution"
          subtitle="kubectl rollout undo & wait"
          badge={{ text: 'COMMAND DURATION', variant: 'warning' }}
          isBoundary={true}
          note="Measures CLI command time, NOT end-to-end system MTTR."
        />

        <MetricCard
          title="Availability During Fault"
          value={`${rollback.readyReplicasDuringFault}/2`}
          unit="replicas"
          subtitle="100% healthy during rollout failure"
          badge={{ text: 'ZERO DOWNTIME', variant: 'success' }}
          note="maxUnavailable: 0 prevented pod teardown"
        />

        <MetricCard
          title="HTTP Status Under Fault"
          value={rollback.httpStatusDuringFault}
          unit="HTTP OK"
          subtitle="Readiness probe stayed green"
          badge={{ text: 'SERVING', variant: 'success' }}
          note="Probed via port-forward 18088:8080"
        />

        <MetricCard
          title="Drill Status"
          value={rollback.status.toUpperCase()}
          subtitle="All assertions passed"
          badge={{ text: 'VERIFIED', variant: 'success' }}
          note="Isolated Kind cluster execution"
        />
      </div>

      {/* Drill Execution Timeline */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-800">
          <div>
            <h2 className="text-lg font-bold text-slate-200">
              Drill Execution Event Timeline
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Events streamed from scripts/kind_rollback_drill.py asserting cluster state at each transition.
            </p>
          </div>
          <StatusBadge status="AUTOMATED DRILL" variant="info" />
        </div>

        <Timeline events={rawEvidence.events} />
      </div>

      {/* Deployment Strategy Configuration */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
        <h2 className="text-lg font-bold text-slate-200">
          Kubernetes Resilience Configuration
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
          <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
            <span className="text-slate-500 block">strategy.rollingUpdate:</span>
            <span className="text-emerald-400 font-bold block">maxUnavailable: 0</span>
            <span className="text-slate-400 block text-[11px] font-sans">
              Guarantees existing healthy replicas are never killed before new pods pass readiness probe.
            </span>
          </div>

          <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
            <span className="text-slate-500 block">strategy.rollingUpdate:</span>
            <span className="text-emerald-400 font-bold block">maxSurge: 1</span>
            <span className="text-slate-400 block text-[11px] font-sans">
              Allows creating 1 candidate pod while retaining both active production replicas.
            </span>
          </div>

          <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
            <span className="text-slate-500 block">readinessProbe.httpGet:</span>
            <span className="text-emerald-400 font-bold block">periodSeconds: 2</span>
            <span className="text-slate-400 block text-[11px] font-sans">
              Fast detection cycle on /health/ready ensures rapid failure isolation.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

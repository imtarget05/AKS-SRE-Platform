import React from 'react';
import { StatusBadge } from '../../components/StatusBadge';
import { MetricCard } from '../../components/MetricCard';
import { getDigestVerificationSummary } from '../../lib/evidence';

export default function DigestPage() {
  const digest = getDigestVerificationSummary();

  return (
    <div className="space-y-10">
      {/* Header */}
      <div className="space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-950/50 border border-emerald-800/50 text-emerald-400 text-xs font-mono">
          <span className="w-2 h-2 rounded-full bg-emerald-400" />
          Container Immutability & Supply Chain Gate
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-100">
          Image Digest Immutability & GitOps Gating
        </h1>
        <p className="text-slate-400 max-w-3xl text-sm leading-relaxed">
          Demonstration of cryptographic container image pinning and fail-closed GitOps
          semantic validation gates preventing configuration drift, untracked mutations,
          and supply chain tampering.
        </p>
      </div>

      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MetricCard
          title="Verified Digest"
          value="sha256:a60c527..."
          subtitle="Cryptographically verified in container runtime"
          badge={{ text: 'VERIFIED', variant: 'success' }}
          note="Asserted by assert_ready_pods_use_digest()"
        />

        <MetricCard
          title="GitOps Gating"
          value="Fail-Closed"
          subtitle="validate-gitops.py pre-deployment check"
          badge={{ text: 'ENFORCED', variant: 'success' }}
          note="Blocks non-canonical projects and wildcard repos"
        />

        <MetricCard
          title="Tag Strategy"
          value="Immutable"
          subtitle="Strict SHA256 digest pinning required"
          badge={{ text: 'NO MUTABLE TAGS', variant: 'info' }}
          note="Mutable tags like :latest fail the release drill"
        />
      </div>

      {/* Verified SHA256 Digest Details */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-800">
          <div>
            <h2 className="text-lg font-bold text-slate-200">
              Verified Runtime SHA256 Digest
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Extracted via Docker image inspect and validated directly from pod container statuses.
            </p>
          </div>
          <StatusBadge status="PULL-BY-DIGEST" variant="success" />
        </div>

        <div className="space-y-3 font-mono text-xs">
          <div>
            <span className="text-slate-500 block mb-1">Full Pinned Image Reference:</span>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-emerald-400 break-all select-all">
              {digest.fullImageRef}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            <div>
              <span className="text-slate-500 block mb-1">Extracted SHA256 Digest:</span>
              <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 text-slate-300 break-all">
                {digest.verifiedSha256Digest}
              </div>
            </div>
            <div>
              <span className="text-slate-500 block mb-1">Container Runtime Verification:</span>
              <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 text-slate-300">
                containerStatuses[].imageID endsWith(@{digest.verifiedSha256Digest.slice(0, 16)}...)
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* CI/CD Fail-Closed Gating Pipeline */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 space-y-6">
        <div>
          <h2 className="text-lg font-bold text-slate-200">
            GitOps Fail-Closed Gating Sequence
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            As defined in <code className="text-cyan-400">.github/workflows/kind-rollback-drill.yml</code>,
            <code className="text-cyan-400"> gitops/validate-gitops.py</code> strictly precedes any deployment or drill execution.
          </p>
        </div>

        <div className="space-y-4">
          {digest.gatingSequence.map((step, idx) => (
            <div
              key={idx}
              className="flex items-start gap-4 p-4 rounded-lg bg-slate-950/70 border border-slate-800/80 text-xs"
            >
              <div className="w-6 h-6 rounded-full bg-blue-900/60 text-blue-400 flex items-center justify-center font-mono font-bold flex-shrink-0 border border-blue-700/50">
                {idx + 1}
              </div>
              <div className="flex-1 font-mono text-slate-300 leading-relaxed">
                {step}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Immutability vs Mutability Comparison */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
        <h2 className="text-lg font-bold text-slate-200">
          Why Digest Immutability Matters in SRE
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
          <div className="p-4 rounded-lg bg-rose-950/20 border border-rose-900/40 space-y-2">
            <div className="flex items-center justify-between text-rose-400 font-bold font-mono">
              <span>Mutable Tags (:latest, :v1)</span>
              <StatusBadge status="FORBIDDEN" variant="danger" />
            </div>
            <ul className="list-disc list-inside text-slate-300 space-y-1 leading-relaxed">
              <li>Tags can be overwritten in registry without audit trail.</li>
              <li>Different nodes in the cluster may pull different underlying image layers.</li>
              <li>Rollbacks cannot guarantee byte-for-byte exact restored binary state.</li>
              <li>Vulnerable to upstream supply chain registry poisoning.</li>
            </ul>
          </div>

          <div className="p-4 rounded-lg bg-emerald-950/20 border border-emerald-900/40 space-y-2">
            <div className="flex items-center justify-between text-emerald-400 font-bold font-mono">
              <span>Pinned SHA256 Digest (@sha256:...)</span>
              <StatusBadge status="STANDARD" variant="success" />
            </div>
            <ul className="list-disc list-inside text-slate-300 space-y-1 leading-relaxed">
              <li>Cryptographic content-addressable hash guaranteed by container runtime.</li>
              <li>Every replica runs 100% bit-for-bit identical compiled binary.</li>
              <li>Rollback restore is mathematically deterministic across all nodes.</li>
              <li>GitOps validation fails closed before deployment if digest is missing.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

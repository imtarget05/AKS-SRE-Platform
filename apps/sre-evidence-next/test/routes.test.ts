import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  findRepoRoot,
  loadSloBaselineEvidence,
  getCalculatedSloSummary,
  loadRollbackDrillEvidence,
  getRollbackSummary,
  getDigestVerificationSummary,
} from '../src/lib/evidence';
import HomePage from '../src/app/page';
import DigestPage from '../src/app/digest/page';
import SloPage from '../src/app/slo/page';
import RollbackPage from '../src/app/rollback/page';

describe('SRE Evidence Next.js Application Route & Logic Tests', () => {
  const repoRoot = findRepoRoot();

  describe('1. SLO Baseline Telemetry & Calculations (/slo)', () => {
    it('should successfully load raw SLO baseline evidence JSON', () => {
      const evidence = loadSloBaselineEvidence();
      expect(evidence).toBeDefined();
      expect(evidence.schema_version).toBe(1);
      expect(evidence.cluster_context).toBe('aks-portfolio-dev');
      expect(evidence.services['opsbridge-api']).toBeDefined();
      expect(evidence.services['bankops-api']).toBeDefined();
    });

    it('should compute exact genuine SLO metrics from evidence', () => {
      const summary = getCalculatedSloSummary();
      
      // Total requests = 14418 (2xx) + 6 (4xx) + 0 (5xx) = 14424
      expect(summary.totalRequests).toBe(14424);
      expect(summary.success2xxCount).toBe(14418);
      expect(summary.client4xxCount).toBe(6);
      expect(summary.server5xxCount).toBe(0);

      // Availability = 100.0%
      expect(summary.calculatedAvailabilityPct).toBe(100.0);
      expect(summary.errorRate5xxPct).toBe(0.0);

      // Latencies
      expect(summary.opsbridgeP95LatencyMs).toBe(54.55);
      expect(summary.bankopsP95LatencyMs).toBe(15.21);

      // Overall SLO verdict
      expect(summary.sloComplianceStatus).toBe('PASS');
    });

    it('should render SloPage component without throwing', () => {
      const element = SloPage();
      expect(element).toBeDefined();
      expect(element.type).toBe('div');
    });
  });

  describe('2. Zero-Downtime Rollback Drill & Technical Boundary (/rollback)', () => {
    it('should load rollback drill evidence JSON from demo-results/kind-rollback/result.json', () => {
      const drill = loadRollbackDrillEvidence();
      expect(drill).toBeDefined();
      expect(drill.scope).toBe('isolated_kind_repo_workload');
      expect(drill.context).toBe('kind-sre-rollback');
      expect(drill.status).toBe('passed');
      expect(drill.events.length).toBeGreaterThanOrEqual(5);
    });

    it('should assert 2/2 ready replicas during deployment fault and command duration 5.12s', () => {
      const summary = getRollbackSummary();
      
      // Zero downtime sustained during bad image rollout
      expect(summary.readyReplicasDuringFault).toBe(2);
      expect(summary.httpStatusDuringFault).toBe(200);

      // Command duration 5.12 seconds
      expect(summary.commandDurationSeconds).toBe(5.12);
      expect(summary.status).toBe('passed');
      expect(summary.restoredReplicas).toBe(2);
    });

    it('should explicitly enforce technical boundary: command duration is NOT system MTTR', () => {
      const summary = getRollbackSummary();
      
      expect(summary.technicalBoundaryNote).toContain('Technical Boundary');
      expect(summary.technicalBoundaryNote).toContain('measures rollback execution time');
      expect(summary.technicalBoundaryNote).toContain('NOT system MTTR');
      expect(summary.technicalBoundaryNote).toContain('maxUnavailable: 0');
    });

    it('should render RollbackPage component without throwing', () => {
      const element = RollbackPage();
      expect(element).toBeDefined();
      expect(element.type).toBe('div');
    });
  });

  describe('3. Image Digest Immutability & GitOps Gating (/digest)', () => {
    it('should verify sha256 pinned digest and GitOps gating script references', () => {
      const summary = getDigestVerificationSummary();

      expect(summary.verifiedSha256Digest).toBe(
        'sha256:a60c527f84d9b7d3dd77ba7bcb60879193b2fbcf2b2d7114c2e791eec35ba97b'
      );
      expect(summary.fullImageRef).toContain(summary.verifiedSha256Digest);
      expect(summary.gitopsGateScript).toBe('gitops/validate-gitops.py');
      expect(summary.releaseDrillScript).toBe('scripts/kind_digest_release_drill.sh');
      expect(summary.workflowGatingEnforced).toBe(true);
      expect(summary.runtimeDigestMatchAsserted).toBe(true);
      expect(summary.gatingSequence.length).toBe(6);
    });

    it('should render DigestPage component without throwing', () => {
      const element = DigestPage();
      expect(element).toBeDefined();
      expect(element.type).toBe('div');
    });
  });

  describe('4. Home Overview Route (/)', () => {
    it('should render HomePage component with overview cards without throwing', () => {
      const element = HomePage();
      expect(element).toBeDefined();
      expect(element.type).toBe('div');
    });
  });

  describe('5. Cloudflare Workers Preview & Modern Assets Configuration', () => {
    it('should have wrangler.toml configured with modern static assets and nodejs_compat', () => {
      const wranglerPath = path.join(__dirname, '../wrangler.toml');
      expect(fs.existsSync(wranglerPath)).toBe(true);

      const content = fs.readFileSync(wranglerPath, 'utf-8');
      expect(content).toContain('name = "sre-evidence-next"');
      expect(content).toContain('compatibility_flags = ["nodejs_compat"]');
      expect(content).toMatch(/assets\s*=\s*\{\s*directory\s*=\s*"\.\/out"\s*\}/);
      
      // STRICT CONSTRAINT: Do NOT use deprecated @cloudflare/next-on-pages
      expect(content).not.toContain('next-on-pages');
    });

    it('should have next.config.mjs configured for static export', () => {
      const nextConfigPath = path.join(__dirname, '../next.config.mjs');
      expect(fs.existsSync(nextConfigPath)).toBe(true);

      const content = fs.readFileSync(nextConfigPath, 'utf-8');
      expect(content).toContain("output: 'export'");
      expect(content).toContain('unoptimized: true');
    });

    it('should not declare deprecated @cloudflare/next-on-pages in package.json', () => {
      const pkgPath = path.join(__dirname, '../package.json');
      const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf-8'));

      expect(pkg.dependencies?.['@cloudflare/next-on-pages']).toBeUndefined();
      expect(pkg.devDependencies?.['@cloudflare/next-on-pages']).toBeUndefined();
    });
  });
});

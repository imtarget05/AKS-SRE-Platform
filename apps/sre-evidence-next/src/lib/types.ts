export interface SloBaselineEvidence {
  schema_version: number;
  purpose: string;
  observation_start_utc: string;
  collected_at_utc: string;
  cluster_context: string;
  data_sources: Record<string, any>;
  sli_definitions_applied: {
    availability: string;
    error_rate: string;
    latency_p95: string;
  };
  services: {
    'opsbridge-api': {
      namespace: string;
      endpoint_probed: string;
      app_image_digest: string;
      registry_image: string;
      in_cluster_probe: {
        n: number;
        status_codes: Record<string, number>;
        availability_pct: number;
        error_rate_pct: number;
        latency_ms: {
          min: number;
          p50: number;
          p90: number;
          p95: number;
          p99: number;
          max: number;
        };
      };
      prometheus_mock_server_side: {
        window: string;
        counters: {
          '2xx': number;
          '4xx': number;
          '5xx': number;
        };
        availability_pct: number;
        error_rate_5xx_pct: number;
        requests_per_second: number;
        p95_seconds: number;
        p99_seconds: number;
        within_500ms_fraction_le_0_512: number;
        note: string;
      };
    };
    'bankops-api': {
      namespace: string;
      endpoint_probed: string;
      app_image_digest: string;
      registry_image: string;
      in_cluster_probe: {
        live: {
          n: number;
          status_codes: Record<string, number>;
          availability_pct: number;
          error_rate_pct: number;
          latency_ms: Record<string, number>;
        };
        ready: {
          n: number;
          status_codes: Record<string, number>;
          availability_pct: number;
          error_rate_pct: number;
          latency_ms: Record<string, number>;
        };
      };
      prometheus_mock_server_side: {
        status: string;
        reason: string;
      };
    };
    'sre-demo-api': {
      status: string;
    };
  };
  proposed_thresholds_from_docs_slo_md: Record<string, string>;
  baseline_vs_proposed: Record<string, string>;
  known_findings: Array<{
    finding: string;
    impact: string;
  }>;
  evidence_files: string[];
}

export interface RollbackEvent {
  name: string;
  timestamp_utc: string;
  ready_replicas?: number;
  http_status?: number;
  pod?: string;
  reason?: string;
  duration_seconds?: number;
  image?: string;
  runtime_image_ids?: string[];
}

export interface RollbackDrillEvidence {
  scope: string;
  context: string;
  good_image: string;
  bad_image: string;
  started_utc: string;
  events: RollbackEvent[];
  status: string;
  finished_utc: string;
}

export interface CalculatedSloSummary {
  totalRequests: number;
  success2xxCount: number;
  client4xxCount: number;
  server5xxCount: number;
  calculatedAvailabilityPct: number;
  opsbridgeP95LatencyMs: number;
  bankopsP95LatencyMs: number;
  errorRate5xxPct: number;
  sloComplianceStatus: 'PASS' | 'FAIL';
  observationWindow: string;
  clusterContext: string;
}

export interface RollbackSummary {
  commandDurationSeconds: number;
  readyReplicasDuringFault: number;
  httpStatusDuringFault: number;
  restoredImage: string;
  restoredReplicas: number;
  status: string;
  technicalBoundaryNote: string;
}

export interface DigestVerificationSummary {
  verifiedSha256Digest: string;
  fullImageRef: string;
  gitopsGateScript: string;
  releaseDrillScript: string;
  workflowGatingEnforced: boolean;
  runtimeDigestMatchAsserted: boolean;
  failClosedRulesCount: number;
  gatingSequence: string[];
}

/**
 * OpenTelemetry bootstrap.
 *
 * Exporter selection is env-driven so the SAME image works in both profiles
 * (ADR-014): OTLP to the in-cluster collector in the Azure profile, or to a
 * local collector in the OSS profile, or disabled entirely in unit tests.
 * Traces must never be a hard startup dependency — a collector outage should
 * degrade observability, not take the workload down.
 */
import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-http';
import { PeriodicExportingMetricReader } from '@opentelemetry/sdk-metrics';
import { diag, DiagConsoleLogger, DiagLogLevel } from '@opentelemetry/api';
import { Registry, Counter, Gauge, Histogram } from 'prom-client';

const enabled = process.env.OTEL_ENABLED !== 'false';

let sdk = null;

if (enabled) {
  if (process.env.OTEL_LOG_LEVEL === 'debug') {
    diag.setLogger(new DiagConsoleLogger(), DiagLogLevel.DEBUG);
  }
  const endpoint = process.env.OTEL_EXPORTER_OTLP_ENDPOINT;

  sdk = new NodeSDK({
    serviceName: process.env.OTEL_SERVICE_NAME ?? 'sre-demo-api',
    serviceVersion: process.env.APP_VERSION ?? 'dev',
    traceExporter: endpoint ? new OTLPTraceExporter({ url: `${endpoint}/v1/traces` }) : undefined,
    metricReader: endpoint
      ? new PeriodicExportingMetricReader({
          exporter: new OTLPMetricExporter({ url: `${endpoint}/v1/metrics` }),
          exportIntervalMillis: 15000,
        })
      : undefined,
    instrumentations: [
      getNodeAutoInstrumentations({
        '@opentelemetry/instrumentation-fs': { enabled: false },
      }),
    ],
  });
  sdk.start();
}

export const OTel = {
  enabled,
  sdk,
  async shutdown() {
    if (sdk) await sdk.shutdown();
  },
};

/**
 * Prometheus RED metrics. Always on, even when OTel is disabled, so the scrape
 * contract does not depend on the tracing pipeline being healthy.
 */
const registry = new Registry();
registry.setDefaultLabels({ service: process.env.OTEL_SERVICE_NAME ?? 'sre-demo-api' });

export const metrics = {
  registry,
  requestsTotal: new Counter({
    name: 'sre_api_requests_total',
    help: 'Total HTTP requests (RED: Rate).',
    labelNames: ['route', 'method', 'status'],
    registers: [registry],
  }),
  errorsTotal: new Counter({
    name: 'sre_api_errors_total',
    help: 'HTTP responses with status >= 500 (RED: Errors).',
    labelNames: ['route', 'method'],
    registers: [registry],
  }),
  duration: new Histogram({
    name: 'sre_api_request_duration_seconds',
    help: 'HTTP request duration (RED: Duration).',
    labelNames: ['route', 'method'],
    // Buckets chosen around the proposed 500ms SLO threshold so the histogram
    // can answer "what fraction was under budget" before the SLO is finalised.
    buckets: [0.005, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5],
    registers: [registry],
  }),
  inFlight: new Gauge({
    name: 'sre_api_requests_in_flight',
    help: 'In-flight HTTP requests.',
    registers: [registry],
  }),
  readiness: new Gauge({
    name: 'sre_api_readiness',
    help: '1 when the pod reports ready and should receive traffic.',
    registers: [registry],
  }),
  dependencyErrors: new Counter({
    name: 'sre_api_dependency_errors_total',
    help: 'Failed outbound calls to the mock dependency.',
    registers: [registry],
  }),
  async shutdown() {
    await registry.metrics().map((m) => m.reset?.());
  },
};

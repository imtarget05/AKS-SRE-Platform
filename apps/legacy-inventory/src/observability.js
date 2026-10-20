'use strict';

const { randomUUID } = require('node:crypto');
const { trace } = require('@opentelemetry/api');
const { resourceFromAttributes } = require('@opentelemetry/resources');
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { PeriodicExportingMetricReader } = require('@opentelemetry/sdk-metrics');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-http');
const { OTLPMetricExporter } = require('@opentelemetry/exporter-metrics-otlp-http');
const { HttpInstrumentation } = require('@opentelemetry/instrumentation-http');
const { ExpressInstrumentation } = require('@opentelemetry/instrumentation-express');
const { Counter, Gauge, Histogram, Registry } = require('prom-client');

const serviceName = process.env.OTEL_SERVICE_NAME ?? 'legacy-inventory-worker';
const endpoint = process.env.OTEL_EXPORTER_OTLP_ENDPOINT?.replace(/\/$/, '');
const registry = new Registry();
registry.setDefaultLabels({ service: serviceName });

const requestsTotal = new Counter({
    name: 'legacy_http_requests_total',
    help: 'HTTP requests completed by the LegacyApp.',
    labelNames: ['route', 'method', 'status_class'],
    registers: [registry],
});
const errorsTotal = new Counter({
    name: 'legacy_http_errors_total',
    help: 'HTTP 5xx responses by route and method.',
    labelNames: ['route', 'method'],
    registers: [registry],
});
const requestDuration = new Histogram({
    name: 'legacy_http_request_duration_seconds',
    help: 'HTTP request duration by route and method.',
    labelNames: ['route', 'method'],
    buckets: [0.005, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5],
    registers: [registry],
});
const requestsInFlight = new Gauge({
    name: 'legacy_http_requests_in_flight',
    help: 'HTTP requests currently being handled.',
    registers: [registry],
});

const sdk = process.env.OTEL_ENABLED === 'false'
    ? null
    : new NodeSDK({
        resource: resourceFromAttributes({
            'service.name': serviceName,
            'service.version': process.env.APP_VERSION ?? '1.0.0',
            'deployment.environment': process.env.NODE_ENV ?? 'production',
        }),
        traceExporter: endpoint ? new OTLPTraceExporter({ url: `${endpoint}/v1/traces` }) : undefined,
        metricReader: endpoint
            ? new PeriodicExportingMetricReader({
                exporter: new OTLPMetricExporter({ url: `${endpoint}/v1/metrics` }),
                exportIntervalMillis: 15000,
            })
            : undefined,
        instrumentations: [new HttpInstrumentation(), new ExpressInstrumentation()],
    });

if (sdk) sdk.start();

function recordHttpRequest({ route, method, statusCode, durationSeconds }) {
    const labels = { route, method, status_class: `${Math.floor(statusCode / 100)}xx` };
    requestsTotal.inc(labels);
    requestDuration.observe({ route, method }, durationSeconds);
    if (statusCode >= 500) errorsTotal.inc({ route, method });
}

const OTel = {
    async shutdown() {
        if (sdk) await sdk.shutdown();
    },
    trace,
};

module.exports = { OTel, registry, requestsInFlight, recordHttpRequest };
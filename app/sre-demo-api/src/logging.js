/**
 * Structured logger. Correlation authority lives HERE, in the application, not
 * in the log sink: the active OpenTelemetry span id is injected into every
 * record before the line is emitted. Per ADR-014 the sink routes bytes and does
 * not create correlation semantics, so a single grep on trace_id can join a
 * Grafana spike to a specific request's log line and its trace.
 *
 * Output is one JSON object per line on stdout. Fluent Bit collects it in the
 * Azure profile; Logstash in the OSS profile. Exactly one sink, never both.
 */
import { trace } from '@opentelemetry/api';

const LEVELS = { debug: 10, info: 20, warn: 30, error: 40 };

export function createLogger({ service = 'sre-demo-api', level = process.env.LOG_LEVEL ?? 'info' } = {}) {
  const threshold = LEVELS[level] ?? LEVELS.info;

  const emit = (levelName, fields, message) => {
    if ((LEVELS[levelName] ?? 0) < threshold) return;
    const span = trace.getActiveSpan();
    const spanContext = span?.spanContext?.();
    const record = {
      timestamp: new Date().toISOString(),
      level: levelName,
      service,
      message,
      ...(spanContext
        ? { trace_id: spanContext.traceId, span_id: spanContext.spanId }
        : {}),
      ...fields,
    };
    process.stdout.write(JSON.stringify(record) + '\n');
  };

  return {
    debug: (fields, message) => emit('debug', fields, message),
    info: (fields, message) => emit('info', fields, message),
    warn: (fields, message) => emit('warn', fields, message),
    error: (fields, message) => emit('error', fields, message),
  };
}

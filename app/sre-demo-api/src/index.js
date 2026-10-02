/**
 * Composition root. Wiring only — no business logic, matching the convention in
 * AGENTS.md for every project in this workspace.
 *
 * OpenTelemetry is initialised BEFORE any instrumented module is imported,
 * because auto-instrumentation patches modules at load time. Getting this
 * order wrong is the usual reason a Node OTel setup silently emits no traces.
 */
import { metrics } from './observability.js';
import { createLogger } from './logging.js';
import { createServer } from './server.js';
import { createState } from './state.js';

const logger = createLogger();
const state = createState({ logger });
const server = createServer({ metrics, state, logger });

const port = Number(process.env.PORT ?? 8080);
server.listen(port, '0.0.0.0', () => {
  logger.info(
    {
      port,
      failure_injection_armed: state.failureInjectionArmed(),
      dependency_url: process.env.DEPENDENCY_URL ?? null,
    },
    'sre-demo-api listening',
  );
});

// SIGTERM arrives first on a pod eviction or rolling update. Draining here is
// what keeps the rollout zero-downtime; SIGKILL arrives 30s later and is the
// reason the drain timeout below is well under that.
for (const signal of ['SIGTERM', 'SIGINT']) {
  process.on(signal, () => {
    logger.info({ signal }, 'signal received');
    server.shutdown();
  });
}

process.on('unhandledRejection', (err) => {
  logger.error({ err: String(err) }, 'unhandled rejection');
});

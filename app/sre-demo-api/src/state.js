/**
 * Runtime state and the mock dependency.
 *
 * The dependency is deliberately a separate HTTP service so that trace
 * propagation can be proven with a real parent/child span pair rather than
 * asserted. It is also the thing that readiness gates on, which is what makes
 * the readiness-vs-liveness split observable.
 */
import http from 'node:http';

export const ARMED_ENV = 'FAILURE_INJECTION_ARMED';

export function createState({ logger }) {
  const dependencyUrl = process.env.DEPENDENCY_URL ?? null;
  const armed = process.env[ARMED_ENV] === 'true';
  let ready = true;

  return {
    /** Failure injection is impossible unless explicitly armed in the env. */
    failureInjectionArmed: () => armed,

    /** Flip readiness without killing the process — the readiness half of the
     *  probe proof. Used by the failure-injection scenarios. */
    setReady: (value) => {
      ready = value;
      logger.warn({ ready: value }, 'readiness changed');
    },
    isReady: () => ready,

    /** Readiness fails when the process is not yet serving, or when the
     *  dependency is unreachable and we are configured to care. */
    async dependencyReady() {
      if (!ready) return false;
      if (!dependencyUrl) return true;
      if (process.env.READINESS_REQUIRES_DEPENDENCY !== 'true') return true;
      try {
        const res = await fetch(`${dependencyUrl}/health`, {
          signal: AbortSignal.timeout(Number(process.env.DEPENDENCY_TIMEOUT_MS ?? 1000)),
        });
        return res.ok;
      } catch {
        return false;
      }
    },

    async callDependency() {
      if (!dependencyUrl) {
        return { ok: true, detail: 'no dependency configured (single-process proof)' };
      }
      try {
        const res = await fetch(`${dependencyUrl}/work?ms=${process.env.DEPENDENCY_LATENCY_MS ?? 5}`, {
          signal: AbortSignal.timeout(Number(process.env.DEPENDENCY_TIMEOUT_MS ?? 2000)),
        });
        if (!res.ok) return { error: true, status: res.status };
        return { ok: true, status: res.status };
      } catch (err) {
        return { error: true, detail: String(err) };
      }
    },
  };
}

/** The mock dependency itself: small, stateless, and deliberately slow. */
export function createMockDependency({ logger }) {
  return http.createServer(async (req, res) => {
    const url = new URL(req.url, 'http://localhost');
    if (url.pathname === '/health') {
      res.setHeader('content-type', 'application/json');
      res.end(JSON.stringify({ status: 'ok', service: 'mock-dependency' }));
      return;
    }
    if (url.pathname === '/work') {
      const ms = Math.min(Number(url.searchParams.get('ms') ?? 5), 10000);
      const status = url.searchParams.get('status');
      if (status === '500') {
        res.statusCode = 500;
        res.end(JSON.stringify({ error: 'injected upstream failure' }));
        return;
      }
      await new Promise((r) => setTimeout(r, ms));
      res.setHeader('content-type', 'application/json');
      res.end(JSON.stringify({ service: 'mock-dependency', slept_ms: ms }));
      return;
    }
    res.statusCode = 404;
    res.end(JSON.stringify({ error: 'not found' }));
  });
}

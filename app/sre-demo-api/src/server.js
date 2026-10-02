import http from 'node:http';
import { URL } from 'node:url';

/**
 * HTTP surface.
 *
 * The probe split is the load-bearing design decision here:
 *
 *   /health/live   answers "is the process event loop alive" ONLY. It never
 *                  touches the dependency. If it did, a slow database would
 *                  trigger kubelet restart loops instead of merely draining the
 *                  pod from traffic.
 *   /health/ready  answers "should this pod receive traffic" and DOES depend on
 *                  the dependency. A failing dependency makes the pod
 *                  un-ready, so the Service drops its endpoint, and the pod is
 *                  not restarted.
 *
 * That difference is observable: inject a dependency failure and the pod stays
 * Running with 0 restarts while becoming un-ready.
 */
export function createServer({ metrics, state, logger }) {
  const startedAt = Date.now();

  const reply = (res, status, payload, route, method = 'GET') => {
    metrics.requestsTotal.inc({ route, method, status: String(status) });
    if (status >= 500) metrics.errorsTotal.inc({ route, method });
    res.statusCode = status;
    res.setHeader('content-type', 'application/json');
    res.end(JSON.stringify(payload));
  };

  const server = http.createServer(async (req, res) => {
    const started = process.hrtime.bigint();
    // The base URL is parsed for its PATH component only, so the Host header
    // cannot influence routing. Using `req.headers.host` as the base (the
    // obvious one-liner) lets a client supply the authority the URL is parsed
    // against, which is a Host-header injection surface even when the base is
    // discarded — and it makes behaviour depend on a client-controlled value
    // for no benefit, since only the path is read below.
    const url = new URL(req.url ?? '/', 'http://workload.invalid');
    const route = url.pathname;
    const method = req.method ?? 'GET';
    metrics.inFlight.inc();
    const done = (status) => {
      metrics.inFlight.dec();
      metrics.duration.observe(
        { route, method },
        Number(process.hrtime.bigint() - started) / 1e9,
      );
      return Number(process.hrtime.bigint() - started) / 1e9;
    };

    try {
      if (route === '/health/live') {
        reply(res, 200, { status: 'live', uptime_s: (Date.now() - startedAt) / 1000 }, route, method);
        return done(200);
      }

      if (route === '/health/ready') {
        const ready = await state.dependencyReady();
        metrics.readiness.set(Number(ready));
        reply(res, ready ? 200 : 503,
          { status: ready ? 'ready' : 'not-ready', dependency: ready }, route, method);
        return done(ready ? 200 : 503);
      }

      if (route === '/metrics') {
        res.setHeader('content-type', metrics.registry.contentType);
        res.end(await metrics.registry.metrics());
        return done(200);
      }

      if (route === '/api/work') {
        const iterations = Math.min(Number(url.searchParams.get('n') ?? 1000), 200000);
        const cpuStart = process.cpuUsage();
        let acc = 0;
        for (let i = 0; i < iterations; i += 1) acc += Math.sqrt(i);
        const cpu = process.cpuUsage(cpuStart);
        logger.info({ iterations, cpu_user_us: cpu.user, checksum: acc }, 'work executed');
        reply(res, 200, { route, iterations, checksum: acc }, route, method);
        return done(200);
      }

      // Real outbound call, so trace propagation yields a genuine parent/child
      // span pair instead of an asserted one.
      if (route === '/api/dependency') {
        const result = await state.callDependency();
        if (result.error) {
          metrics.dependencyErrors.inc();
          logger.error({ result }, 'dependency call failed');
        }
        const status = result.error ? 502 : 200;
        reply(res, status, { route, ...result }, route, method);
        return done(status);
      }

      // Test-only. Cannot be armed unless the env flag is set, so a production
      // deployment physically cannot expose it.
      if (route === '/api/fail') {
        if (state.failureInjectionArmed()) {
          logger.error({}, 'failure injected on purpose');
          reply(res, 500, { route, status: 500, error: 'injected' }, route, method);
          return done(500);
        }
        reply(res, 404,
          { route, status: 404, error: 'failure injection is not armed in this environment' }, route, method);
        return done(404);
      }

      if (route === '/internal/readiness') {
        // Lets a test flip readiness without killing the process.
        const value = url.searchParams.get('ready') === 'false' ? false : true;
        state.setReady(value);
        reply(res, 200, { ready: value }, route, method);
        return done(200);
      }

      reply(res, 404, { route, status: 404, error: 'not found' }, route, method);
      return done(404);
    } catch (err) {
      logger.error({ route, err: String(err) }, 'unhandled request error');
      reply(res, 500, { route, status: 500, error: String(err) }, route, method);
      return done(500);
    }
  });

  // Graceful shutdown: stop accepting new connections, let in-flight requests
  // finish. Without this, every rolling update produces 502s in the load
  // generator and the zero-downtime rollout proof becomes meaningless.
  server.shutdown = () => {
    logger.info({}, 'shutdown requested, draining in-flight requests');
    server.close(() => process.exit(0));
    const timer = setTimeout(() => process.exit(1), 10000);
    timer.unref();
  };

  return server;
}

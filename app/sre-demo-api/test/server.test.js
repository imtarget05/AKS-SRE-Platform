import { test } from 'node:test';
import assert from 'node:assert/strict';

process.env.OTEL_ENABLED = 'false';

const { createServer } = await import('../src/server.js');
const { metrics } = await import('../src/observability.js');
const { createState } = await import('../src/state.js');

const silentLogger = { debug() {}, info() {}, warn() {}, error() {} };

async function withServer(env, fn) {
  const saved = {};
  for (const [k, v] of Object.entries(env)) {
    saved[k] = process.env[k];
    if (v === undefined) delete process.env[k];
    else process.env[k] = v;
  }
  const state = createState({ logger: silentLogger });
  const server = createServer({ metrics, state, logger: silentLogger });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    await fn({ base, state });
  } finally {
    await new Promise((r) => server.close(r));
    for (const [k, v] of Object.entries(saved)) {
      if (v === undefined) delete process.env[k];
      else process.env[k] = v;
    }
  }
}

test('liveness responds 200 without consulting the dependency', async () => {
  await withServer({ DEPENDENCY_URL: 'http://127.0.0.1:1/', READINESS_REQUIRES_DEPENDENCY: 'true' },
    async ({ base }) => {
      const res = await fetch(`${base}/health/live`);
      assert.equal(res.status, 200);
      const body = await res.json();
      assert.equal(body.status, 'live');
    });
});

test('readiness reports not-ready when readiness is flipped false', async () => {
  await withServer({}, async ({ base, state }) => {
    const before = await fetch(`${base}/health/ready`);
    assert.equal(before.status, 200);
    assert.equal((await before.json()).status, 'ready');

    state.setReady(false);
    const after = await fetch(`${base}/health/ready`);
    assert.equal(after.status, 503);
    assert.equal((await after.json()).status, 'not-ready');
  });
});

test('readiness depends on the dependency when configured to', async () => {
  await withServer(
    { DEPENDENCY_URL: 'http://127.0.0.1:1/', READINESS_REQUIRES_DEPENDENCY: 'true', DEPENDENCY_TIMEOUT_MS: '200' },
    async ({ base }) => {
      const res = await fetch(`${base}/health/ready`);
      assert.equal(res.status, 503);
    });
});

test('metrics endpoint exposes RED metrics in Prometheus format', async () => {
  await withServer({}, async ({ base }) => {
    await fetch(`${base}/api/work?n=100`);
    const res = await fetch(`${base}/metrics`);
    assert.equal(res.status, 200);
    const body = await res.text();
    for (const name of [
      'sre_api_requests_total',
      'sre_api_errors_total',
      'sre_api_request_duration_seconds',
      'sre_api_requests_in_flight',
      'sre_api_readiness',
    ]) {
      assert.ok(body.includes(name), `expected ${name} in metrics output`);
    }
    assert.ok(body.includes('route="/api/work"'));
  });
});

test('/api/fail is unavailable unless explicitly armed', async () => {
  await withServer({ FAILURE_INJECTION_ARMED: undefined }, async ({ base }) => {
    const res = await fetch(`${base}/api/fail`);
    assert.equal(res.status, 404);
  });

  await withServer({ FAILURE_INJECTION_ARMED: 'true' }, async ({ base }) => {
    const res = await fetch(`${base}/api/fail`);
    assert.equal(res.status, 500);
    assert.equal((await res.json()).error, 'injected');
  });
});

test('internal readiness rejected 401 when token not configured', async () => {
  await withServer({ INTERNAL_READINESS_TOKEN: undefined }, async ({ base }) => {
    const res = await fetch(`${base}/internal/readiness?ready=true`);
    assert.equal(res.status, 401);
  });
});

test('internal readiness rejected 401 with wrong bearer token', async () => {
  await withServer({ INTERNAL_READINESS_TOKEN: 'test-only-readiness-flip-token-32chars' }, async ({ base }) => {
    const res = await fetch(`${base}/internal/readiness?ready=true`, {
      headers: { Authorization: 'Bearer wrong-token' },
    });
    assert.equal(res.status, 401);
  });
});

test('internal readiness flips state with correct bearer token', async () => {
  await withServer({ INTERNAL_READINESS_TOKEN: 'test-only-readiness-flip-token-32chars' }, async ({ base }) => {
    const first = await fetch(`${base}/health/ready`);
    assert.equal(first.status, 200);
    assert.equal((await first.json()).status, 'ready');

    const flip = await fetch(`${base}/internal/readiness?ready=false`, {
      headers: { Authorization: 'Bearer test-only-readiness-flip-token-32chars' },
    });
    assert.equal(flip.status, 200);
    assert.equal((await flip.json()).ready, false);

    const after = await fetch(`${base}/health/ready`);
    assert.equal(after.status, 503);
    assert.equal((await after.json()).status, 'not-ready');
  });
});

test('500 does not leak internals', async () => {
  await withServer({}, async ({ base, state }) => {
    state.dependencyReady = () => { throw new Error('boom'); };
    const res = await fetch(`${base}/health/ready`);
    assert.equal(res.status, 500);
    const body = await res.json();
    assert.equal(body.error, 'internal server error');
    assert.ok(!String(body).includes('boom'));
    assert.ok(!String(body).includes('Error:'));
    assert.ok(!String(body).includes('at '));
  });
});

test('every response carries x-request-id', async () => {
  await withServer({}, async ({ base }) => {
    const res = await fetch(`${base}/health/live`);
    assert.ok(res.headers.get('x-request-id'));
    assert.match(res.headers.get('x-request-id'), /^[0-9a-f-]{36}$/);
  });
});

test('unknown routes return 404', async () => {
  await withServer({}, async ({ base }) => {
    assert.equal((await fetch(`${base}/nope`)).status, 404);
  });
});

test('work endpoint is deterministic', async () => {
  await withServer({}, async ({ base }) => {
    const a = await (await fetch(`${base}/api/work?n=500`)).json();
    const b = await (await fetch(`${base}/api/work?n=500`)).json();
    assert.equal(a.checksum, b.checksum);
    assert.equal(a.iterations, 500);
  });
});

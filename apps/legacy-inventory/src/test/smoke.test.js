'use strict';

// Smoke tests for the productionized legacy worker.
// Uses the built-in node:test runner — zero extra dependencies, mirrors the
// "keep legacy deps minimal" principle of this project.

const test = require('node:test');
const assert = require('node:assert');
const http = require('node:http');

const app = require('../app');

test('GET /health returns healthy', async () => {
    const server = app.listen(0);
    await new Promise((resolve) => server.once('listening', resolve));
    const port = server.address().port;

    try {
        const body = await fetch(`http://localhost:${port}/health`).then((r) => {
            assert.strictEqual(r.status, 200);
            return r.json();
        });
        assert.strictEqual(body.status, 'healthy');
    } finally {
        server.close();
    }
});

test('POST /sync returns success message', async () => {
    const server = app.listen(0);
    await new Promise((resolve) => server.once('listening', resolve));
    const port = server.address().port;

    try {
        const body = await fetch(`http://localhost:${port}/sync`, { method: 'POST' }).then((r) => {
            assert.strictEqual(r.status, 200);
            return r.json();
        });
        assert.strictEqual(body.message, 'Inventory synced successfully');
    } finally {
        server.close();
    }
});

test('unknown route returns JSON 404', async () => {
    const server = app.listen(0);
    await new Promise((resolve) => server.once('listening', resolve));
    const port = server.address().port;

    try {
        const res = await fetch(`http://localhost:${port}/nope`);
        assert.strictEqual(res.status, 404);
        assert.ok((await res.json()).error);
    } finally {
        server.close();
    }
});

test('metrics and request logs use route templates with correlation ids', async () => {
    const logs = [];
    const originalLog = console.log;
    console.log = (line) => logs.push(line);
    const server = app.listen(0);
    await new Promise((resolve) => server.once('listening', resolve));
    const port = server.address().port;

    try {
        const requestId = 'a6c1b39d-1274-4a09-84cb-79d8ba6e32c4';
        const correlationId = '2a8ee11a-5918-44f1-ae84-8a43416ed605';
        const traceId = '4bf92f3577b34da6a3ce929d0e0e4736';
        const parentSpanId = '00f067aa0ba902b7';
        const response = await fetch(`http://localhost:${port}/sync`, {
            method: 'POST',
            headers: {
                'x-request-id': requestId,
                'x-correlation-id': correlationId,
                traceparent: `00-${traceId}-${parentSpanId}-01`,
            },
        });
        assert.strictEqual(response.status, 200);
        assert.strictEqual(response.headers.get('x-request-id'), requestId);
        assert.strictEqual(response.headers.get('x-correlation-id'), correlationId);

        const metrics = await fetch(`http://localhost:${port}/metrics`);
        const body = await metrics.text();
        assert.strictEqual(metrics.status, 200);
        assert.match(body, /legacy_http_requests_total/);
        assert.match(body, /route="\/sync"/);
        assert.doesNotMatch(body, new RegExp(requestId));

        const requestLog = logs.map((line) => JSON.parse(line)).find((line) => line.msg === 'request');
        assert.strictEqual(requestLog.requestId, requestId);
        assert.strictEqual(requestLog.correlationId, correlationId);
        assert.strictEqual(requestLog.route, '/sync');
        assert.strictEqual(requestLog.traceId, traceId);
        assert.ok(requestLog.spanId);
    } finally {
        console.log = originalLog;
        await new Promise((resolve) => server.close(resolve));
    }
});

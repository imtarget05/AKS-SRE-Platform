'use strict';

// Middleware layer: cross-cutting HTTP concerns (logging, 404, errors).
// Structured single-line JSON so Azure Log Analytics can parse it directly.
const { randomUUID } = require('node:crypto');
const { OTel, requestsInFlight, recordHttpRequest } = require('../observability');

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const BEARER_RE = /\bBearer\s+[A-Za-z0-9._~+/-]+=*/gi;
const SECRET_RE = /\b(password|token|secret|api[_-]?key)\s*[=:]\s*[^\s,;]+/gi;
const EMAIL_RE = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g;
const LONG_NUMBER_RE = /\b\d{8,}\b/g;

function safeId(value) {
    return typeof value === 'string' && UUID_RE.test(value) ? value : randomUUID();
}

function redact(value) {
    return String(value)
        .replace(BEARER_RE, 'Bearer [REDACTED]')
        .replace(SECRET_RE, '$1=[REDACTED]')
        .replace(EMAIL_RE, '[EMAIL]')
        .replace(LONG_NUMBER_RE, '[REDACTED_NUMBER]');
}

function requestLogger(req, res, next) {
    const requestId = safeId(req.get('x-request-id'));
    const correlationId = safeId(req.get('x-correlation-id'));
    req.requestId = requestId;
    req.correlationId = correlationId;
    res.set('x-request-id', requestId);
    res.set('x-correlation-id', correlationId);

    if (req.path === '/metrics') return next();

    const start = process.hrtime.bigint();
    requestsInFlight.inc();
    res.on('finish', () => {
        const durationMs = Number(process.hrtime.bigint() - start) / 1e6;
        const route = req.route?.path
            ? `${req.baseUrl || ''}${req.route.path}`
            : 'unmatched';
        const spanContext = OTel.trace.getActiveSpan()?.spanContext();
        recordHttpRequest({
            route,
            method: req.method,
            statusCode: res.statusCode,
            durationSeconds: durationMs / 1000,
        });
        const record = {
            level: 'info',
            time: new Date().toISOString(),
            msg: 'request',
            method: req.method,
            route,
            status: res.statusCode,
            durationMs: Number(durationMs.toFixed(1)),
            requestId,
            correlationId,
            ...(spanContext ? { traceId: spanContext.traceId, spanId: spanContext.spanId } : {}),
        };
        console.log(JSON.stringify(record));
        requestsInFlight.dec();
    });
    next();
}

function notFound(req, res) {
    res.status(404).json({ error: 'not found' });
}

// eslint-disable-next-line no-unused-vars
function errorHandler(err, req, res, _next) {
    console.error(JSON.stringify({
        level: 'error',
        time: new Date().toISOString(),
        msg: redact(err.message),
        errorType: err.name,
        requestId: req.requestId,
        correlationId: req.correlationId,
    }));
    res.status(500).json({ error: 'internal error' });
}

module.exports = { requestLogger, notFound, errorHandler };

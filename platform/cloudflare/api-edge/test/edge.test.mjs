import { test } from "node:test";
import assert from "node:assert/strict";
import { createHash, createHmac } from "node:crypto";
import handler from "../src/index.mjs";

const groups = ["RATE_ORDER", "RATE_AUTH", "RATE_AI", "RATE_STAFF", "RATE_GENERAL"];

function env(fetchImpl = async () => new Response('{"ok":true}')) {
  const calls = [];
  const value = {
    AZURE_ORIGIN_URL: "https://portfolio.southeastasia.cloudapp.azure.com/",
    ALLOWED_ORIGINS: "https://ops.pages.dev,https://quan.workers.dev",
    AZURE_ORIGIN: { fetch: async (...args) => { calls.push(args); return fetchImpl(...args); } },
  };
  for (const group of groups) value[group] = { limit: async () => ({ success: true }) };
  return { value, calls };
}

test("only fixed owner prefixes route through the mTLS binding", async () => {
  const { value, calls } = env();
  const paths = ["/flashsale/api/orders", "/opsbridge/api/v1/orders", "/quanlykho/api/v1/items"];
  for (const path of paths) {
    const response = await handler.fetch(new Request(`https://edge.workers.dev${path}`), value);
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("Cache-Control"), "private, no-store");
  }
  assert.equal(calls.length, 3);
  assert.equal(calls[0][0], "https://portfolio.southeastasia.cloudapp.azure.com/flashsale/api/orders");
  assert.equal((await handler.fetch(new Request("https://edge.workers.dev/admin"), value)).status, 404);
  assert.equal((await handler.fetch(new Request("https://edge.workers.dev/retail/api/v1/accounts"), value)).status, 404);
  assert.equal(calls.length, 3);
});

test("missing mTLS or rate binding fails closed and cannot reach origin", async () => {
  const { value, calls } = env();
  delete value.AZURE_ORIGIN;
  assert.equal((await handler.fetch(new Request("https://edge.workers.dev/flashsale/api/orders"), value)).status, 503);
  value.AZURE_ORIGIN = { fetch: async () => { throw Error("should not reach"); } };
  delete value.RATE_ORDER;
  assert.equal((await handler.fetch(new Request("https://edge.workers.dev/flashsale/api/orders", { method: "POST" }), value)).status, 503);
  assert.equal(calls.length, 0);
});

test("blocked origin, throttling and upstream outage do not leak business data", async () => {
  const { value } = env(async () => { throw Error("internal host secret"); });
  const unauthorized = new Request("https://edge.workers.dev/opsbridge/api/v1/orders", {
    headers: { Origin: "https://evil.example" },
  });
  assert.equal((await handler.fetch(unauthorized, value)).status, 403);
  value.RATE_GENERAL = { limit: async () => ({ success: false }) };
  assert.equal((await handler.fetch(new Request("https://edge.workers.dev/opsbridge/api/v1/orders"), value)).status, 429);
  value.RATE_GENERAL = { limit: async () => ({ success: true }) };
  const failed = await handler.fetch(new Request("https://edge.workers.dev/opsbridge/api/v1/orders"), value);
  assert.equal(failed.status, 503);
  assert.doesNotMatch(await failed.text(), /internal host secret/);
});

test("forwards owner credentials but strips caller supplied forwarding identity", async () => {
  const { value, calls } = env();
  const request = new Request("https://edge.workers.dev/quanlykho/api/v1/items", {
    headers: { Authorization: "Bearer alice", "X-Forwarded-Host": "evil.example", Origin: "https://ops.pages.dev" },
  });
  const response = await handler.fetch(request, value);
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("Access-Control-Allow-Origin"), "https://ops.pages.dev");
  assert.equal(calls[0][1].headers.get("Authorization"), "Bearer alice");
  assert.equal(calls[0][1].headers.get("X-Forwarded-Host"), null);
  assert.equal(calls[0][1].headers.get("X-Forwarded-Proto"), "https");
});

test("origin proof binds fresh nonce, configured origin host, and owner response", async () => {
  const body = '{"status":"healthy"}';
  const { value, calls } = env(async () => new Response(body, { status: 200 }));
  value.EDGE_PROOF_KEY = "a-private-proof-secret-at-least-32-bytes";
  const nonce = "a".repeat(32);
  const response = await handler.fetch(new Request("https://edge.workers.dev/flashsale/health/live", {
    headers: { "X-Portfolio-Proof-Nonce": nonce },
  }), value);
  assert.equal(response.status, 200);
  assert.equal(calls.length, 1);
  assert.equal(calls[0][1].headers.get("X-Portfolio-Proof-Nonce"), null);
  assert.equal(response.headers.get("X-Portfolio-Origin-Target"), "portfolio.southeastasia.cloudapp.azure.com");
  const bodyHash = createHash("sha256").update(body).digest("hex");
  const expected = createHmac("sha256", value.EDGE_PROOF_KEY)
    .update(`${nonce}\nportfolio.southeastasia.cloudapp.azure.com\n200\n${bodyHash}`).digest("hex");
  assert.equal(response.headers.get("X-Portfolio-Origin-Proof"), expected);
  assert.equal(response.headers.get("Cache-Control"), "private, no-store");
});

test("origin proof fails closed without secret or healthy owner response", async () => {
  const { value, calls } = env();
  const request = new Request("https://edge.workers.dev/flashsale/health/live", {
    headers: { "X-Portfolio-Proof-Nonce": "b".repeat(32) },
  });
  assert.equal((await handler.fetch(request, value)).status, 503);
  assert.equal(calls.length, 0);
  value.EDGE_PROOF_KEY = "a-private-proof-secret-at-least-32-bytes";
  assert.equal((await handler.fetch(request, value)).status, 503);
  assert.equal(calls.length, 1);
});

test("declarative route policy registry decouples application-specific rate limit tiers", async () => {
  const { resolvePolicy } = await import("../src/routes.mjs");
  assert.deepEqual(resolvePolicy("/flashsale/api/orders", "POST"), ["RATE_ORDER", "order"]);
  assert.deepEqual(resolvePolicy("/flashsale/api/orders", "GET"), ["RATE_GENERAL", "general"]);
  assert.deepEqual(resolvePolicy("/quanlykho/api/v1/auth/login", "POST"), ["RATE_AUTH", "auth"]);
  assert.deepEqual(resolvePolicy("/quanlykho/api/v1/ai/summary", "POST"), ["RATE_AI", "ai"]);
  assert.deepEqual(resolvePolicy("/opsbridge/investigations/run", "POST"), ["RATE_AI", "ai"]);
  assert.deepEqual(resolvePolicy("/quanlykho/api/v1/items", "POST"), ["RATE_STAFF", "staff"]);
  assert.deepEqual(resolvePolicy("/quanlykho/api/v1/items", "GET"), ["RATE_GENERAL", "general"]);
});

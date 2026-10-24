import { test } from "node:test";
import assert from "node:assert/strict";
import handler from "../src/index.mjs";

const groups = ["RATE_ORDER", "RATE_AUTH", "RATE_AI", "RATE_STAFF", "RATE_RETAIL", "RATE_GENERAL"];

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
  const paths = ["/flashsale/api/orders", "/opsbridge/api/v1/orders", "/quanlykho/api/v1/items", "/retail/api/v1/accounts"];
  for (const path of paths) {
    const response = await handler.fetch(new Request(`https://edge.workers.dev${path}`), value);
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("Cache-Control"), "private, no-store");
  }
  assert.equal(calls.length, 4);
  assert.equal(calls[0][0], "https://portfolio.southeastasia.cloudapp.azure.com/flashsale/api/orders");
  assert.equal((await handler.fetch(new Request("https://edge.workers.dev/admin"), value)).status, 404);
  assert.equal(calls.length, 4);
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
  const request = new Request("https://edge.workers.dev/retail/api/v1/accounts", {
    headers: { Authorization: "Bearer alice", "X-Forwarded-Host": "evil.example", Origin: "https://ops.pages.dev" },
  });
  const response = await handler.fetch(request, value);
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("Access-Control-Allow-Origin"), "https://ops.pages.dev");
  assert.equal(calls[0][1].headers.get("Authorization"), "Bearer alice");
  assert.equal(calls[0][1].headers.get("X-Forwarded-Host"), null);
  assert.equal(calls[0][1].headers.get("X-Forwarded-Proto"), "https");
});

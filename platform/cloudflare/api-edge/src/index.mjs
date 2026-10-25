import { ROUTE_REGISTRY, resolvePolicy } from "./routes.mjs";

// Reusable Cloudflare Edge Gateway entry point.
// Applications register their routing contracts in routes.mjs.
// The Azure Gateway validates mTLS client certificate; each owner API
// authenticates and authorizes its own business requests.
const prefixes = ROUTE_REGISTRY.map((r) => r.prefix);
const noStore = "private, no-store";

function json(status, error, extra = {}) {
  return new Response(JSON.stringify({ error }), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": noStore, ...extra },
  });
}

function cors(origin, env) {
  const allowed = (env.ALLOWED_ORIGINS ?? "").split(",").map((v) => v.trim());
  return origin && allowed.includes(origin)
    ? { "Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true", Vary: "Origin" }
    : {};
}

function policy(url, method) {
  return resolvePolicy(url.pathname, method);
}

async function actorKey(request, group) {
  if (group === "order" || group === "auth" || group === "general") {
    return request.headers.get("CF-Connecting-IP") ?? "unknown-ip";
  }
  // Never put bearer credentials in a rate-limit key or a log.
  const credential = request.headers.get("Authorization") ?? "";
  if (!credential) return request.headers.get("CF-Connecting-IP") ?? "unknown-ip";
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(credential));
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

async function originProof(secret, nonce, host, status, body) {
  const bodyHash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(body));
  const hex = Array.from(new Uint8Array(bodyHash), (b) => b.toString(16).padStart(2, "0")).join("");
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const signature = await crypto.subtle.sign("HMAC", key,
    new TextEncoder().encode(`${nonce}\n${host}\n${status}\n${hex}`));
  return Array.from(new Uint8Array(signature), (b) => b.toString(16).padStart(2, "0")).join("");
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin");
    const corsHeaders = cors(origin, env);
    if (origin && !corsHeaders["Access-Control-Allow-Origin"]) return json(403, "OriginForbidden");
    if (!prefixes.some((prefix) => url.pathname.startsWith(prefix))) return json(404, "UnknownRoute", corsHeaders);
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          ...corsHeaders,
          "Cache-Control": noStore,
          "Access-Control-Allow-Methods": "GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS",
          "Access-Control-Allow-Headers": "Authorization, Content-Type, Idempotency-Key, X-Outlet-Scope, X-Branch-Scope",
        },
      });
    }

    let target;
    try {
      target = new URL(env.AZURE_ORIGIN_URL ?? "");
      if (target.protocol !== "https:" || target.username || target.password || target.pathname !== "/") {
        return json(503, "OriginNotConfigured", corsHeaders);
      }
    } catch {
      return json(503, "OriginNotConfigured", corsHeaders);
    }
    if (!env.AZURE_ORIGIN?.fetch) return json(503, "MtlsBindingMissing", corsHeaders);

    const proofNonce = request.headers.get("X-Portfolio-Proof-Nonce");
    const proofRequested = url.pathname === "/flashsale/health/live" && request.method === "GET" && proofNonce !== null;
    if (proofRequested && (!/^[0-9a-f]{32}$/.test(proofNonce) || (env.EDGE_PROOF_KEY?.length ?? 0) < 32)) {
      return json(503, "OriginProofUnavailable", corsHeaders);
    }

    const [bindingName, group] = policy(url, request.method);
    const limiter = env[bindingName];
    // A missing rate binding is a deployment error, never an unthrottled path.
    if (!limiter?.limit) return json(503, "RateLimitBindingMissing", corsHeaders);
    try {
      const key = `${group}:${await actorKey(request, group)}`;
      if (!(await limiter.limit({ key })).success) {
        return json(429, "RateLimited", { ...corsHeaders, "Retry-After": "10" });
      }
    } catch {
      return json(503, "RateLimiterUnavailable", corsHeaders);
    }

    target.pathname = url.pathname;
    target.search = url.search;
    const headers = new Headers(request.headers);
    // A caller may not impersonate the edge or select a different backend.
    for (const name of ["Host", "X-Forwarded-For", "X-Forwarded-Host", "X-Forwarded-Proto", "X-Real-IP", "X-Portfolio-Proof-Nonce"]) {
      headers.delete(name);
    }
    headers.set("X-Forwarded-Proto", "https");
    try {
      const response = await env.AZURE_ORIGIN.fetch(target.toString(), {
        method: request.method,
        headers,
        body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
        redirect: "manual",
      });
      if (response.status >= 300 && response.status < 400) return json(502, "OriginRedirectRejected", corsHeaders);
      const responseHeaders = new Headers(response.headers);
      responseHeaders.set("Cache-Control", noStore);
      if (proofRequested) {
        const body = await response.clone().text();
        if (response.status !== 200 || !/"status"\s*:\s*"healthy"/.test(body)) {
          return json(503, "OriginProofUnhealthy", corsHeaders);
        }
        responseHeaders.set("X-Portfolio-Origin-Proof",
          await originProof(env.EDGE_PROOF_KEY, proofNonce, target.host, response.status, body));
        responseHeaders.set("X-Portfolio-Origin-Target", target.host);
        responseHeaders.set("X-Portfolio-Proof-Nonce", proofNonce);
      }
      for (const [name, value] of Object.entries(corsHeaders)) responseHeaders.set(name, value);
      return new Response(response.body, { status: response.status, headers: responseHeaders });
    } catch {
      return json(503, "OriginUnavailable", corsHeaders);
    }
  },
};

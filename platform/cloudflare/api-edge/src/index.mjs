// One Cloudflare Workers API entry point for the four owner services.
// The Azure Gateway still validates the mTLS client certificate and each
// owner API still authenticates and authorizes its own business requests.
const prefixes = ["/flashsale/", "/opsbridge/", "/quanlykho/", "/retail/"];
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
  if (url.pathname.startsWith("/flashsale/") && method === "POST" && /\/api\/orders\/?$/.test(url.pathname)) {
    return ["RATE_ORDER", "order"];
  }
  if (/\/(login|auth|token)(\/|$)/.test(url.pathname)) return ["RATE_AUTH", "auth"];
  if (/\/ai(\/|$)/.test(url.pathname) || url.pathname.includes("/investigations")) return ["RATE_AI", "ai"];
  if (url.pathname.startsWith("/retail/")) return ["RATE_RETAIL", "retail"];
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) return ["RATE_STAFF", "staff"];
  return ["RATE_GENERAL", "general"];
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
    for (const name of ["Host", "X-Forwarded-For", "X-Forwarded-Host", "X-Forwarded-Proto", "X-Real-IP"]) {
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
      for (const [name, value] of Object.entries(corsHeaders)) responseHeaders.set(name, value);
      return new Response(response.body, { status: response.status, headers: responseHeaders });
    } catch {
      return json(503, "OriginUnavailable", corsHeaders);
    }
  },
};

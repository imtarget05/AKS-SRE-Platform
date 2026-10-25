// Declarative routing contracts for multi-application edge gateway.
// Platform Edge provides standard security, mTLS origin binding, CORS, and rate limiting.
// Each application declares its prefix and traffic tier policy according to a stable contract.

export const ROUTE_REGISTRY = [
  {
    prefix: "/flashsale/",
    service: "flashsale-backend",
    policies: [
      {
        pattern: /\/api\/orders\/?$/,
        methods: ["POST"],
        binding: "RATE_ORDER",
        group: "order",
      },
    ],
  },
  {
    prefix: "/opsbridge/",
    service: "opsbridge-platform",
    policies: [
      {
        pattern: /\/investigations(\/|$)/,
        methods: ["*"],
        binding: "RATE_AI",
        group: "ai",
      },
    ],
  },
  {
    prefix: "/quanlykho/",
    service: "quanlykho-inventory",
    policies: [
      {
        pattern: /\/ai(\/|$)/,
        methods: ["*"],
        binding: "RATE_AI",
        group: "ai",
      },
    ],
  },
];

// Common cross-cutting gateway route policies
export const COMMON_POLICIES = [
  {
    pattern: /\/(login|auth|token)(\/|$)/,
    methods: ["*"],
    binding: "RATE_AUTH",
    group: "auth",
  },
  {
    pattern: /\/ai(\/|$)/,
    methods: ["*"],
    binding: "RATE_AI",
    group: "ai",
  },
  {
    pattern: /.*/,
    methods: ["POST", "PUT", "PATCH", "DELETE"],
    binding: "RATE_STAFF",
    group: "staff",
  },
  {
    pattern: /.*/,
    methods: ["*"],
    binding: "RATE_GENERAL",
    group: "general",
  },
];

export function resolvePolicy(pathname, method) {
  // 1. Check application-specific registered rules
  for (const route of ROUTE_REGISTRY) {
    if (pathname.startsWith(route.prefix)) {
      for (const rule of route.policies) {
        const methodMatch = rule.methods.includes("*") || rule.methods.includes(method);
        if (methodMatch && rule.pattern.test(pathname)) {
          return [rule.binding, rule.group];
        }
      }
    }
  }

  // 2. Fall back to common standard traffic policies
  for (const rule of COMMON_POLICIES) {
    const methodMatch = rule.methods.includes("*") || rule.methods.includes(method);
    if (methodMatch && rule.pattern.test(pathname)) {
      return [rule.binding, rule.group];
    }
  }

  return ["RATE_GENERAL", "general"];
}

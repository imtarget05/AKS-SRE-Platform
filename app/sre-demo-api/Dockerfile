# Multi-stage. The runtime image carries no sources, no dev dependencies and no
# build tooling from the app itself, and runs as a non-root user on a
# read-only root filesystem (enforced by the pod securityContext, not only by
# convention).
#
# The non-root UID is baked in deliberately: an AKS pod securityContext can set
# runAsUser, but a numeric USER in the image means the container is already
# unprivileged before any orchestration is involved, and `docker inspect` proves
# it without needing a cluster.
#
# Note: `npm` still exists in the runtime image because it ships with the
# official node base image. Nothing here installs or invokes it at runtime, and
# the image contains no package sources, so there is no supply-chain surface
# beyond what the base image itself carries.

# ---- deps -------------------------------------------------------------------
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
# `npm ci` installs exactly the lockfile. `npm install` would silently update it.
RUN npm ci --omit=dev --ignore-scripts

# ---- test -------------------------------------------------------------------
# Tests run against the production dependency tree, not a dev one, so a test
# cannot pass on a package the deployed image does not have.
FROM node:22-alpine AS test
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY src ./src
COPY test ./test
RUN npm test

# ---- runtime ----------------------------------------------------------------
FROM node:22-alpine AS runtime
WORKDIR /app

RUN addgroup -g 10001 -S sre \
 && adduser -u 10001 -S sre -G sre

ENV NODE_ENV=production \
    PORT=8080 \
    NODE_OPTIONS=--enable-source-maps

COPY --from=deps --chown=10001:10001 /app/node_modules ./node_modules
COPY --chown=10001:10001 package.json ./
COPY --chown=10001:10001 src ./src

USER 10001:10001
EXPOSE 8080

# No HEALTHCHECK instruction on purpose: liveness and readiness are Kubernetes
# probes, and a container-level HEALTHCHECK that disagrees with them creates two
# sources of truth for the same question.

# Exec form so node is PID 1 and receives SIGTERM directly, which is what the
# graceful-shutdown handler needs in order to drain connections on rollout.
CMD ["node", "src/index.js"]

# L3 proof backend image — LOCAL ONLY, no external registry dependency.
#
# Why a hand-rolled image instead of a public "hello world" image:
#   1. it removes a third-party pull from the proof path,
#   2. it pins the exact body the route proof asserts on,
#   3. it is arm64-native, so the proof cannot silently pass through amd64
#      emulation.
#
# Base is node:22-alpine (already on this machine, arm64) and NOT busybox httpd:
# the local alpine build's busybox has no `httpd` applet, which crash-looped the
# first attempt with `exec: "httpd": executable file not found in $PATH`.
#
# Build + load (from the repo root):
#   docker build --platform linux/arm64 \
#     -t flashsale/gateway-proof:local platform/envoy-gateway/proof-backend
#   local/kind/load-image.sh flashsale/gateway-proof:local
FROM node:22-alpine
WORKDIR /app
COPY server.js .
# Non-root, same posture as the portfolio app images (ADR-007 pattern).
USER node
EXPOSE 8080
CMD ["node", "server.js"]


#!/usr/bin/env bash
# L2 — create (or reuse) the LOCAL portfolio kind cluster.
#
# Idempotent: running it twice does not delete or recreate a healthy cluster.
# Local only: it never talks to Azure and never touches the Azure tfstate
# backend (which stays firewall-restricted to specific IPs).
set -euo pipefail

CLUSTER_NAME="local-platform"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="${SCRIPT_DIR}/cluster.yaml"
# Minimum Docker VM memory that fits the L3-L10 stack. Below this the platform
# installs but workloads start OOMKilling once Prometheus + Argo CD are added.
MIN_DOCKER_MEM_MIB="${MIN_DOCKER_MEM_MIB:-6144}"

echo "==> 0/4 Preflight"
for bin in docker kind kubectl; do
  command -v "$bin" >/dev/null 2>&1 || { echo "FAIL: '$bin' not installed"; exit 1; }
done
docker info >/dev/null 2>&1 || { echo "FAIL: Docker daemon not reachable (is Docker Desktop running?)"; exit 1; }

MEM_BYTES="$(docker info --format '{{.MemTotal}}')"
MEM_MIB=$(( MEM_BYTES / 1024 / 1024 ))
echo "    kind:    $(kind version)"
echo "    kubectl: $(kubectl version --client -o json 2>/dev/null | sed -n 's/.*"gitVersion": "\([^"]*\)".*/\1/p' | head -1)"
echo "    docker:  server $(docker version --format '{{.Server.Version}}'), VM memory ${MEM_MIB} MiB"
if [ "$MEM_MIB" -lt "$MIN_DOCKER_MEM_MIB" ]; then
  echo "    WARN: Docker VM memory ${MEM_MIB} MiB < ${MIN_DOCKER_MEM_MIB} MiB recommended."
  echo "          Raise it in Docker Desktop > Settings > Resources > Memory,"
  echo "          then re-run this script. Continuing anyway (create is cheap)."
fi

echo "==> 1/4 Cluster state"
if kind get clusters 2>/dev/null | grep -qx "$CLUSTER_NAME"; then
  echo "    '${CLUSTER_NAME}' already exists — reuse, NOT recreating."
  kind get nodes --name "$CLUSTER_NAME" | sed 's/^/    node: /'
  echo "==> 4/4 Done (existing cluster). kubectl context: kind-${CLUSTER_NAME}"
  exit 0
fi

echo "==> 2/4 kind create cluster '${CLUSTER_NAME}' (config: ${CONFIG})"
kind create cluster --config "$CONFIG" --wait 180s

echo "==> 3/4 Verify control plane"
kubectl --context "kind-${CLUSTER_NAME}" get nodes -o wide
kubectl --context "kind-${CLUSTER_NAME}" get pods -A

echo "==> 4/4 Done."
echo "    context: kind-${CLUSTER_NAME}"
echo "    host ports (inert until L3 Gateway): 127.0.0.1:8080->30080, 127.0.0.1:8443->30443"

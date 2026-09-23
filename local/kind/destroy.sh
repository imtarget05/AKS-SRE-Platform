#!/usr/bin/env bash
# L2 — delete the LOCAL portfolio kind cluster.
#
# Scope: the kind cluster ONLY. This script never deletes Docker volumes of the
# FlashSale compose stack, local backup sets, or any Azure resource.
set -euo pipefail

CLUSTER_NAME="local-platform"

command -v kind >/dev/null 2>&1 || { echo "FAIL: 'kind' not installed"; exit 1; }

if ! kind get clusters 2>/dev/null | grep -qx "$CLUSTER_NAME"; then
  echo "No cluster named '${CLUSTER_NAME}' — nothing to do."
  exit 0
fi

if [ "${1:-}" != "-y" ]; then
  printf "Delete kind cluster '%s' (all local workloads/volumes inside it)? [y/N] " "$CLUSTER_NAME"
  read -r reply
  case "$reply" in
    [yY]|[yY][eE][sS]) ;;
    *) echo "Aborted."; exit 0 ;;
  esac
fi

kind delete cluster --name "$CLUSTER_NAME"
echo "Deleted. Remaining kind clusters:"
kind get clusters 2>/dev/null | sed 's/^/  /' || true

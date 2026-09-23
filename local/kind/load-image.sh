#!/usr/bin/env bash
# Load locally BUILT images into every node of the LOCAL kind cluster.
# No registry, no credentials — this is the L1/L5 image-delivery path.
#
# WHY THIS IS NOT `kind load docker-image` (reproduced 2026-09-23, three runs):
#   $ kind load docker-image alpine:latest --name local-platform
#   ERROR: failed to load image: command "docker exec --privileged -i
#     local-platform-worker ctr --namespace=k8s.io images import --all-platforms
#     --digests --snapshotter=overlayfs -" failed with error: exit status 1
#   Command Output: ctr: content digest sha256:d56c381f...: not found
#
#   Root cause, measured by parsing index.json inside each archive:
#     - plain `docker save`  -> the index references a NESTED OCI *index*
#       (mediaType application/vnd.oci.image.index.v1+json, platform: none), so
#       ctr's `--all-platforms` resolution cannot find a concrete platform
#       manifest -> "content digest ...: not found".
#     - `docker save --platform linux/arm64` -> the index carries concrete
#       `application/vnd.oci.image.manifest.v1+json` entry(ies) -> import works.
#   This matches kind's documented workaround for the Docker containerd image
#   store. The image store is NOT disabled and no kind-internal `docker exec ...
#   ctr` call is used.
#
# Usage:
#   ./load-image.sh flashsale/order-api:local flashsale/order-worker:local
set -euo pipefail

CLUSTER_NAME="${CLUSTER_NAME:-local-platform}"

die() { echo "FAIL: $*" >&2; exit 1; }

command -v kind >/dev/null 2>&1 || die "'kind' not installed"
command -v docker >/dev/null 2>&1 || die "'docker' not installed"
[ "$#" -ge 1 ] || die "usage: $0 <image> [image...]"

kind get clusters 2>/dev/null | grep -qx "$CLUSTER_NAME" \
  || die "kind cluster '${CLUSTER_NAME}' does not exist (run ./create.sh)"

# --- platform detection: never assume the host architecture ---
case "$(uname -m)" in
  arm64|aarch64) PLATFORM="linux/arm64" ;;
  x86_64|amd64)  PLATFORM="linux/amd64" ;;
  *) die "unsupported host architecture: $(uname -m)" ;;
esac

# Portable (macOS /bin/bash is 3.2 — no `mapfile`): read node list line by line.
NODES=()
while IFS= read -r _node; do
  [ -n "$_node" ] && NODES+=("$_node")
done < <(kind get nodes --name "$CLUSTER_NAME")
[ "${#NODES[@]}" -ge 1 ] || die "no nodes found for '${CLUSTER_NAME}'"

for NODE in "${NODES[@]}"; do
  NODE_ARCH="$(docker exec "$NODE" uname -m)"
  case "$NODE_ARCH" in
    aarch64|arm64) NODE_PLATFORM="linux/arm64" ;;
    x86_64)        NODE_PLATFORM="linux/amd64" ;;
    *)             NODE_PLATFORM="unknown-${NODE_ARCH}" ;;
  esac
  [ "$NODE_PLATFORM" = "$PLATFORM" ] || die \
    "node ${NODE} runs ${NODE_ARCH} while this host exports ${PLATFORM}; a single-platform archive would not run there"
done
echo "host  : $(uname -m) -> export platform ${PLATFORM}"
echo "nodes : ${#NODES[@]} node(s), all ${PLATFORM}"

TMP_TAR=""
cleanup() { if [ -n "$TMP_TAR" ]; then rm -f "$TMP_TAR"; fi; }
trap cleanup EXIT

REFS=()
for IMAGE in "$@"; do
  echo "==> ${IMAGE}"
  docker image inspect "$IMAGE" >/dev/null 2>&1 \
    || die "'${IMAGE}' is not in the local Docker daemon — build it first"

  ARCH="$(docker image inspect "$IMAGE" --format '{{.Architecture}}/{{.Os}}')"
  echo "    local image : ${ARCH}"
  if [ "${ARCH%/*}" != "${PLATFORM#*/}" ]; then
    echo "    WARN: image arch ${ARCH} != node platform ${PLATFORM}; the export"
    echo "          may resolve to a different variant or fail"
  fi

  TMP_TAR="$(mktemp -t kind-image-XXXXXX.tar)"
  # Single-platform export: this is the step that makes the import succeed.
  docker image save --platform "$PLATFORM" -o "$TMP_TAR" "$IMAGE"
  # `kind load image-archive` prints nothing on success and exits non-zero on
  # failure; `set -e` makes that fatal instead of silently ignored.
  kind load image-archive "$TMP_TAR" --name "$CLUSTER_NAME"
  rm -f "$TMP_TAR"; TMP_TAR=""
  REFS+=("$IMAGE")
done

echo "==> Verify presence on every node"
FAILED=0
for IMAGE in "${REFS[@]}"; do
  # Normalize the same way on both sides (crictl/ctr store canonical refs):
  # strip the docker.io registry and the implicit library/ namespace, default
  # the tag to :latest. Then compare as EXACT strings with grep -Fx — no regex
  # escaping, which BSD sed/grep handle differently from GNU.
  KEY="${IMAGE#docker.io/}"; KEY="${KEY#library/}"
  case "$KEY" in
    *:*) ;;
    *)   KEY="${KEY}:latest" ;;
  esac
  for NODE in "${NODES[@]}"; do
    if docker exec "$NODE" ctr --namespace=k8s.io images ls -q \
        | sed -e 's|^docker\.io/||' -e 's|^library/||' \
        | grep -Fxq "$KEY"; then
      printf '    OK      %-34s %s\n' "$NODE" "$KEY"
    else
      printf '    MISSING %-34s %s\n' "$NODE" "$KEY"
      FAILED=1
    fi
  done
done

[ "$FAILED" -eq 0 ] || die "at least one node is missing an image"

echo "==> Done. Reference it with imagePullPolicy: IfNotPresent (or Never) so the"
echo "    loaded image is used instead of a registry pull."

#!/usr/bin/env bash
# Build, push, deploy, break, and restore the same immutable image in local kind.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cluster_name="${DIGEST_DRILL_CLUSTER:-sre-digest-drill}"
registry_name="${DIGEST_DRILL_REGISTRY:-sre-digest-registry}"
registry_port="${DIGEST_DRILL_PORT:-5002}"
source_sha="$(git -C "$repo_root" rev-parse HEAD)"
original_context="$(kubectl config current-context 2>/dev/null || true)"
created_cluster=0
created_registry=0

cleanup() {
  if (( created_cluster )); then kind delete cluster --name "$cluster_name"; fi
  if (( created_registry )); then docker rm -f "$registry_name" >/dev/null; fi
  if [[ -n "$original_context" ]]; then
    kubectl config use-context "$original_context" >/dev/null || true
  fi
}
trap cleanup EXIT

if docker container inspect "$registry_name" >/dev/null 2>&1; then
  echo "Registry container already exists: $registry_name" >&2
  exit 1
fi
if kind get clusters | grep -Fxq "$cluster_name"; then
  echo "kind cluster already exists: $cluster_name" >&2
  exit 1
fi

docker run -d --restart=always -p "127.0.0.1:${registry_port}:5000" \
  --name "$registry_name" registry:3 >/dev/null
created_registry=1
cat <<'KIND_CONFIG' | kind create cluster --name "$cluster_name" --config=- --wait 120s
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
containerdConfigPatches:
- |-
  [plugins."io.containerd.grpc.v1.cri".registry]
    config_path = "/etc/containerd/certs.d"
KIND_CONFIG
created_cluster=1
docker network connect kind "$registry_name"

for node in $(kind get nodes --name "$cluster_name"); do
  registry_dir="/etc/containerd/certs.d/localhost:${registry_port}"
  docker exec "$node" mkdir -p "$registry_dir"
  # HTTP stays inside the disposable Docker kind network; no credentials are sent.
  printf '[host."http://%s:5000"]\n' "$registry_name" | docker exec -i "$node" tee "$registry_dir/hosts.toml" >/dev/null # NOSONAR
done

image_tag="localhost:${registry_port}/sre-demo-api:${source_sha}"
docker build -t "$image_tag" "$repo_root/app/sre-demo-api"
docker push "$image_tag"
image_ref="$(docker image inspect --format '{{index .RepoDigests 0}}' "$image_tag")"
if [[ ! "$image_ref" =~ ^localhost:${registry_port}/sre-demo-api@sha256:[0-9a-f]{64}$ ]]; then
  echo "Push did not produce a digest-pinned image reference: $image_ref" >&2
  exit 1
fi

cd "$repo_root"
python3 scripts/kind_rollback_drill.py --context "kind-${cluster_name}" \
  --image "$image_ref" --require-digest
echo "Digest release and rollback verified: $image_ref"

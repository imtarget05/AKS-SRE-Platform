#!/usr/bin/env python3
"""Run a measured bad-image rollback of this repo's API in an isolated kind cluster.

The caller builds and loads --image into the cluster. This script owns only its
temporary namespace. It records Kubernetes state and live HTTP observations.
"""

import argparse
import json
import re
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUTPUT = Path("demo-results/kind-rollback")
DEPLOYMENT = "deployment/sre-demo-api"


def now():
    return datetime.now(timezone.utc).isoformat()


def run(command, *, input_text=None, timeout=120):
    # argv list with shell=False; the context is checked against the active kind context.
    return subprocess.run(command, input=input_text, text=True, capture_output=True, shell=False,  # NOSONAR
                          check=True, timeout=timeout).stdout


def wait_for(predicate, seconds, description):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(1)
    raise TimeoutError(f"Timed out waiting for {description}")


def http_status():
    try:
        with urllib.request.urlopen("http://127.0.0.1:18088/health/ready", timeout=2) as response:
            return response.status
    except (urllib.error.URLError, TimeoutError):
        return 0


def image_pull_failure(kube, namespace):
    pods = json.loads(run(kube + ["-n", namespace, "get", "pods", "-l", "app=sre-demo-api", "-o", "json"]))
    for pod in pods["items"]:
        for state in pod.get("status", {}).get("containerStatuses", []):
            reason = state.get("state", {}).get("waiting", {}).get("reason")
            if reason in {"ErrImagePull", "ImagePullBackOff"}:
                return {"pod": pod["metadata"]["name"], "reason": reason}
    return None


def assert_ready_pods_use_digest(kube, namespace, digest):
    pods = json.loads(run(kube + ["-n", namespace, "get", "pods", "-l", "app=sre-demo-api", "-o", "json"]))
    image_ids = [state.get("imageID", "") for pod in pods["items"]
                 for state in pod.get("status", {}).get("containerStatuses", [])
                 if state.get("ready")]
    if len(image_ids) != 2 or any(not image_id.endswith("@" + digest) for image_id in image_ids):
        raise AssertionError(f"ready pods do not run the pushed runtime image digest {digest}: {image_ids}")
    return image_ids


def collect_evidence(kube, namespace, evidence, port_forward, *, namespace_created=True):
    evidence["finished_utc"] = now()
    (OUTPUT / "result.json").write_text(json.dumps(evidence, indent=2) + "\n")
    if not namespace_created:
        return
    commands = {"pods.json": ["get", "pods", "-o", "json"],
                "events.txt": ["get", "events", "--sort-by=.metadata.creationTimestamp"],
                "deployment.yaml": ["get", "deployment", "sre-demo-api", "-o", "yaml"]}
    for label, command in commands.items():
        try:
            (OUTPUT / label).write_text(run(kube + ["-n", namespace] + command, timeout=15))
        except Exception:
            pass
    if port_forward is not None:
        port_forward.terminate()
        try:
            port_forward.wait(timeout=5)
        except subprocess.TimeoutExpired:
            port_forward.kill()
    run(kube + ["delete", "namespace", namespace, "--ignore-not-found=true", "--wait=false"], timeout=30)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--require-digest", action="store_true")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    namespace = "sre-rollback-drill"
    bad_image = "invalid.local/sre-demo-api:deliberately-missing"
    kube = ["kubectl", "--context", args.context]
    evidence = {"scope": "isolated_kind_repo_workload", "context": args.context,
                "good_image": args.image, "bad_image": bad_image,
                "started_utc": now(), "events": [], "status": "failed"}

    def event(name, **fields):
        evidence["events"].append({"name": name, "timestamp_utc": now(), **fields})

    def get_deployment():
        return json.loads(run(kube + ["-n", namespace, "get", "deployment", "sre-demo-api", "-o", "json"]))

    port_forward = None
    namespace_created = False
    try:
        if args.require_digest and not re.fullmatch(r"[^@]+@sha256:[0-9a-f]{64}", args.image):
            raise ValueError("digest-pinned image is required for the release drill")
        current_context = run(["kubectl", "config", "current-context"]).strip()
        if args.context != current_context or not args.context.startswith("kind-"):
            raise ValueError("Explicit context must be the active kind context")
        run(kube + ["create", "namespace", namespace])
        namespace_created = True
        manifest = {
            "apiVersion": "apps/v1", "kind": "Deployment",
            "metadata": {"name": "sre-demo-api", "namespace": namespace},
            "spec": {"replicas": 2, "revisionHistoryLimit": 3,
                     "strategy": {"type": "RollingUpdate", "rollingUpdate": {"maxSurge": 1, "maxUnavailable": 0}},
                     "selector": {"matchLabels": {"app": "sre-demo-api"}},
                     "template": {"metadata": {"labels": {"app": "sre-demo-api"}},
                                  "spec": {"containers": [{"name": "sre-demo-api", "image": args.image,
                                      "imagePullPolicy": "IfNotPresent", "ports": [{"containerPort": 8080}],
                                      "readinessProbe": {"httpGet": {"path": "/health/ready", "port": 8080},
                                                         "periodSeconds": 2},
                                      "livenessProbe": {"httpGet": {"path": "/health/live", "port": 8080},
                                                        "periodSeconds": 5}}]}}}}
        run(kube + ["apply", "-f", "-"], input_text=json.dumps(manifest))
        run(kube + ["-n", namespace, "rollout", "status", DEPLOYMENT, "--timeout=180s"], timeout=190)
        baseline = get_deployment()
        if baseline["status"].get("readyReplicas") != 2:
            raise AssertionError("Baseline needs two ready replicas")
        runtime_ids = assert_ready_pods_use_digest(kube, namespace, args.image.rsplit("@", 1)[1]) \
            if args.require_digest else []
        event("baseline_ready", ready_replicas=2, runtime_image_ids=runtime_ids)

        port_forward = subprocess.Popen(kube + ["-n", namespace, "port-forward", DEPLOYMENT, "18088:8080"],
                                        stdout=(OUTPUT / "port-forward.log").open("w"), stderr=subprocess.STDOUT)

        wait_for(lambda: http_status() == 200, 30, "baseline HTTP 200")
        event("baseline_http_healthy", http_status=200)
        run(kube + ["-n", namespace, "set", "image", DEPLOYMENT, f"sre-demo-api={bad_image}"])
        event("bad_image_deployed")

        failure = wait_for(lambda: image_pull_failure(kube, namespace), 120, "observed image pull failure")
        ready_during_fault = get_deployment()["status"].get("readyReplicas", 0)
        fault_http = http_status()
        event("fault_detected", **failure, ready_replicas=ready_during_fault, http_status=fault_http)
        if ready_during_fault != 2 or fault_http != 200:
            raise AssertionError("Healthy replicas did not stay available during failed rollout")

        rollback_start = time.monotonic()
        run(kube + ["-n", namespace, "rollout", "undo", DEPLOYMENT])
        run(kube + ["-n", namespace, "rollout", "status", DEPLOYMENT, "--timeout=180s"], timeout=190)
        rollback_seconds = round(time.monotonic() - rollback_start, 3)
        restored = get_deployment()
        restored_image = restored["spec"]["template"]["spec"]["containers"][0]["image"]
        restored_ready = restored["status"].get("readyReplicas", 0)
        restored_http = wait_for(lambda: http_status() == 200, 30, "restored HTTP 200")
        event("rollback_verified", image=restored_image, ready_replicas=restored_ready,
              http_status=200 if restored_http else 0, duration_seconds=rollback_seconds)
        if restored_image != args.image or restored_ready != 2:
            raise AssertionError("Rollback did not restore the exact image and two ready replicas")
        if args.require_digest:
            assert_ready_pods_use_digest(kube, namespace, args.image.rsplit("@", 1)[1])
        evidence["status"] = "passed"
    except Exception as exc:
        evidence["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        collect_evidence(kube, namespace, evidence, port_forward,
                         namespace_created=namespace_created)


if __name__ == "__main__":
    main()

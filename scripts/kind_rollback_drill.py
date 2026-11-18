#!/usr/bin/env python3
"""Run a measured bad-image rollback of this repo's API in an isolated kind cluster.

The caller builds and loads --image into the cluster. This script owns only its
temporary namespace. It records Kubernetes state and live HTTP observations.
"""

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def run(command, *, input_text=None, timeout=120):
    return subprocess.run(command, input=input_text, text=True, capture_output=True,
                          check=True, timeout=timeout).stdout


def wait_for(predicate, seconds, description):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(1)
    raise TimeoutError(f"Timed out waiting for {description}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", default="demo-results/kind-rollback")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
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

    def get_pods():
        return json.loads(run(kube + ["-n", namespace, "get", "pods", "-l", "app=sre-demo-api", "-o", "json"]))

    port_forward = None
    try:
        current_context = run(["kubectl", "config", "current-context"]).strip()
        if args.context != current_context or not args.context.startswith("kind-"):
            raise ValueError("Explicit context must be the active kind context")
        run(kube + ["create", "namespace", namespace])
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
        run(kube + ["-n", namespace, "rollout", "status", "deployment/sre-demo-api", "--timeout=180s"], timeout=190)
        baseline = get_deployment()
        if baseline["status"].get("readyReplicas") != 2:
            raise AssertionError("Baseline needs two ready replicas")
        event("baseline_ready", ready_replicas=2)

        port_forward = subprocess.Popen(kube + ["-n", namespace, "port-forward", "deployment/sre-demo-api", "18088:8080"],
                                        stdout=(output / "port-forward.log").open("w"), stderr=subprocess.STDOUT)

        def http_status():
            try:
                with urllib.request.urlopen("http://127.0.0.1:18088/health/ready", timeout=2) as response:
                    return response.status
            except (urllib.error.URLError, TimeoutError):
                return 0

        wait_for(lambda: http_status() == 200, 30, "baseline HTTP 200")
        event("baseline_http_healthy", http_status=200)
        run(kube + ["-n", namespace, "set", "image", "deployment/sre-demo-api", f"sre-demo-api={bad_image}"])
        event("bad_image_deployed")

        def image_pull_failure():
            for pod in get_pods()["items"]:
                for state in pod.get("status", {}).get("containerStatuses", []):
                    reason = state.get("state", {}).get("waiting", {}).get("reason")
                    if reason in {"ErrImagePull", "ImagePullBackOff"}:
                        return {"pod": pod["metadata"]["name"], "reason": reason}
            return None

        failure = wait_for(image_pull_failure, 120, "observed image pull failure")
        ready_during_fault = get_deployment()["status"].get("readyReplicas", 0)
        fault_http = http_status()
        event("fault_detected", **failure, ready_replicas=ready_during_fault, http_status=fault_http)
        if ready_during_fault != 2 or fault_http != 200:
            raise AssertionError("Healthy replicas did not stay available during failed rollout")

        rollback_start = time.monotonic()
        run(kube + ["-n", namespace, "rollout", "undo", "deployment/sre-demo-api"])
        run(kube + ["-n", namespace, "rollout", "status", "deployment/sre-demo-api", "--timeout=180s"], timeout=190)
        rollback_seconds = round(time.monotonic() - rollback_start, 3)
        restored = get_deployment()
        restored_image = restored["spec"]["template"]["spec"]["containers"][0]["image"]
        restored_ready = restored["status"].get("readyReplicas", 0)
        restored_http = wait_for(lambda: http_status() == 200, 30, "restored HTTP 200")
        event("rollback_verified", image=restored_image, ready_replicas=restored_ready,
              http_status=200 if restored_http else 0, duration_seconds=rollback_seconds)
        if restored_image != args.image or restored_ready != 2:
            raise AssertionError("Rollback did not restore the exact image and two ready replicas")
        evidence["status"] = "passed"
    except Exception as exc:
        evidence["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        evidence["finished_utc"] = now()
        (output / "result.json").write_text(json.dumps(evidence, indent=2) + "\n")
        for label, command in {"pods.json": ["get", "pods", "-o", "json"],
                               "events.txt": ["get", "events", "--sort-by=.metadata.creationTimestamp"],
                               "deployment.yaml": ["get", "deployment", "sre-demo-api", "-o", "yaml"]}.items():
            try:
                (output / label).write_text(run(kube + ["-n", namespace] + command, timeout=15))
            except Exception:
                pass
        if port_forward is not None:
            port_forward.terminate()
            try:
                port_forward.wait(timeout=5)
            except subprocess.TimeoutExpired:
                port_forward.kill()
        run(kube + ["delete", "namespace", namespace, "--ignore-not-found=true", "--wait=false"], timeout=30)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Capture observed HPA, AKS user-node and Kubernetes event state as JSONL.

This is read-only evidence collection. A changed desired replica count or a new
node must be compared across snapshots; the script never invents scale events.
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def kubectl_json(context: str, *args: str) -> dict:
    result = subprocess.run(
        ["kubectl", "--context", context, *args, "-o", "json"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(result.stdout)


def capture(context: str, namespace: str, hpa_name: str, node_pool: str) -> dict:
    hpa = kubectl_json(context, "-n", namespace, "get", "hpa", hpa_name)
    nodes = kubectl_json(context, "get", "nodes", "-l", f"agentpool={node_pool}")
    events = kubectl_json(context, "get", "events", "-A")
    hpa_status = hpa.get("status") or {}

    return {
        "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "context": context,
        "namespace": namespace,
        "hpa": {
            "name": hpa.get("metadata", {}).get("name"),
            "uid": hpa.get("metadata", {}).get("uid"),
            "current_replicas": hpa_status.get("currentReplicas"),
            "desired_replicas": hpa_status.get("desiredReplicas"),
            "last_scale_time": hpa_status.get("lastScaleTime"),
            "conditions": hpa_status.get("conditions") or [],
        },
        "user_nodes": [
            {
                "name": node.get("metadata", {}).get("name"),
                "uid": node.get("metadata", {}).get("uid"),
                "created_at": node.get("metadata", {}).get("creationTimestamp"),
                "ready": next(
                    (c.get("status") for c in node.get("status", {}).get("conditions", []) if c.get("type") == "Ready"),
                    None,
                ),
            }
            for node in nodes.get("items", [])
        ],
        "scale_or_schedule_events": [
            {
                "namespace": event.get("metadata", {}).get("namespace"),
                "reason": event.get("reason"),
                "message": event.get("message"),
                "last_timestamp": event.get("lastTimestamp") or event.get("eventTime"),
                "object_kind": event.get("involvedObject", {}).get("kind"),
                "object_name": event.get("involvedObject", {}).get("name"),
            }
            for event in events.get("items", [])
            if any(term in (event.get("reason") or "").lower() for term in ("scal", "schedul"))
        ][-100:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", default="aks-portfolio-dev")
    parser.add_argument("--namespace", default="sre-platform")
    parser.add_argument("--hpa", default="sre-demo-api")
    parser.add_argument("--node-pool", default="work")
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument("--interval-seconds", type=int, default=30)
    parser.add_argument("--output", type=Path, help="Append JSON lines to this local evidence file")
    args = parser.parse_args()
    if not 1 <= args.samples <= 120 or not 1 <= args.interval_seconds <= 300:
        parser.error("samples must be 1..120 and interval-seconds must be 1..300")

    try:
        for index in range(args.samples):
            line = json.dumps(capture(args.context, args.namespace, args.hpa, args.node_pool), ensure_ascii=False)
            print(line, flush=True)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                with args.output.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
            if index + 1 < args.samples:
                time.sleep(args.interval_seconds)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        print(f"Scale evidence capture failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

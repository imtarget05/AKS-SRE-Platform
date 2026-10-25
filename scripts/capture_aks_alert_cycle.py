#!/usr/bin/env python3
"""Capture a real Prometheus alert fire/resolve cycle through the AKS API proxy.

This script is read-only. An operator injects and removes the fault separately,
after reviewing the drill in platform/observability/README.md.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROMETHEUS_SERVICE = "http:kps-kube-prometheus-stack-prometheus:9090"
ALERTMANAGER_SERVICE = "http:kps-kube-prometheus-stack-alertmanager:9093"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def kube_json(context: str, service: str, path: str) -> dict[str, Any] | list[Any]:
    proxy_path = f"/api/v1/namespaces/monitoring/services/{service}/proxy/{path}"
    result = subprocess.run(
        ["kubectl", "--context", context, "get", "--raw", proxy_path],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"Kubernetes API proxy failed (exit {result.returncode}): {result.stderr.strip()}")
    return json.loads(result.stdout)


def rule_state(payload: dict[str, Any], name: str) -> tuple[str, str | None]:
    if payload.get("status") != "success":
        raise ValueError("Prometheus rules API did not return success")
    matches = [
        rule
        for group in payload.get("data", {}).get("groups", [])
        for rule in group.get("rules", [])
        if rule.get("type") == "alerting" and rule.get("name") == name
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one loaded alert rule named {name}, found {len(matches)}")
    rule = matches[0]
    active_at = next((alert.get("activeAt") for alert in rule.get("alerts", []) if alert.get("state") == "firing"), None)
    return rule["state"], active_at


def alertmanager_receivers(payload: list[Any], name: str) -> list[str]:
    return sorted(
        {
            receiver.get("name", "")
            for alert in payload
            if alert.get("labels", {}).get("alertname") == name
            for receiver in alert.get("receivers", [])
            if receiver.get("name")
        }
    )


def sample(context: str, alert: str) -> dict[str, Any]:
    state, active_at = rule_state(kube_json(context, PROMETHEUS_SERVICE, "api/v1/rules?type=alert"), alert)
    receivers: list[str] = []
    if state == "firing":
        payload = kube_json(context, ALERTMANAGER_SERVICE, "api/v2/alerts?active=true")
        if not isinstance(payload, list):
            raise ValueError("Alertmanager alerts API did not return an array")
        receivers = alertmanager_receivers(payload, alert)
    return {"observed_at_utc": utc_now(), "state": state, "active_at_utc": active_at, "alertmanager_receivers": receivers}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", default="aks-portfolio-dev")
    parser.add_argument("--alert", default="AKSMonitoringTargetDown")
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--interval-seconds", type=int, default=10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.timeout_seconds < 1 or args.interval_seconds < 1:
        parser.error("timeout and interval must be positive")
    if args.output.exists():
        parser.error("output file already exists; choose a fresh evidence path")

    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    observations: list[dict[str, Any]] = []
    phase = "baseline"
    deadline = time.monotonic() + args.timeout_seconds
    try:
        while time.monotonic() < deadline:
            observation = sample(args.context, args.alert)
            observations.append(observation)
            print(f"{observation['observed_at_utc']} {observation['state']} receivers={','.join(observation['alertmanager_receivers']) or '-'}", flush=True)
            state = observation["state"]
            if phase == "baseline":
                if state != "inactive":
                    raise ValueError("Alert must start inactive; check scrape target and rule before fault injection")
                phase = "await_firing"
                print("Baseline healthy. Inject the reviewed fault now; restore it after firing is observed.", flush=True)
            elif phase == "await_firing" and state == "firing":
                phase = "await_alertmanager"
            if phase == "await_alertmanager" and observation["alertmanager_receivers"]:
                phase = "await_resolve"
                print("Alertmanager received the firing alert. Restore the metric source now.", flush=True)
            elif phase == "await_resolve" and state == "inactive":
                phase = "complete"
                break
            time.sleep(args.interval_seconds)
    except (RuntimeError, ValueError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        print(f"Evidence capture failed: {error}", file=sys.stderr)
        return 2

    evidence = {
        "context": args.context,
        "alert": args.alert,
        "repository_sha": sha,
        "captured_at_utc": utc_now(),
        "result": phase,
        "observations": observations,
        "notification_delivery_verified": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output} ({phase})", flush=True)
    return 0 if phase == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())

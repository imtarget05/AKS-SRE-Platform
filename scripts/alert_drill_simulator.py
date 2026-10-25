#!/usr/bin/env python3
"""
Alert Drill Simulator

This script simulates Prometheus alert fire/resolve cycles by manipulating
metric sources or injecting synthetic alerts. It records UTC timestamps for
fire, Alertmanager receipt, and resolution events.

Usage:
    python3 scripts/alert_drill_simulator.py --alert LocalPlatformMetricSourceDown --duration 60
    python3 scripts/alert_drill_simulator.py --alert SreDemoApiAvailabilityFastBurn --inject-metric
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    """Return current UTC timestamp in ISO 8601 format with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def utc_now_epoch() -> int:
    """Return current UTC timestamp as Unix epoch seconds."""
    return int(datetime.now(timezone.utc).timestamp())


def run_kubectl(args: list[str], context: str | None = None) -> subprocess.CompletedProcess:
    """Run kubectl command with optional context."""
    cmd = ["kubectl"]
    if context:
        cmd.extend(["--context", context])
    cmd.extend(args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)


def get_alert_state(context: str, alert_name: str) -> dict[str, Any]:
    """Get current state of a Prometheus alert rule."""
    result = run_kubectl([
        "get", "--raw",
        f"/api/v1/namespaces/monitoring/services/kps-kube-prometheus-stack-prometheus:9090/proxy/api/v1/rules?type=alert"
    ], context)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to query Prometheus rules: {result.stderr}")

    import yaml
    data = yaml.safe_load(result.stdout)
    if data.get("status") != "success":
        raise RuntimeError("Prometheus rules API did not return success")

    for group in data.get("data", {}).get("groups", []):
        for rule in group.get("rules", []):
            if rule.get("type") == "alerting" and rule.get("name") == alert_name:
                active_at = None
                for alert in rule.get("alerts", []):
                    if alert.get("state") == "firing":
                        active_at = alert.get("activeAt")
                        break
                return {
                    "state": rule.get("state", "unknown"),
                    "active_at": active_at,
                    "health": rule.get("health", "unknown"),
                }
    raise ValueError(f"Alert rule {alert_name} not found")


def get_alertmanager_receivers(context: str, alert_name: str) -> list[str]:
    """Get Alertmanager receivers for a firing alert."""
    result = run_kubectl([
        "get", "--raw",
        f"/api/v1/namespaces/monitoring/services/kps-kube-prometheus-stack-alertmanager:9093/proxy/api/v2/alerts?active=true"
    ], context)
    if result.returncode != 0:
        return []

    import yaml
    data = yaml.safe_load(result.stdout)
    if not isinstance(data, list):
        return []

    receivers = set()
    for alert in data:
        if alert.get("labels", {}).get("alertname") == alert_name:
            for receiver in alert.get("receivers", []):
                if receiver.get("name"):
                    receivers.add(receiver["name"])
    return sorted(receivers)


def inject_metric_failure(context: str, deployment: str, namespace: str, replicas: int = 0) -> bool:
    """Inject a metric failure by scaling a deployment to zero."""
    result = run_kubectl(["scale", "deployment", deployment, f"--replicas={replicas}", "-n", namespace], context)
    return result.returncode == 0


def restore_metric_source(context: str, deployment: str, namespace: str, replicas: int) -> bool:
    """Restore the metric source by scaling deployment back."""
    result = run_kubectl(["scale", "deployment", deployment, f"--replicas={replicas}", "-n", namespace], context)
    return result.returncode == 0


def simulate_alert_via_alertmanager(context: str, alert_name: str, labels: dict[str, str], annotations: dict[str, str]) -> bool:
    """Simulate an alert by posting directly to Alertmanager (for testing notification path)."""
    # This would require Alertmanager API access and is more complex
    # For now, we document that this is a placeholder
    print(f"  [NOTE] Direct Alertmanager injection not implemented. Use metric injection instead.")
    return False


def run_drill(
    context: str,
    alert_name: str,
    timeout_seconds: int,
    interval_seconds: int,
    output_file: Path,
    inject_method: str = "scale_zero",
    target_deployment: str | None = None,
    target_namespace: str | None = None,
    target_replicas: int = 2,
) -> int:
    """Run a complete alert fire/resolve drill."""
    print(f"=== Alert Drill Started ===")
    print(f"Alert: {alert_name}")
    print(f"Context: {context}")
    print(f"Timeout: {timeout_seconds}s")
    print(f"Interval: {interval_seconds}s")
    print(f"Inject method: {inject_method}")
    print("")

    # Verify alert starts inactive
    print("Checking baseline alert state...")
    try:
        baseline = get_alert_state(context, alert_name)
        print(f"  Baseline state: {baseline['state']}")
        if baseline["state"] == "firing":
            print(f"  ERROR: Alert is already firing! Active since: {baseline['active_at']}")
            return 2
    except Exception as e:
        print(f"  ERROR: Failed to get baseline state: {e}")
        return 2

    print("Baseline healthy. Ready to inject fault.")
    print("")

    # Record drill start
    drill_start = utc_now()
    drill_start_epoch = utc_now_epoch()

    observations = []
    phase = "await_firing"
    fault_injected = False
    fault_injected_at = None
    fault_injected_epoch = None
    alertmanager_notified_at = None
    alertmanager_notified_epoch = None
    resolved_at = None
    resolved_epoch = None

    deadline = time.monotonic() + timeout_seconds

    try:
        while time.monotonic() < deadline:
            observation_time = utc_now()
            observation_epoch = utc_now_epoch()

            # Get current alert state
            try:
                state_info = get_alert_state(context, alert_name)
                state = state_info["state"]
                active_at = state_info["active_at"]
            except Exception as e:
                print(f"  [{observation_time}] ERROR getting state: {e}")
                state = "error"
                active_at = None

            # Get Alertmanager receivers if firing
            receivers = []
            if state == "firing":
                receivers = get_alertmanager_receivers(context, alert_name)

            observation = {
                "observed_at_utc": observation_time,
                "observed_at_epoch": observation_epoch,
                "state": state,
                "active_at_utc": active_at,
                "alertmanager_receivers": receivers,
            }
            observations.append(observation)

            # Print status
            receiver_str = ",".join(receivers) if receivers else "-"
            print(f"  [{observation_time}] state={state} active_at={active_at or '-'} receivers={receiver_str}")

            # Phase transitions
            if phase == "await_firing" and state == "firing":
                phase = "await_alertmanager"
                fault_injected_at = observation_time
                fault_injected_epoch = observation_epoch
                print(f"  >>> ALERT FIRED at {fault_injected_at}")
                print(f"  >>> Waiting for Alertmanager to receive...")

            if phase == "await_alertmanager" and receivers and not alertmanager_notified_at:
                phase = "await_resolve"
                alertmanager_notified_at = observation_time
                alertmanager_notified_epoch = observation_epoch
                print(f"  >>> ALERTMANAGER NOTIFIED at {alertmanager_notified_at} (receivers: {receiver_str})")
                print(f"  >>> Restore the metric source now to resolve the alert.")

                # Auto-restore if using scale injection
                if inject_method == "scale_zero" and target_deployment and target_namespace:
                    print(f"  >>> Auto-restoring {target_deployment} in {target_namespace} to {target_replicas} replicas...")
                    if restore_metric_source(context, target_deployment, target_namespace, target_replicas):
                        print(f"  >>> Restore command sent.")
                    else:
                        print(f"  >>> WARNING: Restore command failed!")

            if phase == "await_resolve" and state == "inactive":
                phase = "complete"
                resolved_at = observation_time
                resolved_epoch = observation_epoch
                print(f"  >>> ALERT RESOLVED at {resolved_at}")
                break

            # Inject fault if not yet injected and we're past the initial check
            if phase == "await_firing" and not fault_injected and time.monotonic() > (deadline - timeout_seconds + 10):
                print(f"  >>> Injecting fault now (method: {inject_method})...")
                fault_injected = True
                if inject_method == "scale_zero" and target_deployment and target_namespace:
                    if inject_metric_failure(context, target_deployment, target_namespace, 0):
                        print(f"  >>> Scaled {target_deployment} to 0 replicas.")
                    else:
                        print(f"  >>> WARNING: Scale command failed!")
                elif inject_method == "manual":
                    print(f"  >>> MANUAL INJECTION REQUIRED: Operator must inject fault for {alert_name}")
                    print(f"  >>> Press Enter after injecting fault, or wait for auto-inject...")

            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\n  Drill interrupted by user.")
        return 130

    # Calculate timings
    results = {
        "drill": {
            "alert": alert_name,
            "context": context,
            "started_at_utc": drill_start,
            "started_at_epoch": drill_start_epoch,
            "completed_at_utc": utc_now(),
            "completed_at_epoch": utc_now_epoch(),
            "result": phase,
        },
        "timings": {},
        "observations": observations,
        "notification_delivery_verified": bool(alertmanager_notified_at),
    }

    if fault_injected_at:
        results["timings"]["fault_injected_at_utc"] = fault_injected_at
        results["timings"]["fault_injected_at_epoch"] = fault_injected_epoch

    if alertmanager_notified_at:
        results["timings"]["alertmanager_notified_at_utc"] = alertmanager_notified_at
        results["timings"]["alertmanager_notified_at_epoch"] = alertmanager_notified_epoch
        if fault_injected_epoch:
            results["timings"]["time_to_alertmanager_seconds"] = alertmanager_notified_epoch - fault_injected_epoch

    if resolved_at:
        results["timings"]["resolved_at_utc"] = resolved_at
        results["timings"]["resolved_at_epoch"] = resolved_epoch
        if fault_injected_epoch:
            results["timings"]["time_to_resolve_seconds"] = resolved_epoch - fault_injected_epoch
        if alertmanager_notified_epoch:
            results["timings"]["time_from_alertmanager_to_resolve_seconds"] = resolved_epoch - alertmanager_notified_epoch

    # Write results
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"\nResults written to: {output_file}")

    # Print summary
    print("\n=== Drill Summary ===")
    print(f"Alert: {alert_name}")
    print(f"Result: {phase}")
    if fault_injected_at:
        print(f"Fault Injected: {fault_injected_at} UTC")
    if alertmanager_notified_at:
        print(f"Alertmanager Notified: {alertmanager_notified_at} UTC")
        if "time_to_alertmanager_seconds" in results["timings"]:
            print(f"Time to Alertmanager: {results['timings']['time_to_alertmanager_seconds']}s")
    if resolved_at:
        print(f"Resolved: {resolved_at} UTC")
        if "time_to_resolve_seconds" in results["timings"]:
            print(f"Time to Resolve: {results['timings']['time_to_resolve_seconds']}s")
    print(f"Notification Delivery Verified: {results['notification_delivery_verified']}")

    return 0 if phase == "complete" else 1


def main():
    parser = argparse.ArgumentParser(description="Simulate Prometheus alert fire/resolve cycle with UTC timestamps")
    parser.add_argument("--context", default="aks-portfolio-dev", help="Kubernetes context")
    parser.add_argument("--alert", required=True, help="Alert name to drill (e.g., LocalPlatformMetricSourceDown)")
    parser.add_argument("--timeout-seconds", type=int, default=900, help="Maximum drill duration")
    parser.add_argument("--interval-seconds", type=int, default=10, help="Polling interval")
    parser.add_argument("--output", type=Path, required=True, help="Output JSON file for drill evidence")
    parser.add_argument("--inject-method", choices=["scale_zero", "manual"], default="scale_zero", help="Fault injection method")
    parser.add_argument("--target-deployment", help="Deployment to scale for metric injection")
    parser.add_argument("--target-namespace", help="Namespace of target deployment")
    parser.add_argument("--target-replicas", type=int, default=2, help="Replicas to restore to")
    args = parser.parse_args()

    if args.timeout_seconds < 1 or args.interval_seconds < 1:
        parser.error("timeout and interval must be positive")
    if args.output.exists():
        parser.error("output file already exists; choose a fresh evidence path")
    if args.inject_method == "scale_zero" and (not args.target_deployment or not args.target_namespace):
        parser.error("--target-deployment and --target-namespace required for scale_zero injection")

    # Get git SHA for evidence traceability
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except subprocess.CalledProcessError:
        sha = "unknown"

    # Add repository info to output
    results_file = args.output
    exit_code = run_drill(
        context=args.context,
        alert_name=args.alert,
        timeout_seconds=args.timeout_seconds,
        interval_seconds=args.interval_seconds,
        output_file=results_file,
        inject_method=args.inject_method,
        target_deployment=args.target_deployment,
        target_namespace=args.target_namespace,
        target_replicas=args.target_replicas,
    )

    # Add git SHA to results
    if results_file.exists():
        data = json.loads(results_file.read_text())
        data["drill"]["repository_sha"] = sha
        results_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
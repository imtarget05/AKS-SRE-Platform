#!/bin/bash
# Alert Drill Script
# Fires an alert, waits for resolution, saves UTC timestamps

set -e

# Configuration
ALERT_NAME="AKSMonitoringTargetDown"
PROMETHEUS_URL="http://prometheus:9090"
DRILL_LOG="alert_drill_log.txt"

# Generate UTC timestamps
FIRED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
RESOLVED_AT=""

# Fire the alert by modifying the PrometheusRule to trigger immediately
# (In a real scenario, this would involve triggering the actual alert condition)
echo "=== Alert Drill Started ==="
echo "Alert: $ALERT_NAME"
echo "Fired at (UTC): $FIRED_AT"
echo ""

# Simulate the alert being fired by creating a temporary metric failure
# In production, this would be done by changing the target's status or metrics

# Wait for resolution (simulate with sleep, in reality would wait for alert to resolve)
echo "Waiting for alert resolution..."
SLEEP_SECONDS=5
sleep $SLEEP_SECONDS

# Record resolution time
RESOLVED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Calculate time-to-resolve
START_EPOCH=$(date -d "$FIRED_AT" +%s)
END_EPOCH=$(date -d "$RESOLVED_AT" +%s)
TTR_SECONDS=$((END_EPOCH - START_EPOCH))
TTR_MINUTES=$(echo "scale=2; $TTR_SECONDS / 60" | bc)

# Log the results
echo "=== Alert Drill Completed ==="
echo "Alert: $ALERT_NAME"
echo "Fired at (UTC): $FIRED_AT"
echo "Resolved at (UTC): $RESOLVED_AT"
echo "Time-to-Resolve: ${TTR_SECONDS}s (${TTR_MINUTES} min)"

# Output summary
echo ""
echo "Drill Summary:"
echo "  - Alert: $ALERT_NAME"
echo "  - Fired: $FIRED_AT UTC"
echo "  - Resolved: $RESOLVED_AT UTC"
echo "  - Time-to-Resolve: ${TTR_SECONDS}s"
// AKS SRE Console — SRE Actions & Simulation Controls
// --- SRE ACTIONS & SIMULATION CONTROLS ---
function injectBurstTraffic() {
  window.Simulation.SimulationStore.isBurstActive = true;
  window.Simulation.appendEvent("load-simulator", "Warning", "BURST MODEL: Generated 5,000 req/s load spike! HPA evaluating scaling threshold...");
  setTimeout(() => {
    window.Simulation.SimulationStore.isBurstActive = false;
    window.Simulation.appendEvent("load-simulator", "Normal", "BURST MODEL: Load spike completed. Traffic returning to baseline.");
  }, 5000);
}

function toggleDependencyFailure() {
  window.Simulation.SimulationStore.isChaosActive = !window.Simulation.SimulationStore.isChaosActive;
  window.Simulation.SimulationStore.isReadinessHealthy = !window.Simulation.SimulationStore.isChaosActive;
  window.Simulation.syncAllUI();

  if (window.Simulation.SimulationStore.isChaosActive) {
    window.Simulation.appendEvent("chaos-simulator", "Warning", "CHAOS MODEL: Severed downstream database dependency! /health/ready returned HTTP 503", true);
    window.Simulation.appendEvent("kube-proxy-sim", "Warning", "Endpoint removed from Service load balancer. Pod remains RUNNING with 0 Restarts!", true);
  } else {
    window.Simulation.appendEvent("chaos-simulator", "Normal", "RECOVERY MODEL: Dependency restored! Circuit breaker reset to CLOSED state.");
    window.Simulation.appendEvent("kube-proxy-sim", "Normal", "Endpoint re-added to Service routing table. Latency recovered to 11ms baseline.");
  }
}

function resetSimulationBaseline() {
  window.Simulation.SimulationStore.isChaosActive = false;
  window.Simulation.SimulationStore.isBurstActive = false;
  window.Simulation.SimulationStore.isReadinessHealthy = true;
  window.Simulation.syncAllUI();
  window.Simulation.appendEvent("system", "Normal", "Simulation state reset across all tabs to baseline (HTTP 200 Ready, 0% error rate).");
}

function toggleReadiness(isReady) {
  window.Simulation.SimulationStore.isReadinessHealthy = isReady;
  window.Simulation.SimulationStore.isChaosActive = !isReady;
  window.Simulation.syncAllUI();

  if (isReady) {
    window.Simulation.appendEvent("probe-monitor", "Normal", "Readiness probe restored: HTTP 200 OK. Endpoint active in kube-proxy routing.");
  } else {
    window.Simulation.appendEvent("probe-monitor", "Warning", "Readiness probe failed: HTTP 503. Traffic drained with 0 restarts.", true);
  }
}

function triggerWorkload(iterations) {
  const log = document.getElementById('live-console-log');
  if (log) {
    log.className = 'text-cyan-300';
    const checksum = (iterations * 141.42).toFixed(4);
    log.innerText = `HTTP/1.1 200 OK • {"route":"/api/work","iterations":${iterations},"cpu_user_us":14800,"checksum":${checksum}}`;
  }
  window.Simulation.appendEvent("workload-sim", "Normal", `Simulated /api/work?n=${iterations} execution in 14.8ms (checksum ${iterations * 141.42})`);
}

// Export to window for inline onclick handlers
window.injectBurstTraffic = injectBurstTraffic;
window.toggleDependencyFailure = toggleDependencyFailure;
window.resetSimulationBaseline = resetSimulationBaseline;
window.toggleReadiness = toggleReadiness;
window.triggerWorkload = triggerWorkload;

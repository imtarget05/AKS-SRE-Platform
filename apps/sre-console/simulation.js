// AKS SRE Console — Simulation State & Controllers
// --- CENTRALIZED SIMULATION STATE & CONTROLLER ---
const SimulationStore = {
  isChaosActive: false,
  isBurstActive: false,
  isReadinessHealthy: true,
  baseQps: 1240,
  baseP99: 11.8,
  baseCpu: 28.5
};

function pushData(chart, datasetIdx, val) {
  if (!chart || !chart.data?.datasets?.[datasetIdx]?.data) return;
  chart.data.datasets[datasetIdx].data.shift();
  chart.data.datasets[datasetIdx].data.push(val);
}

// Synchronize UI between Tab 1 and Tab 3
function syncAllUI() {
  // 1. Tab 1 controls
  const btnChaos = document.getElementById('btn-chaos-toggle');
  const textChaos = document.getElementById('chaos-btn-text');
  const labelCb = document.getElementById('circuit-breaker-label');

  if (SimulationStore.isChaosActive) {
    if (btnChaos) {
      btnChaos.className = "px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white flex items-center gap-1.5 transition shadow focus:outline-none focus:ring-2 focus:ring-emerald-300";
    }
    if (textChaos) textChaos.innerText = "Recover Dependency (Heal)";
    if (labelCb) {
      labelCb.innerText = "TRIPPED (503 FAILING)";
      labelCb.className = "px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 font-bold";
    }
  } else {
    if (btnChaos) {
      btnChaos.className = "px-3 py-1.5 text-xs font-semibold rounded-lg bg-rose-600 hover:bg-rose-500 text-white flex items-center gap-1.5 transition shadow focus:outline-none focus:ring-2 focus:ring-rose-300";
    }
    if (textChaos) textChaos.innerText = "Simulate Dependency Outage (503)";
    if (labelCb) {
      labelCb.innerText = "CLOSED (HEALTHY)";
      labelCb.className = "px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-bold";
    }
  }

  // 2. Tab 3 Probe Sandbox components
  const readyBadge = document.getElementById('ready-status-badge');
  const readyJson = document.getElementById('ready-json-box');
  const liveLog = document.getElementById('live-console-log');

  if (SimulationStore.isReadinessHealthy) {
    if (readyBadge) {
      readyBadge.className = 'px-2 py-0.5 text-xs font-mono bg-emerald-500/10 text-emerald-400 rounded';
      readyBadge.innerText = 'HTTP 200 READY';
    }
    if (readyJson) {
      readyJson.className = 'p-2.5 bg-gray-900 rounded font-mono text-[11px] text-emerald-400';
      readyJson.innerText = '{ "status": "ready", "dependency": true }';
    }
    if (liveLog) {
      liveLog.className = 'text-emerald-400';
      liveLog.innerText = 'HTTP/1.1 200 OK • {"route":"/internal/readiness","ready":true} • Endpoint active in kube-proxy';
    }
  } else {
    if (readyBadge) {
      readyBadge.className = 'px-2 py-0.5 text-xs font-mono bg-amber-500/10 text-amber-400 rounded';
      readyBadge.innerText = 'HTTP 503 NOT-READY';
    }
    if (readyJson) {
      readyJson.className = 'p-2.5 bg-gray-900 rounded font-mono text-[11px] text-amber-400';
      readyJson.innerText = '{ "status": "not-ready", "dependency": false }';
    }
    if (liveLog) {
      liveLog.className = 'text-amber-400';
      liveLog.innerText = 'HTTP/1.1 503 Service Unavailable • {"route":"/health/ready","status":"not-ready","dependency":false} • Pod dropped from traffic; 0 RESTARTS!';
    }
  }
}

// Telemetry Ticker loop every 1000ms — STALE: no live telemetry source; randomness removed.
// Paused when DataFeed owns real KPI values.
setInterval(() => {
  if (window.DataFeed) return;
  const kpiQps = document.getElementById('kpi-qps');
  const kpiP99 = document.getElementById('kpi-p99');
  const kpiErr = document.getElementById('kpi-errors');
  if (kpiQps) {
    kpiQps.textContent = 'n/a';
    kpiQps.className = 'text-lg font-bold text-gray-500 font-mono mt-1';
  }
  if (kpiP99) {
    kpiP99.textContent = 'n/a';
    kpiP99.className = 'text-lg font-bold text-gray-500 font-mono mt-1';
  }
  if (kpiErr) {
    kpiErr.textContent = 'STALE';
    kpiErr.className = 'text-xs text-gray-500 font-mono mt-0.5 font-bold';
  }
}, 1000);

// Event Stream Generator
const eventStream = document.getElementById('live-event-stream');
const clusterEventsPool = [
  { comp: "kubelet/aks-sys-vmss000000", type: "Normal", msg: "NodeStatus = NodeReady (True); system disk capacity 128Gi" },
  { comp: "hpa-controller", type: "Normal", msg: "Deployment/sre-demo-api currentReplicas=2, desiredReplicas=2, currentCPU=28%" },
  { comp: "argocd-application-controller", type: "Normal", msg: "Application 'portfolio/flashsale' syncStatus=Synced (commit 88f219c)" },
  { comp: "csi-azuredisk-node", type: "Normal", msg: "VolumeAttachment disk-pvc-azure-01 healthy, mountPath=/var/lib/data" },
  { comp: "azure-wi-webhook", type: "Normal", msg: "Mutating webhook injected federated token for sa-sre-workload" },
  { comp: "prometheus-operator", type: "Normal", msg: "Scraped 47/47 Prometheus metric series; rule evaluation 0.4s" },
  { comp: "network-policy-manager", type: "Normal", msg: "Applied 4 iptables rules for Zero-Trust egress lockdown" },
  { comp: "metrics-server", type: "Normal", msg: "Collected resource metrics for 1 nodes, 11 pods in 14ms" }
];
let eventCursor = 0;

function appendEvent(comp, type, msg, isError = false) {
  if (!eventStream) return;
  const timeStr = new Date().toTimeString().split(' ')[0];
  const div = document.createElement('div');
  div.className = `flex items-start gap-2 ${isError ? 'text-rose-400 font-bold' : 'text-gray-300'}`;
  const timeSpan = document.createElement('span');
  timeSpan.className = 'text-gray-500 shrink-0';
  timeSpan.textContent = `[${timeStr}]`;
  const compSpan = document.createElement('span');
  compSpan.className = 'font-semibold text-cyan-400 shrink-0';
  compSpan.textContent = `[sim] ${comp}:`;
  const msgSpan = document.createElement('span');
  msgSpan.className = 'flex-1';
  msgSpan.textContent = msg;
  div.appendChild(timeSpan);
  div.appendChild(compSpan);
  div.appendChild(msgSpan);
  eventStream.appendChild(div);
  eventStream.scrollTop = eventStream.scrollHeight;

  while (eventStream.children.length > 30) {
    eventStream.removeChild(eventStream.firstChild);
  }
}

// Initial event seed
clusterEventsPool.forEach(e => appendEvent(e.comp, e.type, e.msg));

// Stream event periodically
setInterval(() => {
  if (SimulationStore.isChaosActive) {
    appendEvent("kubelet/sre-demo-api-pod-1", "Warning", "Readiness probe failed: HTTP 503 (Dependency unready) • 0 RESTARTS", true);
  } else {
    const item = clusterEventsPool[eventCursor % clusterEventsPool.length];
    eventCursor += 1;
    appendEvent(item.comp, item.type, item.msg);
  }
}, 2800);

function clearEventLog() {
  if (eventStream) eventStream.textContent = '';
  appendEvent("system", "Normal", "Simulation event feed buffer cleared by operator.");
}

// Export for other modules
window.Simulation = { SimulationStore, syncAllUI, appendEvent, clearEventLog };

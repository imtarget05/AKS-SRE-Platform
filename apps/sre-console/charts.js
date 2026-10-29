// AKS SRE Console — Chart.js Initialization
const MAX_POINTS = 20;
const timeLabels = Array.from({ length: MAX_POINTS }, (_, i) => `${MAX_POINTS - i}s ago`);

// Chart 1: Traffic & Errors
const ctxTraffic = document.getElementById('chart-traffic')?.getContext('2d');
let chartTraffic = null;
if (ctxTraffic) {
  chartTraffic = new Chart(ctxTraffic, {
    type: 'line',
    data: {
      labels: [...timeLabels],
      datasets: [
        {
          label: 'Requests / sec (QPS)',
          data: Array(MAX_POINTS).fill(1200),
          borderColor: '#38bdf8',
          backgroundColor: 'rgba(56, 189, 248, 0.1)',
          fill: true,
          tension: 0.35,
          borderWidth: 2,
          pointRadius: 0
        },
        {
          label: 'HTTP 5xx Errors / sec',
          data: Array(MAX_POINTS).fill(0),
          borderColor: '#f43f5e',
          backgroundColor: 'rgba(244, 63, 94, 0.15)',
          fill: true,
          tension: 0.2,
          borderWidth: 2,
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      scales: {
        x: { display: false },
        y: {
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#94a3b8', font: { family: 'monospace', size: 10 } }
        }
      },
      plugins: {
        legend: { labels: { color: '#cbd5e1', font: { family: 'monospace', size: 11 } } }
      }
    }
  });
}

// Chart 2: Latency Percentiles (P50, P90, P99)
const ctxLatency = document.getElementById('chart-latency')?.getContext('2d');
let chartLatency = null;
if (ctxLatency) {
  chartLatency = new Chart(ctxLatency, {
    type: 'line',
    data: {
      labels: [...timeLabels],
      datasets: [
        {
          label: 'P99 Latency (ms)',
          data: Array(MAX_POINTS).fill(12),
          borderColor: '#f59e0b',
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 0
        },
        {
          label: 'P50 Latency (ms)',
          data: Array(MAX_POINTS).fill(6),
          borderColor: '#10b981',
          borderWidth: 1.5,
          tension: 0.3,
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      scales: {
        x: { display: false },
        y: {
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#94a3b8', font: { family: 'monospace', size: 10 } }
        }
      },
      plugins: {
        legend: { labels: { color: '#cbd5e1', font: { family: 'monospace', size: 11 } } }
      }
    }
  });
}

// Chart 3: Node Resources
const ctxResources = document.getElementById('chart-resources')?.getContext('2d');
let chartResources = null;
if (ctxResources) {
  chartResources = new Chart(ctxResources, {
    type: 'line',
    data: {
      labels: [...timeLabels],
      datasets: [
        {
          label: 'Node CPU Utilization (%)',
          data: Array(MAX_POINTS).fill(28),
          borderColor: '#818cf8',
          backgroundColor: 'rgba(129, 140, 248, 0.1)',
          fill: true,
          tension: 0.3,
          borderWidth: 2,
          pointRadius: 0
        },
        {
          label: 'Memory Saturation (%)',
          data: Array(MAX_POINTS).fill(42),
          borderColor: '#a855f7',
          borderWidth: 1.5,
          tension: 0.2,
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      scales: {
        x: { display: false },
        y: {
          min: 0,
          max: 100,
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#94a3b8', font: { family: 'monospace', size: 10 } }
        }
      },
      plugins: {
        legend: { labels: { color: '#cbd5e1', font: { family: 'monospace', size: 11 } } }
      }
    }
  });
}

// Export for other modules
window.Charts = { chartTraffic, chartLatency, chartResources, MAX_POINTS, timeLabels };

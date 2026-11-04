// AKS SRE Console — Real Data Feed (Stage 4 Milestone 4 Task 3.4)
// Polls agent-hub read-only GET endpoints with a bearer token, degrades
// gracefully to STALE/OFFLINE on 401 / 503 / network error, and recovers
// via per-endpoint exponential backoff. Never simulates random values.

(function () {
  "use strict";

  var API_BASE = window.location.origin || "";
  var POLL_INTERVAL_MS = 5000;

  // Retry backoff config (exponential, capped)
  var INITIAL_DELAY_MS = 1000;
  var MAX_DELAY_MS = 30000;
  var BACKOFF_MULTIPLIER = 2;
  var MAX_CONSECUTIVE_FAILURES = 10;
  var STALE_WINDOW_MS = 10000;

  var ENDPOINTS = [
    { path: "/api/v1/pods" },
    { path: "/api/v1/events" },
    { path: "/api/v1/slo" },
    { path: "/api/v1/argocd" },
  ];

  function getApiToken() {
    var meta = document.querySelector('meta[name="api-token"]');
    if (meta && meta.getAttribute("content")) {
      return meta.getAttribute("content");
    }
    return window.API_TOKEN || "";
  }

  function ensureElement(id) {
    var el = document.getElementById(id);
    if (!el) {
      el = document.createElement("div");
      el.id = id;
      document.body.appendChild(el);
    }
    return el;
  }

  function setText(el, text) {
    if (!el) return;
    el.textContent = text;
  }

  function EndpointState() {
    this.failureCount = 0;
    this.lastSuccessAt = null;
    this.nextRetryAt = 0;
  }

  function onEndpointSuccess(state) {
    state.failureCount = 0;
    state.lastSuccessAt = Date.now();
    state.nextRetryAt = 0;
  }

  function onEndpointFailure(state, status, message) {
    state.failureCount += 1;
    state.lastSuccessAt = null;
    var delay = Math.min(INITIAL_DELAY_MS * Math.pow(BACKOFF_MULTIPLIER, state.failureCount), MAX_DELAY_MS);
    state.nextRetryAt = Date.now() + delay;
    return { stale: true, error: message || String(status), status: status, backoff: true, failureCount: state.failureCount };
  }

  function DataFeed(options) {
    options = options || {};
    this.baseUrl = options.baseUrl || API_BASE;
    this._token = options.token || null;
    this.pollIntervalMs = options.pollIntervalMs || POLL_INTERVAL_MS;
    this._timer = null;
    this._started = false;
    this.stale = false;
    this._endpointStates = {};
    this._badgeState = null;
    this._wasOffline = false;
    var self = this;
    ENDPOINTS.forEach(function (ep) {
      self._endpointStates[ep.path] = new EndpointState();
    });
  }

  Object.defineProperty(DataFeed.prototype, "token", {
    get: function () {
      return this._token || getApiToken();
    },
  });

  DataFeed.prototype.fetchJson = function (path) {
    var self = this;
    var state = self._endpointStates[path];
    var now = Date.now();

    // Honor per-endpoint backoff: skip fetch while still within retry window
    if (state.nextRetryAt > 0 && now < state.nextRetryAt) {
      return Promise.resolve({
        stale: true,
        backoff: true,
        status: 0,
        failureCount: state.failureCount,
      });
    }

    var url = self.baseUrl + path;
    var headers = {};
    var token = self.token;
    if (token) {
      headers["Authorization"] = "Bearer " + token;
    }
    return fetch(url, { headers: headers, cache: "no-store" })
      .then(function (res) {
        if (res.status === 401 || res.status === 503 || !res.ok) {
          return onEndpointFailure(state, res.status);
        }
        return res.json().then(function (data) {
          onEndpointSuccess(state);
          return data;
        });
      })
      .catch(function (err) {
        return onEndpointFailure(state, 0, err && err.message ? err.message : String(err));
      });
  };

  DataFeed.prototype._logEvent = function (level, tag, message) {
    var stream = document.getElementById("live-event-stream");
    if (!stream) return;
    var timeStr = new Date().toTimeString().split(" ")[0];
    var div = document.createElement("div");
    div.className = "text-xs font-mono " + (level === "warn" ? "text-rose-400 font-bold" : "text-cyan-400 font-bold");
    var time = document.createElement("span");
    time.className = "text-gray-500 shrink-0";
    time.textContent = "[" + timeStr + "]";
    var tagSpan = document.createElement("span");
    tagSpan.className = "shrink-0";
    tagSpan.textContent = "[" + tag + "] ";
    var msg = document.createElement("span");
    msg.className = "flex-1";
    msg.textContent = message;
    div.appendChild(time);
    div.appendChild(tagSpan);
    div.appendChild(msg);
    stream.appendChild(div);
    stream.scrollTop = stream.scrollHeight;
    while (stream.children.length > 30) {
      stream.removeChild(stream.firstChild);
    }
  };

  DataFeed.prototype.tick = function () {
    var self = this;
    var now = Date.now();

    var results = {};
    var pending = ENDPOINTS.map(function (ep) {
      return self.fetchJson(ep.path).then(function (result) {
        results[ep.path] = result;
      });
    });

    return Promise.all(pending).then(function () {
      var pods = results["/api/v1/pods"];
      var events = results["/api/v1/events"];
      var slo = results["/api/v1/slo"];
      var argocd = results["/api/v1/argocd"];

      var anyStale =
        (pods && pods.stale) ||
        (events && events.stale) ||
        (slo && slo.stale) ||
        (argocd && argocd.stale);

      var anyOffline = false;
      var allOffline = true;
      var newestSuccess = null;
      ENDPOINTS.forEach(function (ep) {
        var st = self._endpointStates[ep.path];
        if (st.failureCount >= MAX_CONSECUTIVE_FAILURES) {
          anyOffline = true;
        } else {
          allOffline = false;
        }
        if (st.lastSuccessAt) {
          if (!newestSuccess || st.lastSuccessAt > newestSuccess) {
            newestSuccess = st.lastSuccessAt;
          }
        }
      });

      var badgeState;
      if (allOffline) {
        badgeState = "OFFLINE";
      } else if (anyStale || anyOffline) {
        badgeState = "STALE";
      } else if (newestSuccess && now - newestSuccess <= STALE_WINDOW_MS) {
        badgeState = "LIVE";
      } else {
        badgeState = "STALE";
      }

      // Reconnect / lost connection transitions
      var prev = self._badgeState;
      if (prev && prev !== badgeState) {
        if (badgeState === "LIVE" && (prev === "STALE" || prev === "OFFLINE")) {
          self._logEvent("replay", "replay", "DataFeed reconnected to agent-hub");
        } else if (prev === "LIVE" && (badgeState === "STALE" || badgeState === "OFFLINE")) {
          self._logEvent("warn", "warn", "DataFeed lost connection to agent-hub");
        }
      }
      self._badgeState = badgeState;
      self._wasOffline = badgeState === "OFFLINE";
      self.stale = badgeState !== "LIVE";

      // pods -> #pods-count
      var podsEl = ensureElement("pods-count");
      if (pods && !pods.stale && Array.isArray(pods)) {
        setText(podsEl, String(pods.length));
        podsEl.classList.remove("stale");
      } else {
        setText(podsEl, "n/a");
        podsEl.classList.add("stale");
      }

      // events -> #live-event-stream (text nodes only; no HTML injection)
      var stream = document.getElementById("live-event-stream");
      if (stream) {
        if (events && !events.stale && Array.isArray(events)) {
          events.slice(-5).forEach(function (e) {
            var div = document.createElement("div");
            div.className = "text-gray-300 text-xs font-mono flex items-start gap-2";
            var time = document.createElement("span");
            time.className = "text-gray-500 shrink-0";
            var ts = (e.created_at || "").slice(11, 19) || "unknown";
            time.textContent = "[" + ts + "]";
            var comp = document.createElement("span");
            comp.className = "font-semibold text-cyan-400 shrink-0";
            comp.textContent = "[agent] " + (e.event_type || "event") + ":";
            var msg = document.createElement("span");
            msg.className = "flex-1";
            msg.textContent = e.action || e.event_type || "event";
            div.appendChild(time);
            div.appendChild(comp);
            div.appendChild(msg);
            stream.appendChild(div);
          });
          stream.scrollTop = stream.scrollHeight;
          while (stream.children.length > 30) {
            stream.removeChild(stream.firstChild);
          }
        } else {
          var d = document.createElement("div");
          d.className = "text-gray-500 text-xs font-mono";
          d.textContent = "[datafeed] events unavailable";
          stream.appendChild(d);
        }
      }

      // slo -> #kpi-qps / #kpi-p99
      var kpiQps = document.getElementById("kpi-qps");
      var kpiP99 = document.getElementById("kpi-p99");
      if (slo && !slo.stale) {
        setText(kpiQps, slo.totalRuns !== undefined ? String(slo.totalRuns) + " runs" : "n/a");
        if (kpiQps) kpiQps.className = "text-lg font-bold text-cyan-400 font-mono mt-1";
        setText(kpiP99, slo.successRate !== undefined ? String(slo.successRate) + "% success" : "n/a");
        if (kpiP99) kpiP99.className = "text-lg font-bold text-emerald-400 font-mono mt-1";
      } else {
        setText(kpiQps, "n/a");
        setText(kpiP99, "n/a");
      }

      // argocd -> #header-gitops-status
      var gitopsEl = document.getElementById("header-gitops-status");
      if (argocd && !argocd.stale && Array.isArray(argocd)) {
        var synced = argocd.filter(function (a) { return a.sync === "Synced"; }).length;
        setText(gitopsEl, argocd.length + " apps · " + synced + " Synced");
      } else {
        setText(gitopsEl, "n/a");
      }

      // stale badge
      var badge = document.getElementById("stale-badge");
      if (!badge) {
        badge = document.createElement("span");
        badge.id = "stale-badge";
        var header = document.querySelector("header");
        if (header) {
          header.appendChild(badge);
        } else {
          document.body.appendChild(badge);
        }
      }
      if (badgeState === "LIVE") {
        setText(badge, "LIVE");
        badge.className = "badge-live";
      } else if (badgeState === "OFFLINE") {
        setText(badge, "OFFLINE");
        badge.className = "badge-offline";
      } else {
        setText(badge, "STALE");
        badge.className = "badge-stale";
      }

      self.lastResult = { pods: pods, events: events, slo: slo, argocd: argocd };
    });
  };

  DataFeed.prototype.start = function () {
    var self = this;
    if (this._started) return;
    this._started = true;
    this.tick();
    this._timer = setInterval(function () { self.tick(); }, this.pollIntervalMs);
  };

  DataFeed.prototype.stop = function () {
    if (this._timer) {
      clearInterval(this._timer);
      this._timer = null;
    }
    this._started = false;
  };

  window.DataFeed = DataFeed;

  window.startDataFeed = function (options) {
    var feed = new DataFeed(options);
    feed.start();
    return feed;
  };
})();

#!/usr/bin/env python3
"""Smoke test for the AKS SRE Console (sre-console).

Checks:
  1. All required files exist.
  2. index.html references styles.css and all 5 JS files.
  3. index.html has tab-panel divs for realtime, cluster, workload, gitops, gates.
  4. app.js has loadTabContent function.
Reports PASS/FAIL per check and overall result.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

REQUIRED_FILES = [
    "index.html",
    "styles.css",
    "app.js",
    "charts.js",
    "simulation.js",
    "actions.js",
    "runbook.js",
    "tabs/realtime.html",
    "tabs/cluster.html",
    "tabs/workload.html",
    "tabs/gitops.html",
    "tabs/gates.html",
]

JS_FILES = ["app.js", "charts.js", "simulation.js", "actions.js", "runbook.js"]

TAB_PANEL_IDS = ["realtime", "cluster", "workload", "gitops", "gates"]


def check_file_exists():
    missing = []
    for rel in REQUIRED_FILES:
        if not os.path.isfile(os.path.join(BASE_DIR, rel)):
            missing.append(rel)
    status = "PASS" if not missing else "FAIL"
    detail = "" if not missing else "missing: " + ", ".join(missing)
    return status, detail


def check_index_references():
    index_path = os.path.join(BASE_DIR, "index.html")
    if not os.path.isfile(index_path):
        return "FAIL", "index.html not found"
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()
    missing = []
    if 'href="styles.css"' not in html:
        missing.append("styles.css")
    for js in JS_FILES:
        if 'src="%s"' % js not in html:
            missing.append(js)
    status = "PASS" if not missing else "FAIL"
    detail = "" if not missing else "missing references: " + ", ".join(missing)
    return status, detail


def check_tab_panels():
    index_path = os.path.join(BASE_DIR, "index.html")
    if not os.path.isfile(index_path):
        return "FAIL", "index.html not found"
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()
    missing = []
    for tab in TAB_PANEL_IDS:
        if 'id="view-%s"' % tab not in html:
            missing.append(tab)
    status = "PASS" if not missing else "FAIL"
    detail = "" if not missing else "missing tab-panels: " + ", ".join(missing)
    return status, detail


def check_load_tab_content():
    app_path = os.path.join(BASE_DIR, "app.js")
    if not os.path.isfile(app_path):
        return "FAIL", "app.js not found"
    with open(app_path, "r", encoding="utf-8") as f:
        app_src = f.read()
    if "function loadTabContent" not in app_src:
        return "FAIL", "loadTabContent function not defined in app.js"
    return "PASS", ""


def main():
    checks = [
        ("Required files exist", check_file_exists),
        ("index.html references styles.css + 5 JS files", check_index_references),
        ("index.html has tab-panel divs (realtime, cluster, workload, gitops, gates)", check_tab_panels),
        ("app.js has loadTabContent function", check_load_tab_content),
    ]

    results = []
    for name, fn in checks:
        status, detail = fn()
        results.append((name, status, detail))
        print("[%s] %s%s" % (status, name, (" - " + detail) if detail else ""))

    overall = "PASS" if all(s == "PASS" for _, s, _ in results) else "FAIL"
    print("\nOverall: %s" % overall)
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

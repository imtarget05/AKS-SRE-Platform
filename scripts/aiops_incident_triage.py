#!/usr/bin/env python3
"""
AIOps Incident Triage & Automated Runbook Correlator
Maps incoming infrastructure/application alerts and incident payloads to
actionable SRE runbooks, severity tiers, and verification commands.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class IncidentTriageEngine:
    def __init__(self, runbooks_dir: Path):
        self.runbooks_dir = runbooks_dir
        self.runbooks: List[Dict[str, Any]] = []
        self._load_runbooks()

    def _load_runbooks(self):
        self.runbooks.clear()
        if not self.runbooks_dir.exists():
            return

        for p in self.runbooks_dir.glob("*.md"):
            content = p.read_text(encoding="utf-8", errors="replace")
            title_m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            title = title_m.group(1).strip() if title_m else p.stem

            trigger_m = re.search(r"\*\*Trigger:\*\*\s*(.+)$", content, re.MULTILINE)
            severity_m = re.search(r"\*\*Severity:\*\*\s*(.+)$", content, re.MULTILINE)
            impact_m = re.search(r"\*\*Impact:\*\*\s*(.+)$", content, re.MULTILINE)
            owner_m = re.search(r"\*\*Owner:\*\*\s*(.+)$", content, re.MULTILINE)
            verification_m = re.search(r"\*\*Verification Target:\*\*\s*(.+)$", content, re.MULTILINE)

            self.runbooks.append({
                "file": p.name,
                "path": str(p),
                "title": title,
                "trigger": trigger_m.group(1).strip() if trigger_m else "",
                "severity": severity_m.group(1).strip() if severity_m else "P2",
                "impact": impact_m.group(1).strip() if impact_m else "",
                "owner": owner_m.group(1).strip() if owner_m else "SRE Platform Team",
                "verification": verification_m.group(1).strip() if verification_m else "",
                "raw_content": content,
            })

    def triage(self, alert_query: str) -> Optional[Dict[str, Any]]:
        expanded_query = re.sub(r"([a-z])([A-Z])", r"\1 \2", alert_query)
        tokens = [t.lower() for t in re.findall(r"\b\w{3,}\b", expanded_query)]
        if not tokens:
            return None

        best_rb = None
        best_score = -1.0

        for rb in self.runbooks:
            title_text = rb["title"].lower()
            trigger_text = rb["trigger"].lower()
            impact_text = rb["impact"].lower()
            content_text = rb["raw_content"].lower()

            score = 0.0
            for t in tokens:
                score += title_text.count(t) * 5.0
                score += trigger_text.count(t) * 4.0
                score += impact_text.count(t) * 2.0
                score += min(content_text.count(t), 10) * 0.5

            if score > best_score and score > 0:
                best_score = score
                best_rb = rb

        if not best_rb:
            return None

        # Extract code blocks from the runbook as suggested remediation commands
        code_blocks = re.findall(r"```bash\n(.*?)\n```", best_rb["raw_content"], re.DOTALL)
        recommended_cmds = []
        for block in code_blocks:
            lines = [l.strip() for l in block.splitlines() if l.strip() and not l.strip().startswith("#")]
            for l in lines:
                if l and not l.startswith("```"):
                    recommended_cmds.append(l)

        return {
            "query": alert_query,
            "matched_runbook": best_rb["file"],
            "title": best_rb["title"],
            "severity": best_rb["severity"],
            "impact": best_rb["impact"],
            "owner": best_rb["owner"],
            "verification_target": best_rb["verification"],
            "recommended_actions": recommended_cmds[:5],
            "runbook_path": best_rb["path"],
        }


def main():
    parser = argparse.ArgumentParser(description="AIOps Incident Triage Engine")
    parser.add_argument("--alert", type=str, help="Incoming alert name or description")
    parser.add_argument("--simulate", action="store_true", help="Run simulated drill triage scenarios")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    args = parser.parse_args()

    runbooks_dir = Path(__file__).resolve().parent.parent / "docs" / "runbooks"
    engine = IncidentTriageEngine(runbooks_dir)

    if args.simulate:
        scenarios = [
            "SLOHighErrorRateBurn: Availability dropped below 99.9%, burn rate 14.4x observed",
            "NodeEvictionDrain: Maintenance planned on local-platform-worker, PDB minAvailable check",
            "NetworkPolicyViolation: Egress packet to 1.1.1.1 dropped from sre-demo-api pod",
        ]
        results = [engine.triage(sc) for sc in scenarios]
        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print("\n=======================================================")
            print("🚀 AIOps SIMULATED INCIDENT TRIAGE REPORT")
            print("=======================================================\n")
            for i, res in enumerate(results, 1):
                if not res:
                    continue
                print(f"[{i}] Alert: {res['query']}")
                print(f"    Matched Runbook : {res['matched_runbook']} ({res['title']})")
                print(f"    Severity Tier   : {res['severity']}")
                print(f"    Assigned Owner  : {res['owner']}")
                print(f"    Impact Summary  : {res['impact']}")
                print(f"    Verification    : {res['verification_target']}")
                print(f"    Immediate Remediation Commands:")
                for cmd in res["recommended_actions"]:
                    print(f"      $ {cmd}")
                print("-" * 55)
        return

    if not args.alert:
        print("Usage: python3 aiops_incident_triage.py --alert 'SLOHighErrorRateBurn' or --simulate")
        return

    result = engine.triage(args.alert)
    if not result:
        print(f"No specific runbook found for alert: '{args.alert}'. Escalate to default SRE On-Call.")
        return

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"\n🚨 AIOps INCIDENT TRIAGE: {result['title']}")
        print(f"   Severity : {result['severity']}")
        print(f"   Owner    : {result['owner']}")
        print(f"   Runbook  : {result['runbook_path']}")
        print(f"   Impact   : {result['impact']}")
        print(f"   Target   : {result['verification_target']}")
        print(f"\n🛠️ Automated Remediation Commands:")
        for cmd in result["recommended_actions"]:
            print(f"   $ {cmd}")
        print()


if __name__ == "__main__":
    main()

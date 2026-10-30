"""CLI entry point for the platform-owned read-only SRE incident agent.

Writes a JSON evidence file. Read-only: no kubectl write, Argo mutation,
Terraform, or secret access. Feature-flag gated; offline default.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .workflow import (
    FEATURE_FLAG_ENV,
    SREIncidentWorkflow,
    _is_feature_enabled,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Platform-owned read-only SRE incident workflow (MVP)"
    )
    parser.add_argument(
        "--alert", required=True, help="Alert name / alert id to investigate"
    )
    parser.add_argument(
        "--context",
        default="kind-local-platform",
        help="Kubernetes context",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="JSON evidence output path",
    )
    parser.add_argument(
        "--assessed-by",
        default="operator",
        help="Who assessed the incident",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    workflow = SREIncidentWorkflow(
        context=args.context, assessed_by=args.assessed_by
    )
    brief = workflow.investigate(
        args.alert, context=args.context, assessed_by=args.assessed_by
    )

    evidence = {
        "incident_id": brief.incident_id,
        "feature_enabled": _is_feature_enabled(),
        "assessed_by": args.assessed_by,
        "context": args.context,
        "alert_evidence": asdict(brief.alert_evidence),
        "triage_verdict": brief.triage_verdict.value,
        "diagnosis": asdict(brief.diagnosis),
        "critic_verdict": asdict(brief.critic_verdict),
        "critic_brief": brief.critic_brief,
        "read_only_checks": brief.read_only_checks,
        "is_read_only": brief.is_read_only,
        "completed_at": brief.completed_at,
        "notification_delivery_verified": bool(brief.alert_evidence.receivers),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {args.output} "
        f"(triage={brief.triage_verdict.value}, read_only={brief.is_read_only})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

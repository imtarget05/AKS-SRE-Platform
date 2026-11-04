#!/usr/bin/env python3
"""Tests for scripts/policy-gate.py check_images image digest rules."""

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, "scripts")

_module_path = Path("scripts/policy-gate.py").resolve()
_spec = importlib.util.spec_from_file_location("policy_gate", _module_path)
policy_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(policy_gate)  # type: ignore[union-attr]

FAILURES = policy_gate.FAILURES
check_images = policy_gate.check_images


def _clear():
    FAILURES.clear()


def test_digest_placeholder_fails():
    docs = [
        {
            "kind": "Deployment",
            "metadata": {"name": "d"},
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "image": "registry.io/app@sha256:" + "0" * 64
                            }
                        ]
                    }
                }
            },
        }
    ]
    _clear()
    check_images(docs, "test.yaml", require_digest=False)
    assert any(f["rule"] == "image-digest-placeholder" for f in FAILURES), FAILURES


def test_valid_digest_passes():
    docs = [
        {
            "kind": "Deployment",
            "metadata": {"name": "d"},
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {"image": "registry.io/app@sha256:" + "abcd" * 16}
                        ]
                    }
                }
            },
        }
    ]
    _clear()
    check_images(docs, "test.yaml", require_digest=False)
    assert not any(
        f["rule"] in ("image-digest-placeholder", "image-digest-malformed")
        for f in FAILURES
    ), FAILURES


if __name__ == "__main__":
    test_digest_placeholder_fails()
    test_valid_digest_passes()
    print("ALL TESTS PASSED")

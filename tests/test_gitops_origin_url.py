"""GitHub checkout remotes may omit the optional .git suffix."""

import importlib.util
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "gitops/validate-gitops.py"
SPEC = importlib.util.spec_from_file_location("gitops_validator", SCRIPT)
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def test_checkout_origin_accepts_optional_git_suffix_only():
    expected = "https://github.com/imtarget05/CreditFlow.git"
    with patch.object(validator.subprocess, "run", return_value=CompletedProcess([], 0, "https://github.com/imtarget05/CreditFlow\n")):
        assert validator.checkout_origin_matches("unused", expected)
    with patch.object(validator.subprocess, "run", return_value=CompletedProcess([], 0, "https://github.com/other/CreditFlow\n")):
        assert not validator.checkout_origin_matches("unused", expected)

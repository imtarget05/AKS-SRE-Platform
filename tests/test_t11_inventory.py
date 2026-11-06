#!/usr/bin/env python3
"""T11 inventory/validation tests (read-only, local files, no Azure API).

Exercises scripts/t11_inventory.py and asserts:
  - declared Terraform resources are labelled TERRAFORM_ONLY, never live
  - out-of-scope resources (App Service, VPN, Application Gateway, Key Vault,
    standalone VM, standalone LB) are labelled NOT_DECLARED
  - kubernetes manifests parse as YAML
  - Python files under scripts/ and tests/ compile
"""
import json
import subprocess
import sys

import pytest

SCRIPT = "scripts/t11_inventory.py"


def run(*args):
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True,
        text=True,
        timeout=120,
    )


def summary(stdout: str) -> dict:
    start = stdout.index("{")
    end = stdout.rindex("}") + 1
    return json.loads(stdout[start:end])


class TestTfResources:
    @pytest.fixture(autouse=True)
    def _out(self):
        self.result = run("tf-resources")
        self.data = summary(self.result.stdout)

    def test_exits_zero(self):
        assert self.result.returncode == 0, self.result.stderr

    def test_no_live_resources(self):
        assert self.data["live_resources"] == [], self.data["live_resources"]

    def _declared_items(self):
        return {r["item"] for r in self.data["declared_resources"]}

    def test_aks_declared_terraform_only(self):
        items = self._declared_items()
        assert "AKS cluster" in items
        for r in self.data["declared_resources"]:
            if r["item"] == "AKS cluster":
                assert r["classification"] == "TERRAFORM_ONLY"
                assert r["live"] is False

    def test_vnet_declared_terraform_only(self):
        items = self._declared_items()
        assert "VNet" in items

    def test_nsg_declared_terraform_only(self):
        items = self._declared_items()
        assert "Network Security Group" in items

    def test_storage_account_declared_terraform_only(self):
        items = self._declared_items()
        assert "Storage account (Blob/File/Disk-capable)" in items

    def test_rbac_role_assignment_declared_terraform_only(self):
        items = self._declared_items()
        assert "RBAC role assignment" in items

    def test_not_declared_scope(self):
        not_declared = {r["item"] for r in self.data["not_declared"]}
        for expected in (
            "App Service",
            "VPN",
            "Application Gateway",
            "Key Vault",
            "VM (standalone)",
            "Standalone Load Balancer",
        ):
            assert expected in not_declared, f"{expected} missing from not_declared"
        for r in self.data["not_declared"]:
            assert r["classification"] == "NOT_DECLARED"
            assert r["live"] is False


class TestManifests:
    @pytest.fixture(autouse=True)
    def _out(self):
        self.result = run("manifests")

    def test_exits_zero(self):
        assert self.result.returncode == 0, self.result.stderr

    def test_lists_manifests(self):
        assert "Valid YAML" in self.result.stdout


class TestSyntax:
    @pytest.fixture(autouse=True)
    def _out(self):
        self.result = run("syntax")

    def test_exits_zero(self):
        assert self.result.returncode == 0, self.result.stderr

    def test_all_compile(self):
        rows = [line for line in self.result.stdout.splitlines()
                if line.strip().startswith("|")]
        for row in rows:
            if "---" in row or " File |" in row:
                continue
            assert " | Yes |" in row, row


class TestAll:
    def test_all_mode_exits_zero(self):
        result = run("all")
        assert result.returncode == 0, result.stderr

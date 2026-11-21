"""Behavior tests for the fail-closed kind rollback evidence runner."""

import json
import subprocess
import sys
from unittest.mock import Mock, patch

import pytest

from scripts import kind_rollback_drill as drill


def deployment(image, ready=2):
    return json.dumps({"status": {"readyReplicas": ready},
                       "spec": {"template": {"spec": {"containers": [{"image": image}]}}}})


def test_complete_drill_writes_measured_evidence(tmp_path):
    image = "sre-demo-api:drill-test"
    state = {"image": image}
    commands = []

    def fake_run(command, **_kwargs):
        commands.append(command)
        if command == ["kubectl", "config", "current-context"]:
            return "kind-sre-rollback\n"
        if "set" in command and "image" in command:
            state["image"] = "invalid.local/sre-demo-api:deliberately-missing"
        if "undo" in command:
            state["image"] = image
        if "deployment" in command and "-o" in command and "json" in command:
            return deployment(state["image"])
        return "{}"

    process = Mock()
    process.wait.return_value = 0
    with patch.object(drill, "OUTPUT", tmp_path), \
         patch.object(drill, "run", side_effect=fake_run), \
         patch.object(drill, "http_status", return_value=200), \
         patch.object(drill, "image_pull_failure", return_value={"pod": "bad-pod", "reason": "ErrImagePull"}), \
         patch.object(drill.subprocess, "Popen", return_value=process), \
         patch.object(sys, "argv", ["drill", "--context", "kind-sre-rollback", "--image", image]):
        drill.main()

    result = json.loads((tmp_path / "result.json").read_text())
    assert result["status"] == "passed"
    assert [event["name"] for event in result["events"]] == [
        "baseline_ready", "baseline_http_healthy", "bad_image_deployed",
        "fault_detected", "rollback_verified"]
    assert result["events"][-1]["image"] == image
    assert result["events"][-1]["duration_seconds"] >= 0
    assert any("undo" in command for command in commands)
    process.terminate.assert_called_once()


def test_rejects_context_that_is_not_active_kind(tmp_path):
    with patch.object(drill, "OUTPUT", tmp_path), \
         patch.object(drill, "run", return_value="production-aks\n"), \
         patch.object(sys, "argv", ["drill", "--context", "production-aks", "--image", "image:test"]):
        with pytest.raises(ValueError, match="active kind"):
            drill.main()
    assert json.loads((tmp_path / "result.json").read_text())["status"] == "failed"


def test_digest_drill_rejects_mutable_image_tag(tmp_path):
    with patch.object(drill, "OUTPUT", tmp_path), \
         patch.object(sys, "argv", ["drill", "--context", "kind-sre-rollback",
                                    "--image", "localhost:5002/sre-demo-api:latest", "--require-digest"]):
        with pytest.raises(ValueError, match="digest-pinned"):
            drill.main()
    assert json.loads((tmp_path / "result.json").read_text())["status"] == "failed"


def test_detects_actual_image_pull_failure():
    pods = {"items": [{"metadata": {"name": "good"}, "status": {"containerStatuses": []}},
                      {"metadata": {"name": "bad"}, "status": {"containerStatuses": [
                          {"state": {"waiting": {"reason": "ErrImagePull"}}}]}}]}
    with patch.object(drill, "run", return_value=json.dumps(pods)):
        assert drill.image_pull_failure(["kubectl"], "ns") == {"pod": "bad", "reason": "ErrImagePull"}
    with patch.object(drill, "run", return_value=json.dumps({"items": []})):
        assert drill.image_pull_failure(["kubectl"], "ns") is None


def test_ready_pods_must_run_the_pushed_digest():
    digest = "sha256:" + "a" * 64
    pods = {"items": [{"status": {"containerStatuses": [
        {"ready": True, "imageID": "localhost:5002/sre-demo-api@" + digest},
        {"ready": True, "imageID": "localhost:5002/sre-demo-api@" + digest},
    ]}}]}
    with patch.object(drill, "run", return_value=json.dumps(pods)):
        assert len(drill.assert_ready_pods_use_digest(["kubectl"], "ns", digest)) == 2
    pods["items"][0]["status"]["containerStatuses"][1]["imageID"] = "other@sha256:" + "b" * 64
    with patch.object(drill, "run", return_value=json.dumps(pods)):
        with pytest.raises(AssertionError, match="runtime image digest"):
            drill.assert_ready_pods_use_digest(["kubectl"], "ns", digest)


def test_wait_and_http_fail_closed():
    with patch.object(drill.time, "monotonic", side_effect=[0, 1]):
        with pytest.raises(TimeoutError):
            drill.wait_for(lambda: False, 1, "missing")
    with patch.object(drill.urllib.request, "urlopen", side_effect=drill.urllib.error.URLError("offline")):
        assert drill.http_status() == 0


def test_cleanup_collects_partial_evidence_and_kills_stuck_forward(tmp_path):
    process = Mock()
    process.wait.side_effect = subprocess.TimeoutExpired("port-forward", 5)
    with patch.object(drill, "OUTPUT", tmp_path), patch.object(drill, "run", return_value="state") as command:
        drill.collect_evidence(["kubectl"], "ns", {"status": "failed"}, process)
    assert json.loads((tmp_path / "result.json").read_text())["status"] == "failed"
    assert (tmp_path / "events.txt").read_text() == "state"
    assert command.call_count == 4
    process.kill.assert_called_once()

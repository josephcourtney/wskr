"""Evidence bundles retain exact outcomes, including GUI and check failures."""

from __future__ import annotations

import json
import zipfile

import pytest

from scripts import phase1_evidence as evidence

pytestmark = pytest.mark.small


def test_run_bundle_is_unique_and_contains_manifest_and_all_logs(monkeypatch, tmp_path):
    monkeypatch.setattr(evidence, "_short_git", lambda *_args: "testhead")

    def fake_run(command, log_path, *, timeout):
        log_path.write_text(f"{command!r} ({timeout})\n", encoding="utf-8")
        return {"status": "passed", "exit_code": 0, "log": log_path.name}

    def fake_capture(name, run_id, directory, *, timeout):
        image = directory / f"{name}-screen.png"
        image.write_bytes(b"fake window png for bundle test")
        return {"status": "captured_unreviewed", "screenshot": image.name}

    monkeypatch.setattr(evidence, "_run_logged", fake_run)
    monkeypatch.setattr(evidence, "_capture_scenario", fake_capture)
    first_zip, first = evidence.collect(tmp_path)
    second_zip, second = evidence.collect(tmp_path)
    assert first_zip != second_zip
    assert first["run_id"] != second["run_id"]
    assert set(first["checks"]) == set(evidence.CHECKS)
    assert set(first["screenshots"]) == set(evidence.SCENARIOS)
    with zipfile.ZipFile(first_zip) as archive:
        names = set(archive.namelist())
        assert "manifest.json" in names
        assert "logs/just-check.log" in names
        assert "screenshots/matplotlib-screen.png" in names
        captured = json.loads(archive.read("manifest.json"))
        assert captured["git"]["sha"] == "testhead"
        assert captured["screenshots"]["rich"]["status"] == "captured_unreviewed"
        assert "screenshots/matplotlib-screen.png" in captured["file_sha256"]


def test_failed_capture_preserved_and_does_not_claim_visual_success(monkeypatch, tmp_path):
    monkeypatch.setattr(evidence, "_short_git", lambda *_args: "localhead")

    def fake_run(command, path, *, timeout):
        path.write_text("check output", encoding="utf-8")
        return {"status": "passed", "exit_code": 0}

    monkeypatch.setattr(evidence, "_run_logged", fake_run)
    monkeypatch.setattr(
        evidence,
        "_capture_scenario",
        lambda *_args, **_kwargs: {"status": "failed", "error": "Screen Recording permission absent"},
    )
    archive, result = evidence.collect(tmp_path)
    assert all(item["status"] == "failed" for item in result["screenshots"].values())
    with zipfile.ZipFile(archive) as contents:
        manifest = json.loads(contents.read("manifest.json"))
        assert manifest["screenshots"]["matplotlib"]["status"] == "failed"
        assert "Screen Recording permission" in manifest["screenshots"]["matplotlib"]["error"]


def test_explicit_skip_modes_are_labeled_and_still_package_evidence(monkeypatch, tmp_path):
    monkeypatch.setattr(evidence, "_short_git", lambda *_args: None)

    def fake_run(command, path, *, timeout):
        path.write_text("rc defaults snapshot", encoding="utf-8")
        return {"status": "passed"}

    monkeypatch.setattr(evidence, "_run_logged", fake_run)
    archive, manifest = evidence.collect(tmp_path, checks=False, gui=False)
    assert archive.exists()
    assert all(item["status"] == "skipped" for item in manifest["checks"].values())
    assert all(item["status"] == "skipped" for item in manifest["screenshots"].values())
    assert manifest["git"]["sha"] is None


def test_screenshot_safety_never_uses_non_macos_desktop(monkeypatch, tmp_path):
    monkeypatch.setattr(evidence.shutil, "which", lambda name: "/fake/kitty" if name == "kitty" else None)
    monkeypatch.setattr(evidence.platform, "system", lambda: "Linux")
    result = evidence._capture_scenario("rich", "abc", tmp_path, timeout=1)
    assert result["status"] == "failed"
    assert "macOS" in result["error"]


def test_capture_uses_only_titled_kitty_window_and_scoped_screencapture(monkeypatch, tmp_path):
    """The runner must not capture the desktop or another Kitty session."""
    from pathlib import Path

    monkeypatch.setattr(evidence.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(evidence.shutil, "which", lambda name: "/usr/local/bin/kitty" if name == "kitty" else None)
    monkeypatch.setattr(evidence, "_find_window", lambda title, *, timeout: 42)
    monkeypatch.setattr(evidence.time, "sleep", lambda _seconds: None)
    processes = []

    class OwnedKitty:
        def __init__(self):
            self.terminated = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

        def wait(self, *, timeout):
            return 0

    def fake_popen(command, **kwargs):
        assert command[0] == "/usr/local/bin/kitty"
        assert "--title" in command
        marker = Path(command[command.index("--ready-file") + 1])
        marker.write_text("render-complete\n", encoding="utf-8")
        process = OwnedKitty()
        processes.append(process)
        return process

    def fake_run(command, **kwargs):
        assert command[:4] == ["/usr/sbin/screencapture", "-x", "-o", "-l"]
        assert command[4] == "42"
        Path(command[-1]).write_bytes(b"mock PNG data; verified separately")
        return type("Result", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(evidence.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(evidence.subprocess, "run", fake_run)
    monkeypatch.setattr(evidence, "_validate_png", lambda _path: (320, 240))
    result = evidence._capture_scenario("matplotlib", "abcdef", tmp_path, timeout=1)
    assert result["status"] == "captured_unreviewed"
    assert result["size_px"] == [320, 240]
    assert all(proc.terminated for proc in processes)
    assert not (tmp_path / "matplotlib.ready").exists()

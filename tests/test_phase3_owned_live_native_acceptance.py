"""Portable checks for the native macOS owned-viewport acceptance harness."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from scripts import phase3_owned_live_native_acceptance as harness

pytestmark = pytest.mark.medium


def _bars(path: Path) -> None:
    image = np.full((120, 180, 3), 50, dtype=np.uint8)
    image[10:100, 10:83] = (255, 0, 0)
    image[10:100, 95:168] = (0, 0, 255)
    Image.fromarray(image).save(path)


def test_pixel_counts_distinguish_bars_and_blank_picker(tmp_path: Path) -> None:
    path = tmp_path / "bars.png"
    _bars(path)
    counts = harness.pixel_counts(path)
    assert counts["red"] > 6000
    assert counts["blue"] > 6000
    assert counts["near_black_fraction"] < 0.95
    assert harness.visible_bars(counts)

    black = tmp_path / "blank.png"
    Image.new("RGB", (180, 120), "black").save(black)
    blank_counts = harness.pixel_counts(black)
    assert blank_counts["near_black_fraction"] == 1.0
    assert not harness.visible_bars(blank_counts)


def test_screenshot_retries_invalid_black_frame(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[str] = []

    def run(argv: list[str], *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
        path = Path(argv[-1])
        calls.append(str(path))
        if len(calls) == 1:
            Image.new("RGB", (180, 120), "black").save(path)
        else:
            _bars(path)
        return subprocess.CompletedProcess(argv, 0, stdout="")

    @dataclass
    class Geometry:
        rows: int = 20
        columns: int = 60
        width_px: int = 720
        height_px: int = 540

    monkeypatch.setattr(harness, "_command", run)
    monkeypatch.setattr(harness, "_dialog", lambda _message: None)
    monkeypatch.setattr(harness, "_geometry", Geometry)
    result = harness._capture(tmp_path, "resized")
    assert len(calls) == 2
    assert result["colors"]["red"] > 6000
    assert (tmp_path / "resized.invalid-1.png").exists()


def test_unowned_probe_rejects_ansi_or_unsuccessful_check(monkeypatch: pytest.MonkeyPatch) -> None:
    def safe(*_args, **_kwargs) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess([], 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(harness.subprocess, "run", safe)
    harness._check_unowned()

    def unsafe(*_args, **_kwargs) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess([], 0, stdout=b"\x1b[?1049h", stderr=b"")

    monkeypatch.setattr(harness.subprocess, "run", unsafe)
    with pytest.raises(AssertionError, match="rejection failed"):
        harness._check_unowned()


def test_resize_poll_waits_for_actual_upload() -> None:
    frames: list[dict] = [{}]

    class View:
        called = 0

        def poll_resize(self) -> bool:
            self.called += 1
            if self.called == 3:
                frames.append({})
                return True
            return False

    view = View()
    harness._poll_for_redraw(view, frames, 2)
    assert view.called == 3


def test_record_stage_preserves_visual_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    report: dict = {"stages": [], "failures": []}
    monkeypatch.setattr(
        harness,
        "_capture",
        lambda _directory, _stage: {"stage": "resized", "colors": {"red": 0, "blue": 0}},
    )
    harness._record_stage(tmp_path, report, "resized", expect_visible=True)
    assert len(report["failures"]) == 1
    assert (tmp_path / "report.json").exists()

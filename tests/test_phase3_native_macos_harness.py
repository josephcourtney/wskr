"""Pure checks for native macOS Kitty screenshot acceptance evidence."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from scripts.phase3_native_macos_resize import _colors, _dialog, _record_visibility, _screenshot, _visible

pytestmark = pytest.mark.medium


def _bars(path: Path) -> None:
    image = Image.new("RGB", (180, 100), "black")
    draw = ImageDraw.Draw(image)
    draw.rectangle((5, 5, 80, 90), fill="red")
    draw.rectangle((95, 5, 175, 90), fill="blue")
    image.save(path)


def test_screen_colors_identify_both_plot_bars(tmp_path: Path) -> None:
    path = tmp_path / "test.png"
    _bars(path)
    counts = _colors(path)
    assert counts["red"] > 5_000
    assert counts["blue"] > 5_000
    _visible({"stage": "initial", "screenshot": str(path), "colors": counts})


def test_screen_colors_reject_missing_chart(tmp_path: Path) -> None:
    path = tmp_path / "empty.png"
    Image.new("RGB", (180, 100), "black").save(path)
    with pytest.raises(AssertionError, match="not both visible"):
        _visible({"stage": "resized", "screenshot": str(path), "colors": _colors(path)})


def test_screenshot_only_selects_window(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def capture(argv: list[str], *, check: bool, timeout: int) -> subprocess.CompletedProcess[str]:
        assert argv[:5] == ["/usr/sbin/screencapture", "-x", "-i", "-w", "-o"]
        assert not check
        assert timeout == 180
        _bars(Path(argv[-1]))
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(subprocess, "run", capture)
    result = _screenshot(tmp_path, "resized")
    assert result["stage"] == "resized"
    assert result["colors"]["red"] > 5_000
    assert result["colors"]["blue"] > 5_000


def test_screenshot_cancellation_is_explicit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def cancel(argv: list[str], *, check: bool, timeout: int) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 1)

    monkeypatch.setattr(subprocess, "run", cancel)
    with pytest.raises(RuntimeError, match="failed or was cancelled"):
        _screenshot(tmp_path, "initial")


def test_visual_failures_are_recorded_without_aborting_remaining_stages() -> None:
    report: dict = {"visual_failures": []}
    _record_visibility(
        report,
        {"stage": "resized", "screenshot": "resized.png", "colors": {"red": 0, "blue": 0}},
    )
    assert len(report["visual_failures"]) == 1
    assert "resized" in report["visual_failures"][0]

    # The final visible frame does not erase prior acceptance failures.
    _record_visibility(
        report,
        {"stage": "expanded", "screenshot": "expanded.png", "colors": {"red": 900, "blue": 900}},
    )
    assert len(report["visual_failures"]) == 1


def test_resize_instructions_use_gui_without_tty_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def show_dialog(
        argv: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        assert not check
        assert capture_output
        assert text
        assert timeout == 180
        return subprocess.CompletedProcess(argv, 0, stdout="button returned:Continue")

    monkeypatch.setattr(subprocess, "run", show_dialog)
    _dialog("Shrink Kitty")
    assert len(calls) == 1
    assert calls[0][:2] == ["/usr/bin/osascript", "-e"]
    assert 'display dialog "Shrink Kitty"' in calls[0][2]


def test_resize_dialog_cancellation_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    def cancel_dialog(
        argv: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="User canceled")

    monkeypatch.setattr(subprocess, "run", cancel_dialog)
    with pytest.raises(RuntimeError, match="cancelled"):
        _dialog("Shrink Kitty")

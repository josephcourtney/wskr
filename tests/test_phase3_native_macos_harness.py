"""Pure checks for native macOS Kitty screenshot acceptance evidence."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from scripts.phase3_native_macos_resize import (
    _clear_scrollback,
    _colors,
    _dialog,
    _mostly_black,
    _record_visibility,
    _screenshot,
    _visible,
)

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


def test_black_screenshot_is_invalid(tmp_path: Path) -> None:
    blank = tmp_path / "blank.png"
    Image.new("RGB", (180, 100), "black").save(blank)
    assert _mostly_black(blank)
    bars = tmp_path / "bars.png"
    _bars(bars)
    assert not _mostly_black(bars)


def test_black_screenshot_retries_without_accepting_zero_bars(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    attempts = [0]
    prompts: list[str] = []

    def capture(argv: list[str], *, check: bool, timeout: int) -> subprocess.CompletedProcess[str]:
        attempts[0] += 1
        path = Path(argv[-1])
        if attempts[0] == 1:
            Image.new("RGB", (180, 100), "black").save(path)
        else:
            _bars(path)
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(subprocess, "run", capture)
    monkeypatch.setattr("scripts.phase3_native_macos_resize._dialog", prompts.append)
    result = _screenshot(tmp_path, "expanded")
    assert attempts == [2]
    assert len(prompts) == 1
    assert (tmp_path / "expanded.invalid-1.png").exists()
    assert result["colors"]["red"] > 5_000


def test_clean_scrollback_uses_erase_saved_lines_only_when_called(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int, bytes]] = []

    class Output:
        def fileno(self) -> int:
            return 42

        def flush(self) -> None:
            pass

    monkeypatch.setattr("scripts.phase3_native_macos_resize.sys.stdout", Output())
    monkeypatch.setattr("scripts.phase3_native_macos_resize.os.write", lambda fd, data: calls.append((fd, data)))
    _clear_scrollback()
    assert calls == [(42, bytes([27]) + b"[3J" + bytes([27]) + b"[2J" + bytes([27]) + b"[H")]

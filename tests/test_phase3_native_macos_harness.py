"""Pure checks for native macOS Kitty screenshot acceptance evidence."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from scripts.phase3_native_macos_resize import (
    _clear_scrollback,
    _colors,
    _dialog,
    _history_fixture,
    _history_text_below_plot,
    _mostly_black,
    _record_history_order,
    _record_visibility,
    _screenshot,
    _seed_history,
    _visible,
    _worker_argv,
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


def test_seeded_history_lines_are_deterministic_and_reflowable() -> None:
    assert _history_fixture(0) == ""
    payload = _history_fixture(3)
    rows = payload.splitlines()
    assert len(rows) == 3
    assert len(rows[0]) == 112
    assert all(len(row) == 112 for row in rows)
    assert rows[0].startswith("WSKR_HISTORY_0000 ")
    assert rows[2].startswith("WSKR_HISTORY_0002 ")
    assert payload.endswith("\n")
    assert "\x1b" not in payload


def test_seeded_history_rejects_unbounded_output() -> None:
    with pytest.raises(ValueError, match="History fixture"):
        _history_fixture(-1)
    with pytest.raises(ValueError, match="History fixture"):
        _history_fixture(201)


def test_seeded_history_prints_only_before_plotting(monkeypatch: pytest.MonkeyPatch) -> None:
    writes: list[str] = []
    flushed = [False]

    class Output:
        def write(self, value: str) -> None:
            writes.append(value)

        def flush(self) -> None:
            flushed[0] = True

    monkeypatch.setattr("scripts.phase3_native_macos_resize.sys.stdout", Output())
    _seed_history(0)
    assert writes == []
    assert not flushed[0]
    _seed_history(2)
    assert len(writes) == 1
    assert writes[0] == _history_fixture(2)
    assert flushed[0]


def _history_behind_plot(path: Path, *, include_trailing_text: bool) -> None:
    """Synthetic screenshot with bars and optional reflowed glyphs below."""
    image = Image.new("RGB", (640, 380), (40, 45, 48))
    draw = ImageDraw.Draw(image)
    draw.rectangle((25, 150, 600, 252), fill="white")
    draw.rectangle((55, 172, 260, 233), fill="red")
    draw.rectangle((300, 166, 555, 233), fill="blue")
    if include_trailing_text:
        # The actual Kitty fixture prints all of its history *before* plotting.
        # Seeing glyphs after the figure therefore diagnoses misplaced history.
        glyph_font = ImageFont.load_default(size=20)
        draw.text((10, 278), "WSKR_HISTORY_0095 " + "=" * 48, fill="white", font=glyph_font)
        draw.text((10, 313), "=" * 60, fill="white", font=glyph_font)
    image.save(path)


def test_native_history_order_rejects_plot_overlapping_prior_history(tmp_path: Path) -> None:
    image = tmp_path / "overlap.png"
    _history_behind_plot(image, include_trailing_text=True)
    assert _history_text_below_plot(image, cell_height_px=27, raster_width=616)

    stage: dict = {"stage": "resized", "screenshot": str(image)}
    report = {
        "history_lines": 96,
        "visual_failures": [],
        "frames": [{"raster": [616, 137], "geometry": {"height_px": 1890, "rows": 70}}],
    }
    _record_history_order(report, stage)
    assert stage["history_after_plot"]
    assert len(report["visual_failures"]) == 1
    assert "reflowed history" in report["visual_failures"][0]


def test_history_order_keeps_clean_and_nonoverlapping_cases(tmp_path: Path) -> None:
    image = tmp_path / "clean.png"
    _history_behind_plot(image, include_trailing_text=False)
    assert not _history_text_below_plot(image, cell_height_px=27, raster_width=616)
    report = {
        "history_lines": 96,
        "visual_failures": [],
        "frames": [{"raster": [616, 137], "geometry": {"height_px": 1890, "rows": 70}}],
    }
    _record_history_order(report, {"stage": "resized", "screenshot": str(image)})
    assert report["visual_failures"] == []
    report["history_lines"] = 0
    _record_history_order(report, {"stage": "resized", "screenshot": str(image)})
    assert report["visual_failures"] == []


@pytest.mark.parametrize(
    ("mode", "height", "history_lines"),
    [("unmanaged", 2, 0), ("unmanaged", 6, 96), ("yabai", 2, 96)],
)
def test_native_resize_worker_uses_importable_module(
    tmp_path: Path, mode: str, height: int, history_lines: int
) -> None:
    argv = _worker_argv(
        tmp_path,
        mode=mode,
        height=height,
        clean_scrollback=True,
        history_lines=history_lines,
    )
    assert argv[:3] == [sys.executable, "-m", "scripts.phase3_native_macos_resize"]
    assert argv[3:11] == [
        "--worker",
        "--mode",
        mode,
        "--height",
        str(height),
        "--directory",
        str(tmp_path.resolve()),
        "--clean-scrollback",
    ]
    assert argv[11:] == (["--history-lines", str(history_lines)] if history_lines else [])


def test_native_resize_module_help_imports_without_kitty() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "scripts.phase3_native_macos_resize", "--help"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert "--clean-scrollback" in result.stdout
    assert "--history-lines" in result.stdout


def test_all_native_resize_just_recipes_launch_as_module() -> None:
    recipes = {
        "native-resize mode=",
        "native-resize-clean mode=",
        "native-resize-history mode=",
    }
    lines = (Path(__file__).resolve().parents[1] / "justfile").read_text(encoding="utf-8").splitlines()
    for recipe in recipes:
        line_index = next(i for i, line in enumerate(lines) if line.startswith(recipe))
        assert "uv run python -m scripts.phase3_native_macos_resize" in lines[line_index + 1]

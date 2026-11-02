"""Opt-in real macOS Kitty appearance and owned-theme acceptance.

Run in a disposable Kitty window, switch the window's actual light/dark
colors between stages and select that Kitty window for each screenshot.
Only this foreground test process performs terminal queries. Native GUI
screenshots require independent visual review even after protocol checks.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from scripts import phase3_native_control_bridge as native_control
from scripts.phase3_native_macos_resize import _capture, _clear_scrollback, _dialog, _save
from wskr.terminal.profile import Source, TerminalProfile

if TYPE_CHECKING:
    from wskr.terminal.profile import Value

_MIN_COLOR_CONTRAST = 4.5


def _sample(field: Value) -> dict:
    value = field.value
    if hasattr(value, "to_hex"):
        value = value.to_hex()
    return {"value": value, "source": str(field.source)}


def _profile_evidence(profile: TerminalProfile) -> dict:
    """Record bounded terminal measurements with explicit source provenance."""
    return {
        "background": _sample(profile.background),
        "foreground": _sample(profile.foreground),
        "opacity": _sample(profile.opacity),
        "font_family": _sample(profile.font_family),
        "font_size_pt": _sample(profile.font_size_pt),
        "dpi_x": _sample(profile.dpi_x),
        "dpi_y": _sample(profile.dpi_y),
        "cell_width_px": _sample(profile.cell_width_px),
        "cell_height_px": _sample(profile.cell_height_px),
        "is_dark": profile.is_dark,
    }


def _color_contrast(profile: TerminalProfile) -> float | None:
    """Measure text contrast only if both foreground/background are known."""
    foreground = profile.foreground.value
    background = profile.background.value
    if foreground is None or background is None:
        return None
    higher = max(foreground.luminance, background.luminance)
    lower = min(foreground.luminance, background.luminance)
    return (higher + 0.05) / (lower + 0.05)


def _check_appearance(report: dict, before: TerminalProfile, after: TerminalProfile, *, refreshed: bool) -> None:
    """Require measured, contrasting, genuinely different terminal themes."""
    for stage, profile in (("initial", before), ("changed", after)):
        for name in ("foreground", "background"):
            field = getattr(profile, name)
            if field.value is None or field.source != Source.MEASURED:
                report["failures"].append(f"{stage}: {name} not measured from owned Kitty query")
        contrast = _color_contrast(profile)
        report[f"{stage}_text_contrast"] = contrast
        if contrast is None or contrast < _MIN_COLOR_CONTRAST:
            report["failures"].append(f"{stage}: measured foreground/background contrast below 4.5:1")
    if before.is_dark is None or after.is_dark is None or before.is_dark == after.is_dark:
        report["failures"].append("Kitty did not report a genuine dark/light theme transition")
    if not refreshed:
        report["failures"].append("Live viewport did not refresh any backend-owned figure colors")


def _run(directory: Path, report: dict) -> None:
    import matplotlib as mpl  # ruff: ignore[import-outside-top-level]

    mpl.use("module://wskr.render.matplotlib.kitty")
    import matplotlib.pyplot as plt  # ruff: ignore[import-outside-top-level]

    from wskr.render.matplotlib.live import owned_viewport  # ruff: ignore[import-outside-top-level]
    from wskr.terminal import probe_owned_profile, use_profile  # ruff: ignore[import-outside-top-level]

    plt.ioff()
    unmatched = bytearray()

    _dialog("Set Kitty to a DARK color theme. Then click Continue to query and capture this window.")
    initial = probe_owned_profile(owns_input=True, on_unmatched=unmatched.extend, palette=False)
    report["initial_profile"] = _profile_evidence(initial)
    _save(report, directory)
    with use_profile(initial):
        fig, ax = plt.subplots()
        ax.plot([0, 1, 2], [0, 2, 1], color="orange")
        ax.set_title("Owned terminal title")
        ax.set_xlabel("Owned X label")
        ax.set_ylabel("Owned Y label")
        ax.grid(visible=True)
    source = (tuple(fig.get_size_inches()), fig.dpi)
    try:
        with owned_viewport(fig) as view:
            _capture(report, directory, "initial_dark")
            _dialog(
                "Change the SAME Kitty window's actual foreground/background to a LIGHT color theme, "
                "then click Continue. Do not switch to another terminal window."
            )
            after = probe_owned_profile(owns_input=True, on_unmatched=unmatched.extend, palette=False)
            report["changed_profile"] = _profile_evidence(after)
            report["theme_refreshed"] = view.refresh_theme(after)
            _save(report, directory)
            _capture(report, directory, "changed_light")
            _check_appearance(report, initial, after, refreshed=report["theme_refreshed"])
        _capture(report, directory, "restored_primary")
        if (tuple(fig.get_size_inches()), fig.dpi) != source:
            report["failures"].append("Backend changed source figure size or DPI")
    finally:
        plt.close("all")
        report["unmatched_reply_bytes"] = len(unmatched)
        _save(report, directory)


def _main(directory: Path, mode: str) -> int:
    directory.mkdir(parents=True, exist_ok=False)
    report: dict = {
        "mode": mode,
        "mode_is_label_only": True,
        "macos": platform.mac_ver()[0],
        "stages": [],
        "failures": [],
        "visual_review_required": True,
        "passed_protocol_checks": False,
    }
    _save(report, directory)
    try:
        _clear_scrollback()
        print("WSKR_APPEARANCE_PRIMARY_SENTINEL", flush=True)
        _run(directory, report)
    except (OSError, RuntimeError, ValueError, AssertionError, KeyboardInterrupt, TimeoutError):
        (directory / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        report["failures"].append("Native appearance coordination failed; see error.txt")
    finally:
        report["passed_protocol_checks"] = not report["failures"]
        _save(report, directory)
    archive = shutil.make_archive(str(directory), "zip", root_dir=directory)
    print(f"Evidence archive: {archive}")
    if report["failures"]:
        print(f"FAILED native appearance checks: {report['failures']}", file=sys.stderr)
        return 1
    print("Owned theme query/refresh checks passed; screenshot review remains required.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("unmanaged", "yabai"), required=True)
    args = parser.parse_args()
    if sys.platform != "darwin" or not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.error("Native macOS with foreground stdin and stdout Kitty TTY required")
    if not (os.getenv("KITTY_WINDOW_ID") or os.getenv("TERM") == "xterm-kitty"):
        parser.error("Run this in Kitty")
    if os.getenv("WSKR_FIT") != "contain":
        parser.error("Use WSKR_FIT=contain")
    if native_control.enabled():
        native_control.request("ready", case="appearance", mode=args.mode)
    directory = Path("artifacts/phase3-native-appearance") / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + f"-{args.mode}"
    )
    return _main(directory, args.mode)


if __name__ == "__main__":
    raise SystemExit(main())

"""Portable regression for owned native appearance evidence semantics."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.phase3_native_macos_appearance import _check_appearance, _color_contrast, _profile_evidence
from wskr.terminal.color import RGB
from wskr.terminal.profile import Source, TerminalProfile, Value

pytestmark = pytest.mark.medium


def _profile(*, dark: bool, measured: bool = True) -> TerminalProfile:
    source = Source.MEASURED if measured else Source.HINT
    background = RGB(12, 12, 12) if dark else RGB(245, 245, 245)
    foreground = RGB(245, 245, 245) if dark else RGB(12, 12, 12)
    return TerminalProfile(
        foreground=Value(foreground, source),
        background=Value(background, source),
        font_family=Value("Terminal Font", Source.MEASURED),
        font_size_pt=Value(12.0, Source.MEASURED),
    )


def test_profile_evidence_preserves_values_and_provenance() -> None:
    report = _profile_evidence(_profile(dark=True))
    assert report["background"] == {"value": "#0c0c0c", "source": "measured"}
    assert report["foreground"] == {"value": "#f5f5f5", "source": "measured"}
    assert report["font_family"]["value"] == "Terminal Font"
    assert report["is_dark"] is True
    assert report["opacity"] == {"value": None, "source": "unknown"}


def test_opposite_measured_themes_and_contrast_qualify() -> None:
    before, after = _profile(dark=True), _profile(dark=False)
    report: dict = {"failures": []}
    _check_appearance(report, before, after, refreshed=True)
    assert report["failures"] == []
    assert report["initial_text_contrast"] == pytest.approx(_color_contrast(before))
    assert report["changed_text_contrast"] >= 4.5


def test_unmeasured_or_unchanged_appearance_does_not_qualify() -> None:
    before, after = _profile(dark=True), _profile(dark=True, measured=False)
    report: dict = {"failures": []}
    _check_appearance(report, before, after, refreshed=False)
    assert any("not measured" in failure for failure in report["failures"])
    assert any("genuine dark/light" in failure for failure in report["failures"])
    assert any("did not refresh" in failure for failure in report["failures"])


def test_native_appearance_module_help_does_not_require_macos(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "scripts.phase3_native_macos_appearance", "--help"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--mode" in result.stdout

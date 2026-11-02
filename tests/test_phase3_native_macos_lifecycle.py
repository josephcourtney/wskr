"""Pure acceptance checks for the native two-figure lifecycle harness."""

from __future__ import annotations

import pytest

from scripts.phase3_native_macos_lifecycle import _assess_stage, _require_uploads

pytestmark = pytest.mark.medium


def test_two_live_figures_with_both_colors_visible_pass() -> None:
    report: dict = {"visual_failures": []}
    _assess_stage(
        report,
        {"stage": "pumped", "colors": {"red": 25000, "blue": 36000}},
        red=True,
        blue=True,
    )
    assert report["visual_failures"] == []


def test_closing_red_preserves_blue_and_rejects_residual_red() -> None:
    report: dict = {"visual_failures": []}
    _assess_stage(
        report,
        {"stage": "after_red_close", "colors": {"red": 500, "blue": 12000}},
        red=False,
        blue=True,
    )
    assert report["visual_failures"] == []
    _assess_stage(
        report,
        {"stage": "after_red_close", "colors": {"red": 12000, "blue": 300}},
        red=False,
        blue=True,
    )
    assert len(report["visual_failures"]) == 2
    assert "closed red figure remains" in report["visual_failures"][0]
    assert "missing blue figure" in report["visual_failures"][1]


def test_closing_both_clears_all_visible_bars() -> None:
    report: dict = {"visual_failures": []}
    _assess_stage(
        report,
        {"stage": "after_blue_close", "colors": {"red": 0, "blue": 0}},
        red=False,
        blue=False,
    )
    assert report["visual_failures"] == []
    _assess_stage(
        report,
        {"stage": "after_child_exit", "colors": {"red": 900, "blue": 900}},
        red=False,
        blue=False,
    )
    assert len(report["visual_failures"]) == 2


def test_single_pump_requires_one_new_upload_per_live_figure() -> None:
    report: dict = {"uploads": {"red": 2, "blue": 2}}
    _require_uploads(report, {"red": 2, "blue": 2}, "pumped")
    with pytest.raises(AssertionError, match="pumped"):
        _require_uploads({"uploads": {"red": 2, "blue": 1}}, {"red": 2, "blue": 2}, "pumped")
    with pytest.raises(AssertionError, match="queued"):
        _require_uploads({"uploads": {"red": 2, "blue": 1}}, {"red": 1, "blue": 1}, "queued")

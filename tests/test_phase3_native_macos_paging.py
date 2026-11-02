"""Portable checks for the opt-in native blocking paging evidence harness."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from scripts.phase3_native_macos_paging import (
    _COLORS,
    _argument_parser,
    _check_page,
    _color_pixels,
    _expanded_geometry,
    _figure_count,
    _figures_on_page,
    _palette,
    _small_geometry,
    _start_geometry,
    _validate_worker,
    _worker_argv,
)
from wskr.render.matplotlib.sheet import plan_sheet_pages
from wskr.terminal.profile import Geometry

pytestmark = pytest.mark.medium


def _stage(path: Path, geometry: Geometry, *, name: str = "page") -> dict:
    return {
        "stage": name,
        "screenshot": str(path),
        "geometry": {
            "rows": geometry.rows,
            "columns": geometry.columns,
            "width_px": geometry.width_px,
            "height_px": geometry.height_px,
        },
    }


def test_measured_resize_changes_paging_capacity() -> None:
    wide = Geometry(21, 80, 1120, 567)
    narrow = Geometry(21, 40, 560, 567)
    initial = plan_sheet_pages(len(_COLORS), wide)
    small = plan_sheet_pages(len(_COLORS), narrow)
    assert initial.columns == 2
    assert small.columns == 1
    assert initial.page_size > small.page_size
    assert initial.total_pages < small.total_pages
    assert _figures_on_page(wide, 1) == list(range(initial.page_size, min(initial.page_size * 2, len(_COLORS))))
    assert _figures_on_page(narrow, 1) == list(range(small.page_size, min(small.page_size * 2, len(_COLORS))))


def test_page_colors_detect_missing_and_unexpected_tiles(tmp_path: Path) -> None:
    geometry = Geometry(21, 80, 1120, 567)
    expected = _figures_on_page(geometry, 0)
    pixels = np.zeros((567, 1120, 3), dtype=np.uint8)
    for index in expected:
        x0 = index * 100
        pixels[40:160, x0 : x0 + 100] = _COLORS[index][1]
    path = tmp_path / "complete.png"
    Image.fromarray(pixels).save(path)
    assert all(_color_pixels(path)[i] >= 12000 for i in expected)
    report: dict = {"failures": []}
    stage = _stage(path, geometry)
    _check_page(report, stage, 0)
    assert report["failures"] == []
    assert stage["expected_figures"] == expected

    pixels[40:160, :100] = 0
    pixels[200:320, :100] = _COLORS[-1][1]
    Image.fromarray(pixels).save(path)
    report = {"failures": []}
    _check_page(report, _stage(path, geometry), 0)
    assert "expected figure 1" in report["failures"][0]
    assert "unexpected figure 9" in report["failures"][1]


def test_worker_uses_same_importable_module_and_dedicated_pipe(tmp_path: Path) -> None:
    assert _worker_argv(17, tmp_path) == [
        sys.executable,
        "-m",
        "scripts.phase3_native_macos_paging",
        "--mode",
        "unmanaged",
        "--worker",
        "--event-fd",
        "17",
        "--directory",
        str(tmp_path.resolve()),
        "--figure-count",
        "9",
    ]


@pytest.mark.parametrize("mode", ["unmanaged", "yabai"])
def test_native_paging_worker_argv_satisfies_real_argument_parser(tmp_path: Path, mode: str) -> None:
    """Catch omissions of parser-required flags before native GUI testing."""
    argv = _worker_argv(17, tmp_path, 13, mode=mode)
    args = _argument_parser().parse_args(argv[3:])
    assert args.mode == mode
    assert args.worker is True
    assert args.event_fd == 17
    assert args.directory == tmp_path.resolve()
    assert args.figure_count == 13


def test_native_paging_module_cli_starts_without_gui(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    done = subprocess.run(
        [sys.executable, "-m", "scripts.phase3_native_macos_paging", "--help"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert "--mode" in done.stdout
    assert "--worker" not in done.stdout


def test_incomplete_paging_evidence_is_reported_without_indexing_missing_frames() -> None:
    report: dict = {"failures": []}
    _validate_worker(report, {"finished": False, "frames": [{"raster": [1000, 400]}]})
    assert len(report["failures"]) == 1
    assert "six contact-sheet frames" in report["failures"][0]


def test_paging_worker_checks_raster_and_viewport_shrink() -> None:
    frames = [
        {"raster": [1000, 400], "geometry": {"width_px": 1120}},
        {"raster": [1000, 400], "geometry": {"width_px": 1120}},
        {"raster": [1000, 400], "geometry": {"width_px": 1120}},
        {"raster": [560, 400], "geometry": {"width_px": 560}},
        {"raster": [560, 400], "geometry": {"width_px": 560}},
        {"raster": [1000, 400], "geometry": {"width_px": 1120}},
    ]
    report: dict = {"failures": []}
    _validate_worker(report, {"finished": True, "frames": frames})
    assert report["failures"] == []

    frames[3]["raster"][0] = 1000
    frames[4]["raster"][0] = 1000
    report = {"failures": []}
    _validate_worker(report, {"finished": True, "frames": frames})
    assert report["failures"] == ["Narrowing the terminal did not reduce transmitted PNG width"]


def test_tall_native_window_creates_multiple_pages_without_forcing_small_height() -> None:
    """70-row native Kitty windows were impossible under the old height limit."""
    for geometry in (Geometry(70, 168, 2352, 1890), Geometry(34, 118, 1652, 918)):
        count = _figure_count(geometry)
        plan = plan_sheet_pages(count, geometry)
        assert count > plan.page_size
        assert plan.total_pages >= 2
        palette = _palette(count)
        assert len(palette) == count
        assert len({rgb for _, rgb in palette}) == count


def test_geometry_checks_accept_real_cell_sizes_without_exact_pixel_intervals(monkeypatch) -> None:
    wide = Geometry(70, 168, 2352, 1890)
    narrow = Geometry(70, 62, 868, 1890)
    expanded = Geometry(70, 153, 2142, 1890)
    scenarios = iter((wide, narrow, expanded))

    def emulate_dialog(_message, predicate):
        geometry = next(scenarios)
        assert predicate(geometry)
        return geometry

    monkeypatch.setattr("scripts.phase3_native_macos_paging._until_valid", emulate_dialog)
    assert _start_geometry() == wide
    assert _small_geometry(wide) == narrow
    assert _expanded_geometry(wide) == expanded


def test_figure_count_also_preserves_navigation_in_one_column_tall_window() -> None:
    window = Geometry(70, 68, 952, 1890)
    count = _figure_count(window)
    plan = plan_sheet_pages(count, window)
    assert plan.columns == 1
    assert plan.total_pages >= 2
    assert _figures_on_page(window, 1, count)


def test_intermediate_drag_frames_do_not_fail_paging_validation() -> None:
    frames = [
        {"raster": [900, 400], "geometry": {"width_px": 1000}},
        {"raster": [900, 400], "geometry": {"width_px": 1000}},
        {"raster": [900, 400], "geometry": {"width_px": 1000}},
        {"raster": [800, 400], "geometry": {"width_px": 800}},
        {"raster": [600, 400], "geometry": {"width_px": 600}},
        {"raster": [600, 400], "geometry": {"width_px": 600}},
        {"raster": [900, 400], "geometry": {"width_px": 1000}},
    ]
    report: dict = {"failures": []}
    _validate_worker(report, {"finished": True, "frames": frames})
    assert report["failures"] == []


def test_color_profile_shifted_native_screenshot_keeps_all_page_tiles(tmp_path: Path) -> None:
    """Synthetic ColorSync-like shifts must not erase real figures from checks."""
    background = (50, 56, 60)
    # Representative transformed RGB values measured from a native Kitty
    # screenshot, not a committed copy of the user's window.
    measured = (
        (218, 60, 74),
        (69, 138, 213),
        (97, 184, 111),
        (220, 143, 64),
        (142, 79, 206),
        (89, 178, 173),
        (214, 205, 86),
        (189, 96, 138),
    )
    geometry = Geometry(18, 160, 2240, 486)
    for page in (0, 1):
        pixels = np.empty((486, 1000, 3), dtype=np.uint8)
        pixels[:] = background
        for offset, index in enumerate(range(page * 4, page * 4 + 4)):
            x = 40 + offset * 230
            pixels[75:225, x : x + 180, :] = measured[index]
        path = tmp_path / f"page-{page}.png"
        Image.fromarray(pixels).save(path)
        report: dict = {"failures": []}
        stage = _stage(path, geometry)
        _check_page(report, stage, page)
        assert report["failures"] == []
        assert all(stage["color_pixels"][i] >= 1300 for i in range(page * 4, page * 4 + 4))
        assert all(
            stage["color_pixels"][i] < 600 for i in range(9) if i not in range(page * 4, page * 4 + 4)
        )


def test_profile_tolerant_detector_rejects_blank_and_ghost_tile(tmp_path: Path) -> None:
    background = (50, 56, 60)
    pixels = np.empty((486, 1000, 3), dtype=np.uint8)
    pixels[:] = background
    blank = tmp_path / "blank.png"
    Image.fromarray(pixels).save(blank)
    assert _color_pixels(blank, count=20) == [0] * 20

    # A wrong-page colored tile must still be detected.
    pixels[100:250, 50:250, :] = (142, 79, 206)
    wrong = tmp_path / "wrong.png"
    Image.fromarray(pixels).save(wrong)
    report: dict = {"failures": [], "figure_count": 9}
    _check_page(report, _stage(wrong, Geometry(18, 160, 2240, 486)), 0)
    assert any("unexpected figure 5" in failure for failure in report["failures"])
    assert any("expected figure 1" in failure for failure in report["failures"])


def test_generated_extra_colors_are_bright_and_separated_from_terminal_background() -> None:
    palette = _palette(20)
    assert len(palette) == 20
    assert len({rgb for _, rgb in palette}) == 20
    background = np.asarray((50, 56, 60), dtype=np.int32)
    for _, rgb in palette[9:]:
        channels = np.asarray(rgb, dtype=np.int32)
        assert int(np.sum((channels - background) ** 2)) > 80**2
        assert max(rgb) >= 192

"""Portable controller checks: no native GUI processes are launched here."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import numpy as np
import pytest
from PIL import Image

from scripts import phase3_owned_live_automated_controller as gui

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.medium


def _bars(path: Path) -> None:
    pixels = np.full((120, 180, 3), 50, dtype=np.uint8)
    pixels[10:100, 10:83] = (255, 0, 0)
    pixels[10:100, 95:168] = (0, 0, 255)
    Image.fromarray(pixels).save(path)


def test_color_accounting_and_blank_capture(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "test.png"
    _bars(path)
    monkeypatch.setattr(gui, "_remote", lambda _socket, *_args: "")
    bars = gui._capture("unix:/tmp/mock", 1, path)
    assert bars["red"] > 5000
    assert bars["blue"] > 5000
    assert bars["width_px"] == 180
    Image.new("RGB", (120, 120), "black").save(path)
    blank = gui._capture("unix:/tmp/mock", 1, path)
    assert blank["black_fraction"] > 0.99


def test_isolated_kitty_window_id(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = json.dumps([{"tabs": [{"windows": [{"id": 17}]}]}])
    monkeypatch.setattr(gui, "_remote", lambda _socket, *_args: payload)
    assert gui._window_id("unix:/tmp/mock") == 17


def test_multiple_window_ids_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = json.dumps([{"tabs": [{"windows": [{"id": 1}, {"id": 2}]}]}])
    monkeypatch.setattr(gui, "_remote", lambda _socket, *_args: payload)
    with pytest.raises(gui.AcceptanceError, match="one isolated Kitty window"):
        gui._window_id("unix:/tmp/mock")


def test_unmanaged_resize_is_kitty_remote(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    monkeypatch.setattr(gui, "_remote", lambda _socket, *args: calls.append(args) or "")
    method = gui._resize("unix:/tmp/mock", 4, "test", mode="unmanaged", small=True, height=2)
    assert method == "kitty_remote"
    assert "resize-os-window" in calls[0]
    assert "--width" in calls[0]


def test_yabai_floating_uses_absolute_resize(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gui, "_query_yabai", lambda _title: {"id": 22, "is-floating": True})
    calls = []
    monkeypatch.setattr(gui, "_run", lambda args, **_kwargs: calls.append(args) or "")
    assert gui._resize("socket", 1, "test", mode="yabai", small=True, height=6) == "yabai_float_absolute"
    assert "abs:720:740" in calls[0]


def test_yabai_bsp_uses_correct_axis_and_child_ratio(monkeypatch: pytest.MonkeyPatch) -> None:
    # Vertical BSP splits control width; second-child share is 1 - ratio.
    window = {"id": 1311, "is-floating": False, "split-type": "vertical", "split-child": "second_child"}
    monkeypatch.setattr(gui, "_query_yabai", lambda _title: window)
    calls = []
    monkeypatch.setattr(gui, "_run", lambda args, **_kwargs: calls.append(args) or "")
    monkeypatch.setattr(gui, "_remote", lambda *_args: pytest.fail("Kitty fallback bypassed yabai"))
    assert gui._resize("socket", 1, "test", mode="yabai-bsp", small=True, height=2) == "yabai_bsp_ratio"
    assert calls[0] == ["yabai", "-m", "window", "1311", "--ratio", "abs:0.75"]
    assert gui._resize("socket", 1, "test", mode="yabai-bsp", small=False, height=2) == "yabai_bsp_ratio"
    assert calls[1][-1] == "abs:0.25"


def test_yabai_horizontal_bsp_is_not_mistaken_for_width_split(monkeypatch: pytest.MonkeyPatch) -> None:
    # Real 7.1.25 evidence: horizontal split only changed physical height.
    window = {"id": 1599, "is-floating": False, "split-type": "horizontal", "split-child": "second_child"}
    monkeypatch.setattr(gui, "_query_yabai", lambda _title: window)
    monkeypatch.setattr(gui, "_run", lambda *_args, **_kwargs: pytest.fail("Must not mutate horizontal split"))
    with pytest.raises(gui.UnsupportedLayoutError, match="vertical split"):
        gui._resize("socket", 1, "test", mode="yabai-bsp", small=True, height=6)


def test_unsupported_bsp_is_skipped_without_false_pass() -> None:
    report = {"failures": [], "skip_reason": "horizontal split"}
    assert gui._report_status(report) == "SKIP"
    report["failures"].append("rendering failure")
    assert gui._report_status(report) == "SKIP"
    report.pop("skip_reason")
    assert gui._report_status(report) == "FAIL"
    report["failures"].clear()
    assert gui._report_status(report) == "PASS"


def test_yabai_without_bsp_split_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        gui,
        "_query_yabai",
        lambda _title: {"id": 33, "is-floating": False, "split-type": "none", "split-child": "none"},
    )
    monkeypatch.setattr(gui, "_run", lambda *_args, **_kwargs: pytest.fail("Cannot resize without a BSP split"))
    with pytest.raises(gui.AcceptanceError, match="split-type='none'"):
        gui._resize("socket", 1, "test", mode="yabai-bsp", small=False, height=6)


def test_prepare_yabai_floating_waits_for_accessibility(monkeypatch: pytest.MonkeyPatch) -> None:
    # The first response reproduces yabai's incomplete new-window placeholder.
    windows = iter([
        {"id": 1585, "is-floating": False, "is-visible": False, "has-ax-reference": False},
        {"id": 1585, "is-floating": False, "is-visible": True, "has-ax-reference": True},
        {"id": 1585, "is-floating": True, "is-visible": True, "has-ax-reference": True},
    ])
    calls = []
    monkeypatch.setattr(gui, "_query_yabai", lambda _title: next(windows))
    monkeypatch.setattr(gui, "_run", lambda args, **_kwargs: calls.append(args) or "")
    monkeypatch.setattr(gui.time, "sleep", lambda _delay: None)
    window = gui._prepare_yabai_floating("isolated-test")
    assert window["is-floating"]
    assert ["yabai", "-m", "window", "1585", "--toggle", "float"] in calls


def test_frame_width_assertion_and_restoration(tmp_path: Path) -> None:
    frames = [{"raster": [900, 200]}, {"raster": [600, 134]}, {"raster": [900, 200]}]
    (tmp_path / "worker-report.json").write_text(json.dumps({"frames": frames}), encoding="utf-8")
    report = {
        "stages": [
            {"red": 0, "blue": 0},
            {"red": 1, "blue": 1},
            {"red": 1, "blue": 1},
            {"red": 0, "blue": 0},
        ],
        "failures": [],
    }
    gui._verify(report, tmp_path)
    assert not report["failures"]
    report["stages"][-1]["red"] = 9000
    gui._verify(report, tmp_path)
    assert report["failures"]


def test_retina_calibration_uses_physical_pixel_measurement() -> None:
    # Requested 1200 -> 2394 physical pixels, so 720 physical needs ~361 units.
    width = gui._calibrated_request(requested=1200, observed=2394, target=720)
    assert 350 <= width <= 370
    assert gui._calibrated_request(requested=1200, observed=1200, target=720) == 720


def test_small_resize_rechecks_physical_screen_width(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    requests: list[int] = []
    widths = iter([900, 705])  # first attempt remained too wide, second fits

    def fake_resize(*_args, requested_width: int, **_kwargs) -> str:
        requests.append(requested_width)
        return "kitty_remote"

    def fake_measure(*_args, **_kwargs) -> dict:
        return {"width_px": next(widths), "height_px": 1000}

    monkeypatch.setattr(gui, "_resize", fake_resize)
    monkeypatch.setattr(gui, "_wait_new_width", fake_measure)
    attempts = gui._resize_to_fit(
        "socket", 1, "test", mode="unmanaged", height=2, wide_measurement={"width_px": 2394}, out=tmp_path / "probe.png"
    )
    assert len(attempts) == 2
    assert requests[1] < requests[0]
    assert attempts[-1]["observed_width_px"] == 705


def test_bsp_layout_fails_cleanly_if_it_cannot_fit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(gui, "_resize", lambda *_args, **_kwargs: "yabai_bsp_ratio")
    monkeypatch.setattr(gui, "_wait_new_width", lambda *_args, **_kwargs: {"width_px": 1350, "height_px": 800})
    with pytest.raises(gui.AcceptanceError, match="Could not reach a fitted physical width"):
        gui._resize_to_fit(
            "socket", 1, "test", mode="yabai", height=6, wide_measurement={"width_px": 2394}, out=tmp_path / "probe.png"
        )


def test_yabai_service_unavailable_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gui.shutil, "which", lambda command: "/usr/local/bin/yabai" if command == "yabai" else None)

    def fake_command(*_args, **_kwargs) -> str:
        msg = "failed to connect to socket"
        raise gui.AcceptanceError(msg)

    monkeypatch.setattr(gui, "_run", fake_command)
    status = gui._yabai_status()
    assert status is not None
    assert "failed to connect" in status

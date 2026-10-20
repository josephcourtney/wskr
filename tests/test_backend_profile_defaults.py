"""Standard Matplotlib backend initial sizing; display-time resizing is Phase 3."""

import matplotlib as mpl
import pytest

pytestmark = pytest.mark.medium

from wskr.render.matplotlib import core
from wskr.terminal.profile import Geometry, probe_profile


def test_backend_auto_uses_measured_pixels_without_mutating_rcparams(monkeypatch):
    profile = probe_profile(geometry=Geometry(30, 100, 1000, 600))
    monkeypatch.setattr(core, "probe_profile", lambda: profile)
    monkeypatch.setitem(mpl.rcParams, "figure.figsize", mpl.rcParamsDefault["figure.figsize"])
    monkeypatch.setitem(mpl.rcParams, "figure.dpi", 100)
    original = tuple(mpl.rcParams["figure.figsize"])
    manager = core._BackendTermAgg.new_figure_manager(901)
    try:
        width, height = manager.canvas.figure.get_size_inches()
        assert width == pytest.approx(9)
        assert height == pytest.approx(1.98)
        assert tuple(mpl.rcParams["figure.figsize"]) == original
    finally:
        manager.destroy()


def test_explicit_figsize_and_dpi_remain_authoritative(monkeypatch):
    monkeypatch.setattr(core, "probe_profile", lambda: probe_profile(geometry=Geometry(30, 100, 1000, 600)))
    manager = core._BackendTermAgg.new_figure_manager(902, figsize=(7, 3), dpi=125)
    try:
        assert tuple(manager.canvas.figure.get_size_inches()) == (7, 3)
        assert manager.canvas.figure.dpi == 125
    finally:
        manager.destroy()


def test_nondefault_matplotlib_style_figsize_is_respected(monkeypatch):
    monkeypatch.setattr(core, "probe_profile", lambda: probe_profile(geometry=Geometry(30, 100, 1000, 600)))
    monkeypatch.setitem(mpl.rcParams, "figure.figsize", [6, 3])
    manager = core._BackendTermAgg.new_figure_manager(903)
    try:
        assert tuple(manager.canvas.figure.get_size_inches()) == (6, 3)
    finally:
        manager.destroy()

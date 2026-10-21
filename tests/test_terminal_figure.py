"""Test that ordinary pyplot figures get backend-owned terminal style defaults.

The tests never send OSC or Kitty escape traffic and do not depend on a GUI.
"""

from __future__ import annotations

import matplotlib as mpl
import pytest
from matplotlib.figure import Figure

from wskr.render.matplotlib import core
from wskr.render.matplotlib.figure import TerminalFigure
from wskr.render.matplotlib.theme import resolve_rc_defaults
from wskr.terminal.profile import Geometry, probe_profile

pytestmark = pytest.mark.medium


def _profile(*, background: str = "0000", foreground: str = "ffff"):
    palette = (
        "ffff/ffff/ffff",
        "0000/0000/0000",
        "ffff/0000/0000",
        "0000/ffff/0000",
        "0000/0000/ffff",
        "ffff/ffff/0000",
        "0000/ffff/ffff",
        "ffff/0000/ffff",
    )

    def reply(request: bytes) -> bytes:
        if request.startswith(b"\x1b]10;"):
            return f"\x1b]10;rgb:{foreground}/{foreground}/{foreground}\x07".encode()
        if request.startswith(b"\x1b]11;"):
            return f"\x1b]11;rgb:{background}/{background}/{background}\x07".encode()
        index = int(request.split(b";")[1])
        return f"\x1b]4;{index};rgb:{palette[index % len(palette)]}\x07".encode()

    return probe_profile(
        geometry=Geometry(30, 100, 1000, 600), color_query=reply, palette=True
    )


def test_pyplot_none_arguments_get_terminal_dimensions_and_colors(monkeypatch):
    profile = _profile()
    monkeypatch.setattr(core, "probe_profile", lambda: profile)
    monkeypatch.setitem(mpl.rcParams, "figure.figsize", mpl.rcParamsDefault["figure.figsize"])
    monkeypatch.setitem(mpl.rcParams, "figure.facecolor", mpl.rcParamsDefault["figure.facecolor"])
    monkeypatch.setitem(mpl.rcParams, "axes.facecolor", mpl.rcParamsDefault["axes.facecolor"])
    monkeypatch.setitem(mpl.rcParams, "axes.prop_cycle", mpl.rcParamsDefault["axes.prop_cycle"])
    before = mpl.rcParams.copy()
    manager = core._BackendTermAgg.new_figure_manager(
        1001, figsize=None, dpi=None, facecolor=None, FigureClass=Figure
    )
    try:
        fig = manager.canvas.figure
        assert isinstance(fig, TerminalFigure)
        assert tuple(fig.get_size_inches()) == pytest.approx((9, 1.98))
        assert fig.get_facecolor() == mpl.colors.to_rgba("#000000")

        ax = fig.add_subplot(111)
        assert ax.get_facecolor() == mpl.colors.to_rgba("#000000")
        assert ax.xaxis.label.get_color() == "#ffffff"
        assert ax.title.get_color() == "#ffffff"
        color = ax.plot([0, 1], [1, 2])[0].get_color()
        assert color in resolve_rc_defaults(profile)["axes.prop_cycle"].by_key()["color"]
        assert fig.suptitle("Terminal title").get_color() == "#ffffff"
        assert fig.text(0.5, 0.5, "caption").get_color() == "#ffffff"
        assert mpl.rcParams == before
    finally:
        manager.destroy()


def test_user_figure_arguments_and_artist_edits_win(monkeypatch):
    monkeypatch.setattr(core, "probe_profile", _profile)
    manager = core._BackendTermAgg.new_figure_manager(
        1002, figsize=(7, 3), facecolor="#112233"
    )
    try:
        fig = manager.canvas.figure
        assert tuple(fig.get_size_inches()) == (7, 3)
        assert fig.get_facecolor() == mpl.colors.to_rgba("#112233")
        ax = fig.add_subplot(111, facecolor="#332211")
        assert ax.get_facecolor() == mpl.colors.to_rgba("#332211")
        line = ax.plot([0, 1], [1, 2], color="orange")[0]
        assert line.get_color() == "orange"
        ax.set_title("Specific color", color="cyan")
        assert ax.title.get_color() == "cyan"
    finally:
        manager.destroy()


def test_custom_figure_subclass_never_replaced(monkeypatch):
    class CustomFigure(Figure):
        pass

    monkeypatch.setattr(core, "probe_profile", _profile)
    manager = core._BackendTermAgg.new_figure_manager(1003, FigureClass=CustomFigure)
    try:
        assert type(manager.canvas.figure) is CustomFigure
    finally:
        manager.destroy()


def test_custom_global_style_disables_that_terminal_default(monkeypatch):
    monkeypatch.setattr(core, "probe_profile", _profile)
    monkeypatch.setitem(mpl.rcParams, "axes.facecolor", "#202020")
    manager = core._BackendTermAgg.new_figure_manager(1004)
    try:
        ax = manager.canvas.figure.add_subplot(111)
        assert ax.get_facecolor() == mpl.colors.to_rgba("#202020")
    finally:
        manager.destroy()


def test_new_global_style_after_figure_creation_is_authoritative(monkeypatch):
    monkeypatch.setattr(core, "probe_profile", _profile)
    monkeypatch.setitem(mpl.rcParams, "axes.facecolor", mpl.rcParamsDefault["axes.facecolor"])
    manager = core._BackendTermAgg.new_figure_manager(1005)
    try:
        monkeypatch.setitem(mpl.rcParams, "axes.facecolor", "#ededed")
        ax = manager.canvas.figure.add_axes((0.1, 0.1, 0.8, 0.8))
        assert ax.get_facecolor() == mpl.colors.to_rgba("#ededed")
    finally:
        manager.destroy()


def test_unknown_background_cannot_choose_contrast_checked_palette():
    profile = probe_profile(geometry=Geometry(25, 80, 800, 500))
    assert "axes.prop_cycle" not in resolve_rc_defaults(profile)


def test_contrast_filter_removes_background_color_and_duplicates():
    profile = _profile(background="ffff", foreground="0000")
    colors = resolve_rc_defaults(profile)["axes.prop_cycle"].by_key()["color"]
    assert "#ffffff" not in colors
    assert len(colors) == len(set(colors))
    assert "#000000" in colors

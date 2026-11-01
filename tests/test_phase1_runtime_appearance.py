"""Runtime terminal appearance is opt-in, locally scoped, and user-style safe."""

from __future__ import annotations

import matplotlib as mpl
import pytest

from wskr.render.matplotlib import core
from wskr.render.matplotlib.theme import resolve_rc_defaults
from wskr.terminal import current_profile, use_profile
from wskr.terminal.profile import Geometry, probe_owned_profile, probe_profile

pytestmark = pytest.mark.medium


def _profile(foreground: str, background: str):
    def query(request: bytes) -> bytes:
        code = 10 if request.startswith(b"\x1b]10;") else 11
        color = foreground if code == 10 else background
        return f"\x1b]{code};rgb:{color[0:2]}/{color[2:4]}/{color[4:6]}\x07".encode()

    return probe_profile(geometry=Geometry(30, 100, 1000, 600), color_query=query)


def test_scoped_profile_changes_only_new_figures_not_existing_artists(monkeypatch):
    dark = _profile("ffffff", "000000")
    light = _profile("000000", "ffffff")
    monkeypatch.setattr(core, "probe_profile", lambda: pytest.fail("queried unowned TTY"))
    with mpl.rc_context():
        mpl.rcdefaults()
        original = dict(mpl.rcParams)
        with use_profile(dark):
            manager1 = core._BackendTermAgg.new_figure_manager(7801)
            figure1 = manager1.canvas.figure
            ax1 = figure1.add_subplot(111)
            ax1.set_title("backend-owned")
            explicit = ax1.plot([0, 1], [0, 1], color="red")[0]
            assert figure1.get_facecolor() == mpl.colors.to_rgba("#000000")
            assert ax1.title.get_color() == "#ffffff"
            assert explicit.get_color() == "red"
            with use_profile(light):
                manager2 = core._BackendTermAgg.new_figure_manager(7802)
                figure2 = manager2.canvas.figure
                ax2 = figure2.add_subplot(111)
                assert figure2.get_facecolor() == mpl.colors.to_rgba("#ffffff")
                assert ax2.title.get_color() == "#000000"
            assert current_profile() is dark
        assert current_profile() is None
        assert figure1.get_facecolor() == mpl.colors.to_rgba("#000000")
        assert ax1.title.get_color() == "#ffffff"
        assert dict(mpl.rcParams) == original
        manager1.destroy()
        manager2.destroy()


def test_user_rcparams_and_explicit_artist_properties_win(monkeypatch):
    monkeypatch.setattr(core, "probe_profile", lambda: pytest.fail("unowned query"))
    with mpl.rc_context():
        mpl.rcdefaults()
        mpl.rcParams["axes.labelcolor"] = "orange"
        with use_profile(_profile("ffffff", "000000")):
            manager = core._BackendTermAgg.new_figure_manager(7803, figsize=(7, 3), facecolor="magenta")
            try:
                fig = manager.canvas.figure
                ax = fig.add_subplot(111)
                ax.set_xlabel("user choice")
                assert tuple(fig.get_size_inches()) == (7, 3)
                assert fig.get_facecolor() == mpl.colors.to_rgba("magenta")
                assert ax.xaxis.label.get_color() == "orange"
                assert ax.text(0, 0, "explicit", color="lime").get_color() == "lime"
            finally:
                manager.destroy()


def test_runtime_font_and_cell_geometry_scale_without_physical_dpi():
    prof = probe_profile(
        geometry=Geometry(30, 100, 1000, 600),
        kitty_query=lambda field: (
            (
                b"\x1bP1+r"
                + f"kitty-query-{field}".encode().hex().encode()
                + b"="
                + ("240" if field in {"dpi_x", "dpi_y"} else "12").encode().hex().encode()
                + b"\x1b\\"
            )
            if field in {"dpi_x", "dpi_y", "font_size"}
            else b"invalid"
        ),
    )
    defaults = resolve_rc_defaults(prof, dpi=100)
    assert defaults["figure.dpi"] == 100
    assert prof.dpi_x.value == 240
    assert defaults["font.family"] == ["monospace"]
    assert defaults["lines.linewidth"] > 0
    assert defaults["lines.markersize"] > 0
    assert defaults["axes.linewidth"] > 0


def test_known_translucent_terminal_uses_transparent_backend_surfaces():
    def reply(field: str) -> bytes:
        name = f"kitty-query-{field}".encode().hex().encode()
        value = {"background": "#151515", "foreground": "#efefef", "background_opacity": "0.5"}
        if field not in value:
            return b"invalid"
        return b"\x1bP1+r" + name + b"=" + value[field].encode().hex().encode() + b"\x1b\\"

    prof = probe_profile(geometry=Geometry(25, 80, 800, 500), kitty_query=reply)
    defaults = resolve_rc_defaults(prof)
    assert defaults["figure.facecolor"] == "none"
    assert defaults["axes.facecolor"] == "none"
    assert defaults["text.color"] == "#efefef"


def test_live_probe_refuses_unowned_input_without_query(monkeypatch):
    monkeypatch.setattr(core, "probe_profile", lambda: pytest.fail("unowned query"))
    with pytest.raises(RuntimeError, match="exclusive input"):
        probe_owned_profile()
    with pytest.raises(RuntimeError, match="same TTY"):
        probe_owned_profile(owns_input=True, on_unmatched=lambda _: None)


def test_owned_profile_integrates_osc_csi_and_kitty_callbacks(monkeypatch):
    from wskr.terminal import profile as terminal_profile

    calls = []
    unmatched = []

    def osc(request, **options):
        calls.append(("osc", request, options["owns_input"]))
        return b"\x1b]11;rgb:0000/0000/0000\x07" if request.startswith(b"\x1b]11") else b"invalid"

    def csi(request, **options):
        calls.append(("csi", request, options["owns_input"]))
        return b"\x1b[6;20;10t"

    def kitty(field, **options):
        calls.append(("kitty", field, options["owns_input"]))
        name = f"kitty-query-{field}".encode().hex().encode()
        if field == "font_size":
            return b"\x1bP1+r" + name + b"=" + b"31322e35" + b"\x1b\\"
        return b"invalid"

    monkeypatch.setattr(terminal_profile, "_foreground_tty_owned", lambda: True)
    monkeypatch.setattr(terminal_profile, "read_geometry", lambda: Geometry(25, 80))
    monkeypatch.setattr(terminal_profile, "query_osc", osc)
    monkeypatch.setattr(terminal_profile, "query_csi", csi)
    monkeypatch.setattr(terminal_profile, "query_kitty_field", kitty)
    prof = probe_owned_profile(owns_input=True, on_unmatched=unmatched.extend, palette=False)
    assert prof.background.value is not None
    assert prof.background.value.to_hex() == "#000000"
    assert prof.font_size_pt.value == pytest.approx(12.5)
    assert prof.cell_height_px.value == 20
    assert all(item[2] is True for item in calls)
    assert len([item for item in calls if item[0] == "osc"]) == 2
    assert len([item for item in calls if item[0] == "kitty"]) == 7

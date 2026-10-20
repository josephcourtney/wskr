"""Pure terminal-to-Matplotlib default derivation tests."""

import matplotlib as mpl
import pytest

from wskr.render.matplotlib.theme import resolve_rc_defaults, suggested_figure_size
from wskr.terminal.profile import Geometry, probe_profile


def test_unmeasured_terminal_does_not_guess_theme_or_physical_size():
    unknown = probe_profile(geometry=Geometry(30, 80))
    assert suggested_figure_size(unknown) is None
    assert resolve_rc_defaults(unknown) == {}


def test_measured_terminal_geometry_scales_with_pixels():
    measured = probe_profile(geometry=Geometry(40, 100, 1000, 800))
    figure = suggested_figure_size(measured, dpi=100)
    assert figure is not None
    assert figure.width_in == pytest.approx(9)
    assert figure.height_in == pytest.approx(2.64)


def test_measured_color_produces_contrast_defaults_without_global_rc_change():
    original = dict(mpl.rcParams)
    result = probe_profile(
        geometry=Geometry(30, 80, 800, 600),
        color_query=lambda request: (
            b"\x1b]10;rgb:ffff/ffff/ffff\x07" if request.startswith(b"\x1b]10") else b"\x1b]11;rgb:0000/0000/0000\x07"
        ),
    )
    defaults = resolve_rc_defaults(result)
    assert defaults["figure.facecolor"] == "#000000"
    assert defaults["text.color"] == "#ffffff"
    assert defaults["font.size"] > 6
    assert dict(mpl.rcParams) == original


def test_explicit_values_exclude_backend_owned_defaults():
    profile = probe_profile(geometry=Geometry(30, 80, 800, 600))
    defaults = resolve_rc_defaults(
        profile,
        explicit={"figure.figsize": (7, 3), "figure.dpi": 200},
    )
    assert "figure.figsize" not in defaults
    assert "figure.dpi" not in defaults
    assert suggested_figure_size(profile, dpi=0) is None


def test_invalid_fraction_is_rejected():
    profile = probe_profile(geometry=Geometry(30, 80, 800, 600))
    with pytest.raises(ValueError, match="fractions"):
        suggested_figure_size(profile, width_fraction=2)


def test_import_wskr_does_not_change_matplotlib_rcparams():
    import importlib

    import wskr

    before = mpl.rcParams["text.usetex"]
    mpl.rcParams["text.usetex"] = True
    try:
        importlib.reload(wskr)
        assert mpl.rcParams["text.usetex"] is True
    finally:
        mpl.rcParams["text.usetex"] = before

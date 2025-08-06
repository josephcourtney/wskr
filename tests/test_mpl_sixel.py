import os

import pytest


def test_sixel_import_raises():
    with pytest.raises(
        ImportError, match="Sixel backend is not yet implemented. Set WSKR_ENABLE_SIXEL=true to bypass."
    ):
        import wskr.mpl.sixel  # noqa: PLC0415
    orig_wskr_enable_sixel = os.environ.get("WSKR_ENABLE_SIXEL")
    os.environ["WSKR_ENABLE_SIXEL"] = "true"
    import wskr.mpl.sixel  # noqa: PLC0415

    if orig_wskr_enable_sixel is not None:
        os.environ["WSKR_ENABLE_SIXEL"] = orig_wskr_enable_sixel

    assert wskr.mpl.sixel


def test_sixel_backend_show_raises():
    orig_wskr_enable_sixel = os.environ.get("WSKR_ENABLE_SIXEL")
    os.environ["WSKR_ENABLE_SIXEL"] = "true"
    from wskr.mpl.sixel import _BackendSixelAgg  # noqa: PLC0415

    with pytest.raises(NotImplementedError, match="not yet implemented"):
        _BackendSixelAgg.show()

    if orig_wskr_enable_sixel is not None:
        os.environ["WSKR_ENABLE_SIXEL"] = orig_wskr_enable_sixel

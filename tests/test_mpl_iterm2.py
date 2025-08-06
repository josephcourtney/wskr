import os

import pytest


def test_iterm2_import_raises():
    with pytest.raises(
        ImportError, match="iTerm2 backend is not yet implemented. Set WSKR_ENABLE_ITERM2=true to bypass."
    ):
        import wskr.mpl.iterm2  # noqa: PLC0415
    orig_wskr_enable_iterm2 = os.environ.get("WSKR_ENABLE_ITERM2")
    os.environ["WSKR_ENABLE_ITERM2"] = "true"
    import wskr.mpl.iterm2  # noqa: PLC0415

    if orig_wskr_enable_iterm2 is not None:
        os.environ["WSKR_ENABLE_ITERM2"] = orig_wskr_enable_iterm2

    assert wskr.mpl.iterm2


def test_iterm2_backend_show_raises():
    orig_wskr_enable_iterm2 = os.environ.get("WSKR_ENABLE_ITERM2")
    os.environ["WSKR_ENABLE_ITERM2"] = "true"
    from wskr.mpl.iterm2 import _BackendIterm2Agg  # noqa: PLC0415

    with pytest.raises(NotImplementedError, match="not yet implemented"):
        _BackendIterm2Agg.show()

    if orig_wskr_enable_iterm2 is not None:
        os.environ["WSKR_ENABLE_ITERM2"] = orig_wskr_enable_iterm2

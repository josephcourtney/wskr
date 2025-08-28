import os
import sys

import pytest

from wskr.core.errors import FeatureUnavailableError


def test_sixel_import_raises(monkeypatch):
    monkeypatch.delenv("WSKR_ENABLE_SIXEL", raising=False)
    sys.modules.pop("wskr.render.matplotlib.sixel", None)
    with pytest.raises(
        FeatureUnavailableError,
        match=r"Sixel backend is not yet implemented\. Set WSKR_ENABLE_SIXEL=true to bypass\.",
    ):
        import wskr.render.matplotlib.sixel  # noqa: PLC0415
    orig = os.environ.get("WSKR_ENABLE_SIXEL")
    os.environ["WSKR_ENABLE_SIXEL"] = "true"
    sys.modules.pop("wskr.render.matplotlib.sixel", None)
    import wskr.render.matplotlib.sixel  # noqa: PLC0415

    # sourcery skip: no-conditionals-in-tests
    if orig is not None:
        os.environ["WSKR_ENABLE_SIXEL"] = orig
    assert wskr.render.matplotlib.sixel


def test_sixel_backend_show_raises(monkeypatch):
    orig = os.environ.get("WSKR_ENABLE_SIXEL")
    os.environ["WSKR_ENABLE_SIXEL"] = "true"
    from wskr.render.matplotlib.sixel import _BackendSixelAgg  # noqa: PLC0415

    with pytest.raises(NotImplementedError, match="not yet implemented"):
        _BackendSixelAgg.show()
    # sourcery skip: no-conditionals-in-tests
    if orig is not None:
        os.environ["WSKR_ENABLE_SIXEL"] = orig

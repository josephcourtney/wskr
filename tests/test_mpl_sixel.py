import pytest

from wskr.mpl.sixel import _BackendSixelAgg


def test_sixel_backend_show_raises():
    with pytest.raises(NotImplementedError, match="not yet implemented"):
        _BackendSixelAgg.show()

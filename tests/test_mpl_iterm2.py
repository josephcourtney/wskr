import pytest

from wskr.mpl.iterm2 import _BackendIterm2Agg


def test_iterm2_backend_show_raises():
    with pytest.raises(NotImplementedError, match="not yet implemented"):
        _BackendIterm2Agg.show()

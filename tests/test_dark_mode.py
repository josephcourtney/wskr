import os
import pty
import threading

import pytest

from wskr import ttyools
from wskr.mpl import utils


def test_env_color_strategy(monkeypatch):
    monkeypatch.setenv("COLORFGBG", "15;0")
    assert utils.EnvColorStrategy().detect() is True
    monkeypatch.setenv("COLORFGBG", "0;15")
    assert utils.EnvColorStrategy().detect() is False
    monkeypatch.delenv("COLORFGBG", raising=False)
    try:
        utils.EnvColorStrategy().detect()
    except KeyError:
        pass
    else:  # pragma: no cover - fail path
        raise AssertionError


def test_osc_strategy_uses_config_timeout(monkeypatch):
    monkeypatch.setattr(utils, "OSC_TIMEOUT_S", 0.5)
    seen: dict[str, float] = {}

    def fake_query(cmd, more, timeout):
        seen["timeout"] = timeout
        return b"\x1b]11;rgb:0000/0000/0000\x07"

    monkeypatch.setattr(utils, "query_tty", fake_query)
    assert utils.OscQueryStrategy().detect() is True
    assert seen["timeout"] == 0.5


def test_osc_strategy_parser_error(monkeypatch):
    monkeypatch.setattr(utils, "query_tty", lambda *_a, **_k: b"oops")
    with pytest.raises(ValueError, match="Unexpected"):
        utils.OscQueryStrategy().detect()


def test_osc_strategy_parser_partial(monkeypatch):
    monkeypatch.setattr(utils, "query_tty", lambda *_a, **_k: b"\x1b]11;rgb:0000/0000\x07")
    with pytest.raises(ValueError, match="Unexpected"):
        utils.OscQueryStrategy().detect()


def test_detect_dark_mode_chain(monkeypatch):
    monkeypatch.setenv("COLORFGBG", "15;0")
    called: dict[str, bool] = {}

    def fake_query(*_a, **_k):
        called["osc"] = True
        return b""

    monkeypatch.setattr(utils, "query_tty", fake_query)
    assert utils.detect_dark_mode() is True
    assert "osc" not in called

    monkeypatch.delenv("COLORFGBG", raising=False)
    monkeypatch.setattr(
        utils,
        "query_tty",
        lambda *_a, **_k: b"\x1b]11;rgb:0000/0000/0000\x07",
    )
    assert utils.detect_dark_mode() is True


def test_osc_strategy_real_tty(monkeypatch):
    master_fd, slave_fd = pty.openpty()
    monkeypatch.setattr(ttyools, "_get_tty_fd", lambda: os.dup(slave_fd))

    def responder():
        data = os.read(master_fd, 100)
        assert data == utils._OSC_BG_QUERY
        os.write(master_fd, b"\x1b]11;rgb:0000/0000/0000\x07")

    t = threading.Thread(target=responder)
    t.start()
    try:
        assert utils.OscQueryStrategy(timeout=0.1).detect() is True
    finally:
        t.join()
        os.close(master_fd)
        os.close(slave_fd)


def test_detect_dark_mode_override(monkeypatch):
    monkeypatch.setenv("WSKR_DARK_MODE", "1")
    assert utils.detect_dark_mode() is True
    monkeypatch.setenv("WSKR_DARK_MODE", "0")
    assert utils.detect_dark_mode() is False

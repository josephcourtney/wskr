import os
import pty
import sys
import threading

import pytest

from wskr.render.matplotlib import utils
from wskr.terminal import query


def test_env_color_strategy(monkeypatch):
    monkeypatch.setenv("COLORFGBG", "15;0")
    assert utils.EnvColorStrategy().detect() is True
    monkeypatch.setenv("COLORFGBG", "0;15")
    assert utils.EnvColorStrategy().detect() is False
    monkeypatch.delenv("COLORFGBG", raising=False)
    with pytest.raises(KeyError):
        utils.EnvColorStrategy().detect()


def test_osc_strategy_uses_config_timeout(monkeypatch):
    monkeypatch.setattr(utils, "OSC_TIMEOUT_S", 0.5)
    seen = {}

    def fake_query(cmd, more, timeout):
        seen["timeout"] = timeout
        return b"\x1b]11;rgb:0000/0000/0000\x07"

    assert utils.OscQueryStrategy(query=fake_query).detect() is True
    assert seen["timeout"] == pytest.approx(0.5)


@pytest.mark.parametrize("bad", [b"oops", b"\x1b]11;rgb:0000/0000\x07"])
def test_osc_strategy_parser_error(bad):
    with pytest.raises(ValueError, match="Unexpected"):
        utils.OscQueryStrategy(query=lambda *_a, **_k: bad).detect()


def test_detect_dark_mode_chain(monkeypatch):
    monkeypatch.setenv("COLORFGBG", "15;0")
    called = []

    def fake_query(*_args, **_kwargs):
        called.append(True)
        return b""

    # Without input ownership, default OSC must not read shared user input.
    monkeypatch.setattr("wskr.terminal.query._open_tty", fake_query)
    assert utils.detect_dark_mode() is True
    assert called == []

    monkeypatch.delenv("COLORFGBG", raising=False)

    def injected(*_a, **_k):
        return b"\x1b]11;rgb:0000/0000/0000\x07"

    assert utils.detect_dark_mode(strategies=[utils.OscQueryStrategy(query=injected)]) is True


@pytest.mark.skipif(
    os.getenv("WSKR_RUN_TTY") != "1",
    reason="WSKR_RUN_TTY!=1; skip PTY-dependent test in constrained env",
)
def test_osc_strategy_real_tty(monkeypatch):
    master_fd, slave_fd = pty.openpty()
    monkeypatch.setattr(query, "_open_tty", lambda: os.dup(slave_fd))
    monkeypatch.setattr(query, "_stdout_is_tty", lambda: True)

    def responder():
        data = os.read(master_fd, 100)
        assert data == utils._OSC_BG_QUERY
        os.write(master_fd, b"\x1b]11;rgb:0000/0000/0000\x07")

    thread = threading.Thread(target=responder, daemon=True)
    thread.start()
    try:
        assert utils.OscQueryStrategy(
            timeout=0.5,
            owns_input=True,
            on_unmatched=lambda _bytes: None,
        ).detect() is True
    finally:
        thread.join(timeout=2)
        os.close(master_fd)
        os.close(slave_fd)


def test_detect_dark_mode_override(monkeypatch):
    monkeypatch.setenv("WSKR_DARK_MODE", "1")
    assert utils.detect_dark_mode() is True
    monkeypatch.setenv("WSKR_DARK_MODE", "0")
    assert utils.detect_dark_mode() is False


def test_darkdetect_strategy(monkeypatch):
    class DummyDD:
        @staticmethod
        def theme() -> str:
            return "Dark"

    monkeypatch.setitem(sys.modules, "darkdetect", DummyDD)
    monkeypatch.setattr(utils, "darkdetect", DummyDD)
    monkeypatch.delenv("COLORFGBG", raising=False)
    assert utils.detect_dark_mode(strategies=[utils.DarkDetectStrategy()]) is True
    monkeypatch.setattr(DummyDD, "theme", staticmethod(lambda: "Light"))
    assert utils.detect_dark_mode(strategies=[utils.DarkDetectStrategy()]) is False

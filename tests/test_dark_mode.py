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


def test_detect_dark_mode_override(monkeypatch):
    monkeypatch.setenv("WSKR_DARK_MODE", "1")
    assert utils.detect_dark_mode() is True
    monkeypatch.setenv("WSKR_DARK_MODE", "0")
    assert utils.detect_dark_mode() is False

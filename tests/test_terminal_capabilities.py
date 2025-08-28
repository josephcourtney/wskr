from __future__ import annotations

from wskr.terminal.generic import GenericCapabilities


def test_generic_window_size_is_fallback():
    caps = GenericCapabilities()
    assert caps.window_px() == (800, 600)


def test_generic_dark_mode_uses_env(monkeypatch):
    caps = GenericCapabilities()
    monkeypatch.setenv("COLORFGBG", "15;0")
    assert caps.is_dark() is True
    monkeypatch.setenv("COLORFGBG", "0;15")
    assert caps.is_dark() is False
    monkeypatch.delenv("COLORFGBG", raising=False)
    assert caps.is_dark() is False

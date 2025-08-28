from __future__ import annotations

from wskr.core import demo


def test_demo_runs(monkeypatch):
    called: dict[str, bool] = {}

    def fake_show():
        called["show"] = True

    monkeypatch.setattr(demo.plt, "show", fake_show)
    monkeypatch.setenv("WSKR_TRANSPORT", "noop")
    assert demo.main([]) == 0
    assert called["show"]

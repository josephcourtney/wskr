import matplotlib.pyplot as plt

import wskr
from wskr.mpl import utils


def test_init_applies_dark(monkeypatch):
    monkeypatch.setattr(utils, "detect_dark_mode", lambda: True)
    seen = {}
    monkeypatch.setattr(plt.style, "use", lambda style: seen.setdefault("style", style))
    wskr.init(style="auto-dark")
    assert seen["style"] == "dark_background"


def test_init_no_dark(monkeypatch):
    monkeypatch.setattr(utils, "detect_dark_mode", lambda: False)
    seen = {}
    monkeypatch.setattr(plt.style, "use", lambda style: seen.setdefault("style", style))
    wskr.init(style="auto-dark")
    assert seen == {}

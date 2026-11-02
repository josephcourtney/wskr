"""Cooperative IPython post-cell event pumping without stealing host input."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from matplotlib.figure import Figure

from wskr.render.matplotlib import core, ipython

pytestmark = pytest.mark.medium


class Events:
    def __init__(self) -> None:
        self.callbacks: list = []

    def register(self, name: str, callback) -> None:
        assert name == "post_run_cell"
        self.callbacks.append(callback)

    def unregister(self, name: str, callback) -> None:
        assert name == "post_run_cell"
        self.callbacks.remove(callback)

    def emit(self) -> None:
        for callback in tuple(self.callbacks):
            callback(None)


class Shell:
    def __init__(self) -> None:
        self.events = Events()


def test_ipython_extension_drains_all_registered_figures_once_per_cell(monkeypatch) -> None:
    shell = Shell()
    first = core.WskrFigureCanvas(Figure())
    second = core.WskrFigureCanvas(Figure())
    drained: list[str] = []
    monkeypatch.setattr(first, "_flush_one", lambda: drained.append("first"))
    monkeypatch.setattr(second, "_flush_one", lambda: drained.append("second"))
    monkeypatch.setattr(
        ipython.Gcf,
        "get_all_fig_managers",
        lambda: [SimpleNamespace(canvas=first), SimpleNamespace(canvas=second)],
    )
    monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("IPython owns stdin"))

    assert shell.events.callbacks == []  # import does not register anything
    try:
        ipython.load_ipython_extension(shell)
        ipython.load_ipython_extension(shell)
        assert len(shell.events.callbacks) == 1
        shell.events.emit()
        assert drained == ["first", "second"]
        shell.events.emit()
        assert drained == ["first", "second", "first", "second"]
    finally:
        ipython.unload_ipython_extension(shell)
    assert shell.events.callbacks == []
    shell.events.emit()
    assert len(drained) == 4
    ipython.unload_ipython_extension(shell)  # multiple unloads are harmless


def test_ipython_extension_leaves_unrelated_callbacks_and_managers_alone(monkeypatch) -> None:
    shell = Shell()
    callback = lambda _result: None
    shell.events.register("post_run_cell", callback)
    monkeypatch.setattr(ipython.Gcf, "get_all_fig_managers", lambda: [SimpleNamespace(canvas=object())])
    ipython.load_ipython_extension(shell)
    assert len(shell.events.callbacks) == 2
    shell.events.emit()
    ipython.unload_ipython_extension(shell)
    assert shell.events.callbacks == [callback]


def test_ipython_extension_requires_an_explicit_host_dispatcher() -> None:
    with pytest.raises(TypeError, match="events.register"):
        ipython.load_ipython_extension(object())

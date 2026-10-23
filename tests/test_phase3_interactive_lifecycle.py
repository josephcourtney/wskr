"""Phase 3 terminal show ownership and native Kitty draw-idle regressions."""

from __future__ import annotations

import os
import sys
from io import StringIO

import pytest
from matplotlib.backend_bases import FigureManagerBase
from matplotlib.figure import Figure

from wskr.render.matplotlib import core, kitty

pytestmark = pytest.mark.medium


class _Stream:
    def __init__(self, fd: int) -> None:
        self.fd = fd

    def isatty(self) -> bool:
        return True

    def fileno(self) -> int:
        return self.fd


def test_blocking_input_requires_same_foreground_tty(monkeypatch) -> None:
    first_master, first_slave = os.openpty()
    second_master, second_slave = os.openpty()
    try:
        with monkeypatch.context() as patch:
            patch.setattr(sys, "stdin", _Stream(first_slave))
            patch.setattr(sys, "stdout", _Stream(first_slave))
            patch.setattr(os, "tcgetpgrp", lambda _fd: 444)
            patch.setattr(os, "getpgrp", lambda: 444)
            assert core._owns_foreground_terminal_input()
            patch.setattr(sys, "stdout", _Stream(second_slave))
            assert not core._owns_foreground_terminal_input()
            patch.setattr(sys, "stdout", _Stream(first_slave))
            patch.setattr(os, "tcgetpgrp", lambda _fd: 445)
            assert not core._owns_foreground_terminal_input()
    finally:
        for fd in (first_master, first_slave, second_master, second_slave):
            os.close(fd)


def test_pipe_and_missing_input_cannot_be_claimed(monkeypatch) -> None:
    monkeypatch.setattr(sys, "stdin", StringIO())
    assert not core._owns_foreground_terminal_input()
    monkeypatch.setattr(sys, "stdin", None)
    assert not core._owns_foreground_terminal_input()


def test_default_and_false_show_do_not_consume_input_or_close_figures(monkeypatch) -> None:
    events: list[str] = []

    class Manager:
        def __init__(self, tag: str) -> None:
            self.tag = tag

        def show(self) -> None:
            events.append(self.tag)

    monkeypatch.setattr(core.Gcf, "get_all_fig_managers", lambda: [Manager("first"), Manager("second")])
    monkeypatch.setattr(core.Gcf, "destroy_all", lambda: pytest.fail("nonblocking show closed figures"))
    monkeypatch.setattr("builtins.input", lambda _prompt: pytest.fail("nonblocking show consumed stdin"))
    core._BackendTermAgg.show()
    core._BackendTermAgg.show(block=None)
    core._BackendTermAgg.show(block=False)
    assert events == ["first", "second"] * 3


def test_explicit_block_renders_then_waits_and_closes(monkeypatch) -> None:
    events: list[str] = []

    class Manager:
        def show(self) -> None:
            events.append("render")

    monkeypatch.setattr(core.Gcf, "get_all_fig_managers", lambda: [Manager(), Manager()])
    monkeypatch.setattr(core, "_owns_foreground_terminal_input", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: events.append("input"))
    monkeypatch.setattr(core.Gcf, "destroy_all", lambda: events.append("close"))
    core._BackendTermAgg.show(block=True)
    assert events == ["render", "render", "input", "close"]


def test_blocking_show_rejects_unowned_input_before_render(monkeypatch) -> None:
    class Manager:
        def show(self) -> None:
            pytest.fail("rejected block request rendered graphics")

    monkeypatch.setattr(core.Gcf, "get_all_fig_managers", lambda: [Manager()])
    monkeypatch.setattr(core, "_owns_foreground_terminal_input", lambda: False)
    with pytest.raises(RuntimeError, match="same TTY"):
        core._BackendTermAgg.show(block=True)


@pytest.mark.parametrize("failure", [KeyboardInterrupt, EOFError])
def test_blocking_show_releases_figures_on_input_failure(monkeypatch, failure) -> None:
    events: list[str] = []

    class Manager:
        def show(self) -> None:
            events.append("render")

    def fail_input(_prompt: str) -> None:
        raise failure

    monkeypatch.setattr(core.Gcf, "get_all_fig_managers", lambda: [Manager()])
    monkeypatch.setattr(core, "_owns_foreground_terminal_input", lambda: True)
    monkeypatch.setattr("builtins.input", fail_input)
    monkeypatch.setattr(core.Gcf, "destroy_all", lambda: events.append("close"))
    with pytest.raises(failure):
        core._BackendTermAgg.show(block=True)
    assert events == ["render", "close"]


def test_blocking_show_with_no_registered_figures_returns_immediately(monkeypatch) -> None:
    monkeypatch.setattr(core.Gcf, "get_all_fig_managers", list)
    monkeypatch.setattr(core, "_owns_foreground_terminal_input", lambda: pytest.fail("unneeded TTY gate"))
    core._BackendTermAgg.show(block=True)


def test_kitty_canvas_interactive_draw_idle_sends_exactly_one_png(monkeypatch) -> None:
    fig = Figure(figsize=(2, 1.5), dpi=90)
    fig.subplots().plot([0, 1], [0, 1])
    canvas = kitty.KittyFigureCanvas(fig)
    events: list[bytes] = []

    class Manager(FigureManagerBase):
        def show(self) -> None:
            events.append(b"render")
            if len(events) == 1:
                canvas.draw()  # Reentrant callback must not trigger another show.

    Manager(canvas, 4901)
    assert canvas.manager_class is kitty.KittyFigureManager
    monkeypatch.setattr(core, "is_interactive", lambda: True)
    canvas.draw_idle()
    assert events == [b"render"]


def test_kitty_canvas_noninteractive_draw_idle_does_not_transmit(monkeypatch) -> None:
    fig = Figure(figsize=(2, 1.5), dpi=90)
    fig.subplots().plot([0, 1], [1, 2])
    canvas = kitty.KittyFigureCanvas(fig)

    class Manager(FigureManagerBase):
        def show(self) -> None:
            pytest.fail("noninteractive draw_idle transmitted a PNG")

    Manager(canvas, 4902)
    monkeypatch.setattr(core, "is_interactive", lambda: False)
    canvas.draw_idle()

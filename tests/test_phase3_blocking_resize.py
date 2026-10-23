"""Live foreground terminal resize handling for opt-in fitted Matplotlib plots."""

from __future__ import annotations

import errno
import fcntl
import os
import pty
import select
import signal
import struct
import sys
import termios
import time

import pytest

from wskr.render.matplotlib import core
from wskr.terminal.profile import Geometry

pytestmark = pytest.mark.medium

_CHILD = """
import matplotlib
matplotlib.use("module://wskr.render.matplotlib.kitty")
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(6, 6), dpi=120)
ax.bar([1, 2, 3], [2, 4, 3], color=("cyan", "magenta", "yellow"))
plt.show(block=True)
print("RESIZE_DONE", tuple(float(value) for value in fig.get_size_inches()), fig.dpi, flush=True)
"""


def test_fitted_blocking_session_debounces_and_reads_only_complete_input(monkeypatch) -> None:
    first = Geometry(30, 80, 640, 400)
    second = Geometry(25, 70, 550, 300)
    third = Geometry(18, 45, 390, 210)
    seen: list[str] = []

    class Input:
        def fileno(self) -> int:
            return 7

    polls = iter(([], [], [], [], [], [], [7]))
    geometry = iter((second, third, third, third, third, third))
    clock = iter((0.0, 0.05, 0.10, 0.30))
    monkeypatch.setattr(core.sys, "stdin", Input())
    monkeypatch.setattr(core.select, "select", lambda *_args: (next(polls), [], []))
    monkeypatch.setattr(core, "read_geometry", lambda: next(geometry))
    monkeypatch.setattr(core, "monotonic", lambda: next(clock))
    monkeypatch.setattr(core, "_redraw_foreground_figures", lambda _managers: seen.append("redraw"))
    monkeypatch.setattr("builtins.input", lambda: seen.append("enter"))

    core._wait_for_foreground_resize([], first)
    assert seen == ["redraw", "enter"]


def test_fitted_blocking_session_ignores_unavailable_geometry(monkeypatch) -> None:
    initial = Geometry(24, 80, 640, 480)
    seen: list[str] = []

    class Input:
        def fileno(self) -> int:
            return 8

    polls = iter(([], [], [8]))
    monkeypatch.setattr(core.sys, "stdin", Input())
    monkeypatch.setattr(core.select, "select", lambda *_args: (next(polls), [], []))
    monkeypatch.setattr(core, "read_geometry", lambda: None)
    monkeypatch.setattr(core, "_redraw_foreground_figures", lambda _managers: pytest.fail("unknown geometry redrawn"))
    monkeypatch.setattr("builtins.input", lambda: seen.append("enter"))
    core._wait_for_foreground_resize([], initial)
    assert seen == ["enter"]


def _exec_child() -> None:
    os.environ["TERM"] = "xterm-kitty"
    os.environ["WSKR_FIT"] = "contain"
    os.environ.pop("WSKR_SCALE", None)
    try:
        os.execv(sys.executable, [sys.executable, "-c", _CHILD])  # ruff: ignore[start-process-with-no-shell]
    except OSError:
        os._exit(127)


def _set_geometry(fd: int, *, width: int, height: int) -> None:
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, width, height))


def _collect_resized_session(master: int) -> tuple[bytes, bool]:
    output = bytearray()
    resized = False
    pressed_enter = False
    deadline = time.monotonic() + 22.0
    while time.monotonic() < deadline:
        readable, _, _ = select.select([master], [], [], 0.1)
        if readable:
            try:
                chunk = os.read(master, 65536)
            except OSError as exc:
                if exc.errno != errno.EIO:
                    raise
                chunk = b""
            if not chunk:
                break
            output.extend(chunk)

        if not resized and b"press Enter to close displayed figures" in output:
            _set_geometry(master, width=480, height=240)
            resized = True
        if resized and not pressed_enter and output.count(b"a=T") >= 2:
            os.write(master, b"\n")
            pressed_enter = True
        if b"RESIZE_DONE" in output:
            break
    return bytes(output), pressed_enter


def _reap(child: int) -> int:
    waited, status = os.waitpid(child, os.WNOHANG)
    deadline = time.monotonic() + 3.0
    while waited == 0 and time.monotonic() < deadline:
        time.sleep(0.05)
        waited, status = os.waitpid(child, os.WNOHANG)
    if waited == 0:
        os.kill(child, signal.SIGKILL)
        _, status = os.waitpid(child, 0)
    return status


def test_actual_foreground_pty_redraws_when_kernel_viewport_changes() -> None:
    child, master = pty.fork()
    if child == 0:
        _exec_child()
    _set_geometry(master, width=700, height=460)
    output = b""
    sent_enter = False
    try:
        output, sent_enter = _collect_resized_session(master)
    finally:
        status = _reap(child)
        os.close(master)

    assert sent_enter, output[-2000:]
    assert output.count(b"a=T") == 2, output[-2000:]
    assert b"\x1b[H\x1b[2J" in output
    assert output.count(b"a=d,d=I") == 2
    enter = output.index(b"\x1b[?1049h")
    restore = output.index(b"\x1b[?1049l")
    done = output.index(b"RESIZE_DONE")
    assert enter < restore < done
    assert b"(6.0, 6.0) 120" in output
    assert os.WIFEXITED(status)
    assert os.WEXITSTATUS(status) == 0

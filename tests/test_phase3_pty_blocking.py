"""End-to-end pyplot.show(block=True) in a foreground POSIX PTY.

The child owns the controlling TTY. The parent emulates an explicit Enter
after the terminal backend renders and prompts the user.
"""

from __future__ import annotations

import errno
import os
import pty
import select
import signal
import sys
import time

import pytest

pytestmark = pytest.mark.medium

_SCRIPT = """
import matplotlib
matplotlib.use("module://wskr.render.matplotlib.kitty")
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(1.5, 1.0), dpi=48)
ax.plot([0, 1, 2], [1, 0, 1])
plt.show(block=True)
print("BLOCK_DONE", flush=True)
"""


def _exec_child(script: str = _SCRIPT) -> None:
    os.environ["TERM"] = "xterm-kitty"
    os.environ["WSKR_SCALE"] = "0.5"
    try:
        os.execv(sys.executable, [sys.executable, "-c", script])  # ruff: ignore[start-process-with-no-shell]
    except OSError:
        os._exit(127)


def _capture_until_done(master: int) -> tuple[bytes, bool]:
    output = bytearray()
    sent_enter = False
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        readable, _, _ = select.select([master], [], [], 0.2)
        if readable:
            try:
                data = os.read(master, 65536)
            except OSError as exc:
                if exc.errno != errno.EIO:
                    raise
                data = b""
            if not data:
                break
            output.extend(data)
        if b"press Enter to close displayed figures" in output and not sent_enter:
            os.write(master, b"\n")
            sent_enter = True
        if b"BLOCK_DONE" in output:
            break
    return bytes(output), sent_enter


def _reap_child(child: int) -> int:
    waited, code = os.waitpid(child, os.WNOHANG)
    until = time.monotonic() + 3
    while waited == 0 and time.monotonic() < until:
        time.sleep(0.05)
        waited, code = os.waitpid(child, os.WNOHANG)
    if waited == 0:
        os.kill(child, signal.SIGKILL)
        _, code = os.waitpid(child, 0)
    return code


def test_real_foreground_pty_blocking_show_and_scoped_close() -> None:
    child, master = pty.fork()
    if child == 0:
        _exec_child()

    output = b""
    sent_enter = False
    try:
        output, sent_enter = _capture_until_done(master)
    finally:
        status = _reap_child(child)
        os.close(master)

    assert sent_enter, output[-2000:]
    assert b"BLOCK_DONE" in output, output[-2000:]
    assert b"a=T" in output or b"a=t" in output
    assert b"a=d,d=I" in output
    enter = output.index(b"\x1b[?1049h")
    upload = output.index(b"\x1b_G")
    deletion = output.index(b"a=d,d=I")
    restore = output.index(b"\x1b[?1049l")
    returned = output.index(b"BLOCK_DONE")
    assert enter < upload < deletion < restore < returned
    assert os.WIFEXITED(status)
    assert os.WEXITSTATUS(status) == 0


def test_real_foreground_pty_default_show_auto_blocks() -> None:
    """A noninteractive script without block= must own the canonical prompt."""
    child, master = pty.fork()
    if child == 0:
        _exec_child(_SCRIPT.replace("plt.show(block=True)", "plt.show()"))

    output = b""
    sent_enter = False
    try:
        output, sent_enter = _capture_until_done(master)
    finally:
        status = _reap_child(child)
        os.close(master)

    assert sent_enter, output[-2000:]
    assert b"BLOCK_DONE" in output, output[-2000:]
    assert b"\x1b[?1049h" in output
    assert b"\x1b[?1049l" in output
    assert os.WIFEXITED(status)
    assert os.WEXITSTATUS(status) == 0


def test_real_pty_interactive_multiple_figures_pump_without_input() -> None:
    """Standard pyplot + one canvas pump uploads both managed images."""
    script = """
import matplotlib
matplotlib.use("module://wskr.render.matplotlib.kitty")
import matplotlib.pyplot as plt
plt.ion()
fig_a, ax_a = plt.subplots(figsize=(2, 1), dpi=70)
fig_b, ax_b = plt.subplots(figsize=(2, 1), dpi=70)
ax_a.plot([0, 1], [1, 0])
ax_b.plot([0, 1], [0, 1])
fig_a.canvas.draw_idle()
fig_b.canvas.draw_idle()
fig_a.canvas.flush_events()
print("BLOCK_DONE", flush=True)
plt.close(fig_a)
plt.close(fig_b)
"""
    child, master = pty.fork()
    if child == 0:
        os.environ["WSKR_IDLE_REDRAW"] = "coalesce"
        _exec_child(script)

    try:
        output, sent_enter = _capture_until_done(master)
    finally:
        status = _reap_child(child)
        os.close(master)

    assert not sent_enter
    assert b"BLOCK_DONE" in output, output[-2000:]
    assert output.count(b"a=T") >= 2, output[-2000:]
    assert os.WIFEXITED(status)
    assert os.WEXITSTATUS(status) == 0

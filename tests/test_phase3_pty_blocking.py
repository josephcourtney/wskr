"""Actual pyplot.show(block=True) lifecycle across a foreground POSIX PTY.

The child owns the controlling TTY. Its parent plays the role of a user by
pressing Enter after the terminal backend presents an explicit prompt.
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


def test_real_foreground_pty_blocking_show_and_scoped_close() -> None:
    child, master = pty.fork()
    if child == 0:
        os.environ["TERM"] = "xterm-kitty"
        os.environ["WSKR_SCALE"] = "0.5"
        try:
            os.execv(sys.executable, [sys.executable, "-c", _SCRIPT])
        except OSError:
            os._exit(127)

    output = bytearray()
    sent_enter = False
    status: int | None = None
    deadline = time.monotonic() + 20
    try:
        while time.monotonic() < deadline:
            readable, _, _ = select.select([master], [], [], 0.2)
            if readable:
                try:
                    data = os.read(master, 65536)
                except OSError as exc:
                    if exc.errno != errno.EIO:
                        raise
                    data = b""
                if data:
                    output.extend(data)
                elif sent_enter:
                    break
            if b"press Enter to close displayed figures" in output and not sent_enter:
                os.write(master, b"\n")
                sent_enter = True
            if b"BLOCK_DONE" in output:
                break
    finally:
        # Never leak a process or foreground TTY if a regression hangs.
        waited, code = os.waitpid(child, os.WNOHANG)
        if waited == 0:
            os.kill(child, signal.SIGKILL)
            _, code = os.waitpid(child, 0)
        status = code
        os.close(master)

    assert sent_enter, bytes(output[-2000:])
    assert b"BLOCK_DONE" in output, bytes(output[-2000:])
    assert b"a=T" in output or b"a=t" in output  # Native Kitty PNG upload
    assert b"a=d,d=I" in output  # Explicit user close, not retained history
    assert status is not None and os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0

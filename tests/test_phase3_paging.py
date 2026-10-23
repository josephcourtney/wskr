"""Measured contact-sheet paging and real foreground Kitty navigation."""

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
from io import BytesIO
from typing import TYPE_CHECKING

import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PIL import Image

from wskr.protocol.base import ImageProtocol
from wskr.render.matplotlib import core
from wskr.render.matplotlib.sheet import contact_sheet, plan_sheet_pages
from wskr.terminal.profile import Geometry

if TYPE_CHECKING:
    from matplotlib.backend_bases import FigureManagerBase


pytestmark = pytest.mark.medium

_SCRIPT = """
import matplotlib
matplotlib.use("module://wskr.render.matplotlib.kitty")
import matplotlib.pyplot as plt

for color in ("red", "blue", "green", "magenta", "yellow"):
    plt.figure(figsize=(3, 2), dpi=80, facecolor=color)
plt.show(block=True)
print("PAGING_DONE", flush=True)
"""


class _Captured(ImageProtocol):
    def __init__(self) -> None:
        self.frames: list[bytes] = []
        self.closed = False

    def get_window_size_px(self) -> tuple[int, int]:
        return 400, 260

    def send_image(self, png_bytes: bytes) -> None:
        self.frames.append(png_bytes)

    def init_image(self, png_bytes: bytes) -> int:
        self.frames.append(png_bytes)
        return len(self.frames)

    def close(self) -> None:
        self.closed = True


def _canvas(color: str) -> FigureCanvasAgg:
    return FigureCanvasAgg(Figure(figsize=(3, 2), dpi=80, facecolor=color))


@pytest.mark.parametrize(
    ("geometry", "capacity", "columns", "pages"),
    [
        (Geometry(24, 80, 400, 260), 1, 1, 5),
        (Geometry(24, 80, 640, 400), 2, 2, 3),
        (Geometry(40, 80, 480, 800), 4, 1, 2),
    ],
)
def test_page_capacity_preserves_readable_panels(geometry, capacity, columns, pages) -> None:
    plan = plan_sheet_pages(5, geometry)
    assert plan.page_size == capacity
    assert plan.columns == columns
    assert plan.total_pages == pages
    assert plan.page_slice(50).start == (pages - 1) * capacity
    assert plan.page_slice(-5).start == 0


def test_single_figure_page_preserves_source_export() -> None:
    canvas = _canvas("magenta")
    before = BytesIO()
    canvas.figure.savefig(before, format="png")
    geometry = Geometry(24, 80, 400, 260)
    png = contact_sheet([canvas], geometry, columns=1)
    with Image.open(BytesIO(png)) as image:
        assert image.size == (400, 238)
        assert len(image.convert("RGB").tobytes()) == 400 * 238 * 3
    after = BytesIO()
    canvas.figure.savefig(after, format="png")
    assert before.getvalue() == after.getvalue()
    assert tuple(canvas.figure.get_size_inches()) == (3, 2)
    assert canvas.figure.dpi == 80


def test_paged_manager_transmits_only_selected_figure(monkeypatch) -> None:
    transport = _Captured()
    managers: list[FigureManagerBase] = [
        core.WskrFigureManager(_canvas(color), 9100 + index, transport_factory=lambda: transport)
        for index, color in enumerate(("red", "blue", "green"))
    ]

    class Output:
        def flush(self) -> None:
            pass

        def fileno(self) -> int:
            return 1

    writes: list[bytes] = []
    monkeypatch.setenv("WSKR_FIT", "contain")
    monkeypatch.setattr(core, "is_interactive", lambda: False)
    monkeypatch.setattr(core.sys, "stdout", Output())
    monkeypatch.setattr(core.os, "write", lambda _fd, data: writes.append(data))
    try:
        geometry = Geometry(24, 80, 400, 260)
        plan = core._show_blocking_managers(managers, geometry, page_index=2)
        assert plan is not None
        assert plan.total_pages == 3
        assert len(transport.frames) == 1
        with Image.open(BytesIO(transport.frames[0])) as image:
            rgb = image.convert("RGB").tobytes()
            assert rgb.count(bytes((0, 128, 0))) > 200
            assert rgb.count(bytes((255, 0, 0))) == 0
        assert writes == [b"\x1b[24;1H"]
    finally:
        for manager in managers:
            manager.destroy()


def test_page_prompt_shortens_for_narrow_cells() -> None:
    plan = plan_sheet_pages(5, Geometry(24, 14, 400, 260))
    prompt = core._page_prompt(plan, 1, Geometry(24, 14, 400, 260))
    assert len(prompt) < 14
    assert "2/5" in prompt


def _exec_child() -> None:
    os.environ["TERM"] = "xterm-kitty"
    os.environ["WSKR_FIT"] = "contain"
    os.environ.pop("WSKR_SCALE", None)
    try:
        os.execv(sys.executable, [sys.executable, "-c", _SCRIPT])  # ruff: ignore[start-process-with-no-shell]
    except OSError:
        os._exit(127)


def _collect_paging_session(master: int) -> tuple[bytes, int]:
    output = bytearray()
    sent = 0
    commands = (b"n\n", b"n\n", b"p\n", b"\n")
    deadline = time.monotonic() + 25
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
        if sent < len(commands) and output.count(b"a=T") >= sent + 1 and b"n/p" in output:
            os.write(master, commands[sent])
            sent += 1
        if b"PAGING_DONE" in output:
            break
    return bytes(output), sent


def _reap_child(child: int) -> int:
    waited, status = os.waitpid(child, os.WNOHANG)
    deadline = time.monotonic() + 3.0
    while waited == 0 and time.monotonic() < deadline:
        time.sleep(0.05)
        waited, status = os.waitpid(child, os.WNOHANG)
    if waited == 0:
        os.kill(child, signal.SIGKILL)
        _, status = os.waitpid(child, 0)
    return status


def test_real_foreground_pty_navigates_pages_and_restores_screen() -> None:
    child, master = pty.fork()
    if child == 0:
        _exec_child()
    fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 400, 260))
    output = b""
    sent = 0
    try:
        output, sent = _collect_paging_session(master)
    finally:
        status = _reap_child(child)
        os.close(master)

    assert sent == 4, output[-2000:]
    assert output.count(b"a=T") == 4, output[-2000:]
    assert output.count(b"a=d,d=I") == 4
    assert output.count(b"\x1b[H\x1b[2J") == 3
    assert output.index(b"\x1b[?1049h") < output.index(b"\x1b[?1049l") < output.index(b"PAGING_DONE")
    assert os.WIFEXITED(status)
    assert os.WEXITSTATUS(status) == 0

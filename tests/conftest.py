import contextlib
import os
import select
import subprocess
import termios

import pytest

from wskr.protocol.base import ImageProtocol
from wskr.terminal import io

MAX_OUTPUT_LINES = 32
MAX_TIME_PER_TEST = 5


def pytest_collection_modifyitems(config, items):  # call signature defined by pytest
    for test in items:
        test.add_marker(pytest.mark.timeout(MAX_TIME_PER_TEST))


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Limit captured output per test."""
    # Only modify output for the call phase (i.e. test execution)
    if report.when != "call" or not report.failed:
        return
    new_sections: list[tuple[str, str]] = []
    for title, content in report.sections:
        if title.startswith(("Captured stdout", "Captured stderr")):
            lines = content.splitlines()
            if len(lines) > MAX_OUTPUT_LINES:
                truncated_section: str = "\n".join([*lines[:MAX_OUTPUT_LINES], "... [output truncated]"])
                new_sections.append((title, truncated_section))
            else:
                new_sections.append((title, content))

        else:
            new_sections.append((title, content))
    report.sections = new_sections


class DummyTransport(ImageProtocol):
    def __init__(self, width=800, height=600):
        self.width = width
        self.height = height
        self.last_image = None
        self.counter = 0

    def get_window_size_px(self) -> tuple[int, int]:
        return (self.width, self.height)

    def send_image(self, png_bytes: bytes) -> None:
        self.last_image = png_bytes

    def init_image(self, png_bytes: bytes) -> int:
        self.last_image = png_bytes
        self.counter += 1
        return self.counter


@pytest.fixture
def dummy_transport() -> DummyTransport:
    return DummyTransport()


@pytest.fixture
def dummy_png() -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 12


@pytest.fixture
def fake_tty(monkeypatch, tmp_path):
    # 1) Track all closes
    closed = []

    # 2) os.ttyname() → some fake file
    monkeypatch.setattr(os, "ttyname", lambda fd: str(tmp_path / "tty"))

    # 3) os.open → fake fd
    fake_fd = 99
    monkeypatch.setattr(os, "open", lambda *a, **kw: fake_fd)

    # 4) record os.close calls into closed[]
    monkeypatch.setattr(os, "close", closed.append)

    # 5) os.write doesn't actually write
    monkeypatch.setattr(os, "write", lambda fd, data: len(data))

    # 6) termios.tcdrain → no-op
    monkeypatch.setattr(termios, "tcdrain", lambda fd: None)

    # 7) Replace io.tty_attributes with a real no-op context manager
    monkeypatch.setattr(io, "tty_attributes", lambda *args, **kwargs: contextlib.nullcontext())

    # 8) select.select always reports no data
    monkeypatch.setattr(select, "select", lambda r, w, x, t: ([], [], []))

    # Finally, return our closed-list so tests can assert on it
    return closed


@pytest.fixture
def popen_recorder(monkeypatch):
    """Patch subprocess.Popen to record calls and expose the last instance.

    Returns a dict with keys:
    - calls: list of (args, env) tuples
    - last: the last Dummy instance created
    """
    calls: list[tuple[list[str], dict | None]] = []

    class Dummy:
        def __init__(self, args, env=None, **kw):
            self.args = args
            self.env = env
            calls.append((args, env))

        def poll(self):
            return 0

    monkeypatch.setattr(subprocess, "Popen", Dummy)
    return {"calls": calls, "last": None}

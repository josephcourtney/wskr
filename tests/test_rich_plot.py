import numpy as np
from rich.console import Console

from wskr.plot import make_plot_grid
from wskr.rich.plt import RichPlot, get_terminal_size, sparkline


def test_rich_plot_can_render_to_console(monkeypatch, dummy_transport):
    # Patch get_terminal_size and get_image_transport to avoid real system I/O
    monkeypatch.setattr("wskr.rich.plt.get_terminal_size", lambda: (10, 20, 100, 30))
    monkeypatch.setattr("wskr.rich.img.get_image_transport", lambda: dummy_transport)

    fig, ax = make_plot_grid(1, 1)
    ax[0].plot([0, 1, 2], [3, 2, 4])
    rich_plot = RichPlot(fig, desired_width=20, desired_height=5)

    console = Console(record=True)
    console.print(rich_plot)
    output = console.export_text()

    assert output.strip()


def test_rich_plot_ansi_output(dummy_transport, monkeypatch):
    monkeypatch.setattr("wskr.rich.plt.get_terminal_size", lambda: (10, 20, 80, 24))
    monkeypatch.setattr("wskr.rich.img.get_image_transport", lambda: dummy_transport)

    fig, ax = make_plot_grid(1, 1)
    ax[0].plot([0, 1, 2], [1, 2, 1], c="white")
    rp = RichPlot(fig, desired_width=10, desired_height=3)

    console = Console()
    with console.capture() as capture:
        console.print(rp)
    output = capture.get()

    # We expect 3 non-empty lines — one for each "row" in the RichImage
    lines = [line for line in output.splitlines() if line.strip()]
    assert len(lines) == 3
    assert all(len(line.strip()) > 0 for line in lines)


def test_sparkline_generates_correct_rows(monkeypatch):
    monkeypatch.setattr("wskr.rich.plt.get_terminal_size", lambda: (10, 20, 5, 5))
    sp = sparkline(np.linspace(0, 1, 16), np.sin(np.linspace(0, 1, 16)), columns=4, rows=3)
    console = Console(record=True)
    console.print(sp)
    output = console.export_text().splitlines()
    non_empty = [line for line in output if line.strip()]
    assert len(non_empty) == 3


def test_get_terminal_size_is_cached(monkeypatch):
    calls = {"count": 0}

    def fake_ioctl(fd, req, buf):
        calls["count"] += 1
        raise OSError

    monkeypatch.setattr("fcntl.ioctl", fake_ioctl)
    sz1 = get_terminal_size()
    sz2 = get_terminal_size()
    assert sz1 == sz2
    assert calls["count"] == 1

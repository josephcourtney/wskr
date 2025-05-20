import io
from typing import Any

from rich.console import Console
from rich.text import Text

from wskr.plot import make_plot_grid
from wskr.rich.img import RichImage
from wskr.rich.plt import RichPlot


def assert_rendered(renderable: Any, expected: str) -> None:
    """Assert that the rendered console output includes `expected` text."""
    console = Console(record=True)
    console.print(renderable)
    output = console.export_text()
    assert expected in output, f"Expected '{expected}' in output, got:\n{output}"


def test_rich_image_can_be_instantiated(dummy_png, dummy_transport):
    rich_image = RichImage(
        image_path=io.BytesIO(dummy_png),
        desired_width=5,
        desired_height=3,
        transport=dummy_transport,
    )

    assert rich_image.image_id == 1
    assert dummy_transport.last_image.startswith(b"\x89PNG")


def test_rich_image_yields_text(dummy_png, dummy_transport):
    rich_img = RichImage(io.BytesIO(dummy_png), desired_width=10, desired_height=5, transport=dummy_transport)
    console = Console()
    segments = list(rich_img.__rich_console__(console, console.options))

    assert len(segments) == 5  # one per desired_height
    assert all(isinstance(seg, Text) for seg in segments)
    assert dummy_transport.last_image is not None


def test_rich_image_measures_correctly(dummy_png, dummy_transport):
    rich_img = RichImage(io.BytesIO(dummy_png), desired_width=12, desired_height=3, transport=dummy_transport)
    console = Console()
    measurement = rich_img.__rich_measure__(console, console.options)

    assert measurement.minimum == 12
    assert measurement.maximum == 12


def test_rich_plot_output_shape(monkeypatch, dummy_transport):
    monkeypatch.setattr("wskr.rich.plt.get_terminal_size", lambda: (10, 20, 100, 40))
    monkeypatch.setattr("wskr.rich.img.get_image_transport", lambda: dummy_transport)

    fig, ax = make_plot_grid(1, 1)
    ax[0].plot([0, 1], [1, 2])
    rp = RichPlot(fig, desired_width=20, desired_height=5)

    console = Console(record=True)
    console.print(rp)

    rendered_text = console.export_text()
    assert rendered_text.strip()
    assert len(rendered_text.splitlines()) >= 5


def test_rich_plot_can_be_measured(monkeypatch, dummy_transport):
    monkeypatch.setattr("wskr.rich.plt.get_terminal_size", lambda: (8, 16, 100, 40))
    monkeypatch.setattr("wskr.rich.img.get_image_transport", dummy_transport)

    fig, _ = make_plot_grid(1, 1)
    rp = RichPlot(fig, desired_width=40, desired_height=20)

    console = Console()
    m = rp.__rich_measure__(console, console.options)
    assert m.minimum <= 40
    assert m.maximum >= 40


def test_rich_image_rendered_lines(dummy_png, dummy_transport):
    rich_image = RichImage(
        image_path=io.BytesIO(dummy_png),
        desired_width=4,
        desired_height=2,
        transport=dummy_transport,
    )
    console = Console(record=True)
    console.print(rich_image)
    output = console.export_text()

    lines = [line for line in output.splitlines() if line.strip()]
    assert len(lines) == 2

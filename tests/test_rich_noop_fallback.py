"""Regression for a visible Rich fallback when the default transport is noop."""

from io import BytesIO

import pytest
from rich.console import Console

from wskr.protocol.noop import NoOpProtocol
from wskr.render.rich.img import RichImage

pytestmark = pytest.mark.small


def test_noop_renders_visible_status_on_every_print_without_raw_upload(monkeypatch, capsys):
    monkeypatch.delenv("WSKR_PROTOCOL", raising=False)
    monkeypatch.setattr("wskr.render.rich.img.get_image_protocol", NoOpProtocol)
    png = b"\\x89PNG\\r\\n\\x1a\\n" + b"\\x00" * 12

    image = RichImage(BytesIO(png), desired_width=50, desired_height=3)
    assert image.image_id == -1

    console = Console(width=80, record=True)
    console.print(image)
    console.print(image)

    output = console.export_text()
    assert output.count("image unavailable") == 2
    assert "[wskr] Warning" not in capsys.readouterr().out
    assert "\\x1b_G" not in output


"""The Kitty registry can recognize the transport without unsafe Rich writes."""

from io import BytesIO

import pytest
from rich.console import Console
from rich.panel import Panel

from wskr.protocol import registry
from wskr.protocol.kitty import KittyTransport
from wskr.protocol.noop import NoOpProtocol
from wskr.render.rich.img import RichImage

pytestmark = pytest.mark.small


def test_kitty_protocol_is_lazily_registered_without_tty_queries(monkeypatch):
    monkeypatch.setattr(registry, "_IMAGE_PROTOCOLS", {})
    monkeypatch.setattr(registry, "_ENTRYPOINTS_LOADED", True)
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/kitty" if name == "kitty" else None)

    transport = registry.get_image_protocol("kitty")
    assert isinstance(transport, KittyTransport)
    assert transport.supports_inline_placement is False
    assert "kitty" in registry._IMAGE_PROTOCOLS


def test_rich_explicit_kitty_never_calls_unsafe_inline_upload(monkeypatch, dummy_png, capsys):
    monkeypatch.setattr(registry, "_IMAGE_PROTOCOLS", {})
    monkeypatch.setattr(registry, "_ENTRYPOINTS_LOADED", True)
    monkeypatch.setenv("WSKR_PROTOCOL", "kitty")
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/kitty" if name == "kitty" else None)

    def unsafe_upload(*args, **kwargs):
        pytest.fail("Legacy Kitty inline upload and TTY query must not execute")

    monkeypatch.setattr(KittyTransport, "init_image", unsafe_upload)
    monkeypatch.setattr(KittyTransport, "send_image", unsafe_upload)
    image = RichImage(BytesIO(dummy_png), desired_width=20, desired_height=3)

    console = Console(record=True, width=70)
    console.print(Panel(image, title="Safe Kitty Rich fallback"))
    text = console.export_text()
    assert "inline placement unavailable" in text
    assert "no graphics protocol" not in text
    assert "Unknown protocol" not in capsys.readouterr().out


def test_unknown_protocol_still_uses_noop(monkeypatch):
    monkeypatch.setattr(registry, "_IMAGE_PROTOCOLS", {})
    monkeypatch.setattr(registry, "_ENTRYPOINTS_LOADED", True)
    assert isinstance(registry.get_image_protocol("not-installed"), NoOpProtocol)

"""The Kitty registry can recognize the transport without unsafe Rich writes."""

from io import BytesIO

import pytest
from rich.console import Console
from rich.panel import Panel

from wskr.core.errors import TransportUnavailableError
from wskr.protocol import registry
from wskr.protocol.kitty import KittyTransport
from wskr.protocol.kitty_native import NativeKittyTransport
from wskr.protocol.noop import NoOpProtocol
from wskr.render.rich.img import RichImage

pytestmark = pytest.mark.small


def test_kitty_protocol_is_lazily_registered_without_tty_queries(monkeypatch):
    monkeypatch.setattr(registry, "_IMAGE_PROTOCOLS", {})
    monkeypatch.setattr(registry, "_ENTRYPOINTS_LOADED", True)
    # Registry lookup must be lazy, but constructing a real transport without
    # an attached Kitty TTY must fail rather than quietly choose icat/noop.
    with pytest.raises(TransportUnavailableError, match="TTY"):
        registry.get_image_protocol("kitty")
    assert registry._IMAGE_PROTOCOLS["kitty"].cls is NativeKittyTransport
    assert NativeKittyTransport.supports_inline_placement is False


def test_rich_explicit_kitty_never_calls_unsafe_inline_upload(monkeypatch, dummy_png, capsys):
    monkeypatch.setattr(registry, "_IMAGE_PROTOCOLS", {})
    monkeypatch.setattr(registry, "_ENTRYPOINTS_LOADED", True)
    monkeypatch.setenv("WSKR_PROTOCOL", "kitty")

    def unsafe_upload(*args, **kwargs):
        pytest.fail("Legacy Kitty inline upload and TTY query must not execute")

    monkeypatch.setattr(KittyTransport, "init_image", unsafe_upload)
    monkeypatch.setattr(KittyTransport, "send_image", unsafe_upload)
    image = RichImage(BytesIO(dummy_png), desired_width=20, desired_height=3)

    console = Console(record=True, width=70)
    console.print(Panel(image, title="Safe Kitty Rich fallback"))
    text = console.export_text()
    # A captured/redirected console has no graphics output TTY, so Rich must
    # report no graphics rather than pretend an inline Kitty placement exists.
    assert "image unavailable (no graphics protocol)" in text
    assert "inline placement unavailable" not in text
    assert "Unknown protocol" not in capsys.readouterr().out


def test_unknown_protocol_still_uses_noop(monkeypatch):
    monkeypatch.setattr(registry, "_IMAGE_PROTOCOLS", {})
    monkeypatch.setattr(registry, "_ENTRYPOINTS_LOADED", True)
    assert isinstance(registry.get_image_protocol("not-installed"), NoOpProtocol)

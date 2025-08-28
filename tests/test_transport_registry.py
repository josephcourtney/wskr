import importlib.metadata

import pytest

from wskr.core.config import configure
from wskr.terminal.core.base import ImageTransport
from wskr.terminal.core.registry import (
    get_image_transport,
    load_entry_points,
    register_image_transport,
)
from wskr.terminal.core.transport import NoOpTransport


class FakeTransport(ImageTransport):
    def get_window_size_px(self):
        return (100, 100)

    def send_image(self, png_bytes: bytes) -> None:
        pass

    def init_image(self, png_bytes: bytes) -> int:
        return 1


def test_can_register_and_instantiate_transport():
    configure(FALLBACK="error")
    register_image_transport("fake", FakeTransport)
    transport = get_image_transport("fake")
    assert isinstance(transport, FakeTransport)


def test_fallback_to_noop_transport():
    configure(FALLBACK="noop")
    transport = get_image_transport("nonexistent")
    assert transport.get_window_size_px() == (800, 600)


def test_register_image_transport_invalid_name():
    with pytest.raises(ValueError, match="non-empty string"):
        register_image_transport("", NoOpTransport)
    with pytest.raises(ValueError, match="non-empty string"):
        register_image_transport("   ", NoOpTransport)


def test_register_image_transport_invalid_class():
    class NotATransport:
        pass

    with pytest.raises(TypeError, match="must subclass ImageTransport"):
        register_image_transport("foo", NotATransport)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="must subclass ImageTransport"):
        register_image_transport("bar", object)  # type: ignore[arg-type]


def test_load_entry_points(monkeypatch):
    class DummyEP:
        name = "thirdparty"

        def load(self):
            class DummyTransport(ImageTransport):
                def get_window_size_px(self):
                    return (1, 1)

                def send_image(self, png_bytes: bytes) -> None:
                    return

                def init_image(self, png_bytes: bytes) -> int:
                    return 1

            return DummyTransport

    monkeypatch.setattr(
        importlib.metadata,
        "entry_points",
        lambda group=None: [DummyEP()] if group == "wskr.image_transports" else [],
    )
    from wskr.terminal.core import registry as reg  # noqa: PLC0415

    reg._ENTRYPOINTS_LOADED = False  # type: ignore[attr-defined]
    reg._IMAGE_TRANSPORTS.clear()  # type: ignore[attr-defined]
    load_entry_points()
    assert isinstance(get_image_transport("thirdparty"), ImageTransport)

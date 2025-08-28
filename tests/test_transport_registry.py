import importlib.metadata

import pytest

from wskr.protocol.base import ImageProtocol
from wskr.protocol.noop import NoOpProtocol
from wskr.protocol.registry import (
    get_image_protocol,
    load_entry_points,
    register_image_protocol,
)


class FakeProtocol(ImageProtocol):
    def get_window_size_px(self):
        return (100, 100)

    def send_image(self, png_bytes: bytes) -> None:
        pass

    def init_image(self, png_bytes: bytes) -> int:
        return 1


def test_can_register_and_instantiate_protocol():
    register_image_protocol("fake", FakeProtocol)
    proto = get_image_protocol("fake")
    assert isinstance(proto, FakeProtocol)


def test_fallback_to_noop_protocol():
    proto = get_image_protocol("nonexistent")
    assert proto.get_window_size_px() == (800, 600)


def test_register_image_protocol_invalid_name():
    with pytest.raises(ValueError, match="non-empty string"):
        register_image_protocol("", NoOpProtocol)
    with pytest.raises(ValueError, match="non-empty string"):
        register_image_protocol("   ", NoOpProtocol)


def test_register_image_protocol_invalid_class():
    class NotATransport:
        pass

    with pytest.raises(TypeError, match="must subclass ImageProtocol"):
        register_image_protocol("foo", NotATransport)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="must subclass ImageProtocol"):
        register_image_protocol("bar", object)  # type: ignore[arg-type]


def test_load_entry_points(monkeypatch):
    class DummyEP:
        name = "thirdparty"

        def load(self):
            class DummyProtocol(ImageProtocol):
                def get_window_size_px(self):
                    return (1, 1)

                def send_image(self, png_bytes: bytes) -> None:
                    return

                def init_image(self, png_bytes: bytes) -> int:
                    return 1

            return DummyProtocol

    monkeypatch.setattr(
        importlib.metadata,
        "entry_points",
        lambda group=None: [DummyEP()] if group == "wskr.image_protocols" else [],
    )
    from wskr.protocol import registry as reg  # noqa: PLC0415

    reg._ENTRYPOINTS_LOADED = False  # type: ignore[attr-defined]
    reg._IMAGE_PROTOCOLS.clear()  # type: ignore[attr-defined]
    load_entry_points()
    assert isinstance(get_image_protocol("thirdparty"), ImageProtocol)

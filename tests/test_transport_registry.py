import pytest

from wskr.tty.base import ImageTransport
from wskr.tty.registry import get_image_transport, register_image_transport
from wskr.tty.transport import NoOpTransport


class FakeTransport(ImageTransport):
    def get_window_size_px(self):
        return (100, 100)

    def send_image(self, png_bytes: bytes) -> None:
        pass

    def init_image(self, png_bytes: bytes) -> int:
        return 1


def test_can_register_and_instantiate_transport():
    register_image_transport("fake", FakeTransport)
    transport = get_image_transport("fake")
    assert isinstance(transport, FakeTransport)


def test_fallback_to_noop_transport():
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
        register_image_transport("foo", NotATransport)
    with pytest.raises(TypeError, match="must subclass ImageTransport"):
        register_image_transport("bar", object)

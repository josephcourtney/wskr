from wskr.tty.base import ImageTransport
from wskr.tty.registry import TransportName, get_image_transport, register_image_transport
from wskr.tty.transport import NoOpTransport


class BadTransport(ImageTransport):
    def __init__(self):
        msg = "Initialization failed"
        raise RuntimeError(msg)

    def get_window_size_px(self):
        return (1, 1)

    def send_image(self, png_bytes: bytes) -> None:
        pass

    def init_image(self, png_bytes: bytes) -> int:
        return 0


def test_unknown_key_fallbacks_to_noop():
    t = get_image_transport("does_not_exist")
    assert isinstance(t, NoOpTransport)


def test_bad_transport_registration(monkeypatch):
    register_image_transport("bad", BadTransport)
    t = get_image_transport("bad")
    assert isinstance(t, NoOpTransport)


def test_get_image_transport_with_enum(monkeypatch):
    monkeypatch.setattr(
        "wskr.tty.registry._IMAGE_TRANSPORTS",
        {TransportName.NOOP.value: NoOpTransport},
    )
    t = get_image_transport(TransportName.NOOP)
    assert isinstance(t, NoOpTransport)

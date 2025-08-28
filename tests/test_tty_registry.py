import importlib.metadata
from types import SimpleNamespace

from wskr.protocol import registry
from wskr.protocol.base import ImageProtocol
from wskr.protocol.noop import NoOpProtocol
from wskr.protocol.registry import get_image_protocol, register_image_protocol


class BadProtocol(ImageProtocol):
    def __init__(self):
        msg = "boom"
        raise RuntimeError(msg)

    def get_window_size_px(self):  # pragma: no cover - not invoked
        return (1, 1)

    def send_image(self, png_bytes: bytes) -> None:  # pragma: no cover - not invoked
        pass

    def init_image(self, png_bytes: bytes) -> int:  # pragma: no cover - not invoked
        return 0


class DummyProtocol(NoOpProtocol):
    pass


def test_unknown_key_returns_noop():
    t = get_image_protocol("does_not_exist")
    assert isinstance(t, NoOpProtocol)


def test_bad_protocol_registration_raises():
    register_image_protocol("bad", BadProtocol)
    # registry falls back to NoOpProtocol on init failure
    proto = get_image_protocol("bad")
    assert isinstance(proto, NoOpProtocol)


def test_disabled_protocol_raises():
    register_image_protocol("disabled", DummyProtocol, enabled=False)
    # disabled protocols also fall back to NoOpProtocol
    proto = get_image_protocol("disabled")
    assert isinstance(proto, NoOpProtocol)


def test_entry_points_autoload(monkeypatch):
    monkeypatch.setattr(registry, "_IMAGE_PROTOCOLS", {"noop": registry._ProtocolEntry(NoOpProtocol)})
    monkeypatch.setattr(registry, "_ENTRYPOINTS_LOADED", False)

    ep = SimpleNamespace(name="dummy", load=lambda: DummyProtocol)

    def fake_entry_points(*, group):
        return [ep] if group == "wskr.image_protocols" else []

    monkeypatch.setattr(importlib.metadata, "entry_points", fake_entry_points)
    t = get_image_protocol("dummy")
    assert isinstance(t, DummyProtocol)


def test_entry_points_failure(monkeypatch):
    monkeypatch.setattr(registry, "_ENTRYPOINTS_LOADED", False)

    def bad_entry_points(*, group):
        msg = "boom"
        raise RuntimeError(msg)

    monkeypatch.setattr(importlib.metadata, "entry_points", bad_entry_points)
    # Should not raise despite entry point discovery failure
    assert isinstance(get_image_protocol("noop"), NoOpProtocol)

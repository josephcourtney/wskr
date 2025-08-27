import importlib.metadata
from types import SimpleNamespace

import pytest

from wskr.config import configure
from wskr.errors import TransportInitError, TransportUnavailableError
from wskr.tty import registry
from wskr.tty.base import ImageTransport
from wskr.tty.registry import TransportName, get_image_transport, register_image_transport
from wskr.tty.transport import NoOpTransport


class BadTransport(ImageTransport):
    def __init__(self):
        msg = "boom"
        raise RuntimeError(msg)

    def get_window_size_px(self):  # pragma: no cover - not invoked
        return (1, 1)

    def send_image(self, png_bytes: bytes) -> None:  # pragma: no cover - not invoked
        pass

    def init_image(self, png_bytes: bytes) -> int:  # pragma: no cover - not invoked
        return 0


class DummyTransport(NoOpTransport):
    pass


def setup_module(module):
    configure(FALLBACK="noop")


def test_unknown_key_returns_noop_when_policy_noop():
    configure(FALLBACK="noop")
    t = get_image_transport("does_not_exist")
    assert isinstance(t, NoOpTransport)


def test_unknown_key_raises_when_policy_error():
    configure(FALLBACK="error")
    with pytest.raises(TransportUnavailableError):
        get_image_transport("does_not_exist")
    configure(FALLBACK="noop")


def test_bad_transport_registration_raises():
    configure(FALLBACK="error")
    register_image_transport("bad", BadTransport)
    with pytest.raises(TransportInitError):
        get_image_transport("bad")
    configure(FALLBACK="noop")


def test_disabled_transport_raises():
    configure(FALLBACK="error")
    register_image_transport("disabled", DummyTransport, enabled=False)
    with pytest.raises(TransportUnavailableError):
        get_image_transport("disabled")
    configure(FALLBACK="noop")


def test_entry_points_autoload(monkeypatch):
    configure(FALLBACK="error")
    monkeypatch.setattr(
        registry, "_IMAGE_TRANSPORTS", {TransportName.NOOP.value: registry._TransportEntry(NoOpTransport)}
    )
    monkeypatch.setattr(registry, "_ENTRYPOINTS_LOADED", False)

    ep = SimpleNamespace(name="dummy", load=lambda: DummyTransport)

    def fake_entry_points(*, group):
        return [ep] if group == "wskr.image_transports" else []

    monkeypatch.setattr(importlib.metadata, "entry_points", fake_entry_points)
    t = get_image_transport("dummy")
    assert isinstance(t, DummyTransport)
    configure(FALLBACK="noop")


def test_entry_points_failure(monkeypatch):
    configure(FALLBACK="noop")
    monkeypatch.setattr(registry, "_ENTRYPOINTS_LOADED", False)

    def bad_entry_points(*, group):
        msg = "boom"
        raise RuntimeError(msg)

    monkeypatch.setattr(importlib.metadata, "entry_points", bad_entry_points)
    # Should not raise despite entry point discovery failure
    assert isinstance(get_image_transport("noop"), NoOpTransport)


def test_get_image_transport_with_enum(monkeypatch):
    monkeypatch.setattr(
        registry,
        "_IMAGE_TRANSPORTS",
        {TransportName.NOOP.value: registry._TransportEntry(NoOpTransport)},
    )
    t = get_image_transport(TransportName.NOOP)
    assert isinstance(t, NoOpTransport)

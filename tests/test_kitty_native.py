"""Deterministic tests for Phase 2 Kitty framing and ownership."""

from __future__ import annotations

import base64
import sys

import pytest

from wskr.core.errors import TransportRuntimeError, TransportUnavailableError
from wskr.protocol import kitty_io
from wskr.protocol.kitty_codec import (
    MAX_CHUNK,
    command,
    delete,
    parse_response,
    placement,
    probe_request,
    transmit,
)
from wskr.protocol.kitty_native import KittyImageManager, NativeKittyTransport

pytestmark = pytest.mark.small
PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 6500


def test_png_chunking_and_roundtrip() -> None:
    frames = list(transmit(PNG, 17))
    assert len(frames) >= 3
    payloads = [frame.split(b";", 1)[1].removesuffix(b"\x1b\\") for frame in frames]
    assert all(len(part) <= MAX_CHUNK for part in payloads)
    assert base64.b64decode(b"".join(payloads)) == PNG
    assert frames[0].startswith(b"\x1b_Ga=t,f=100,t=d,i=17,q=2,m=1;")
    assert frames[1].startswith(b"\x1b_Gm=1,q=2;")
    assert frames[-1].startswith(b"\x1b_Gm=0,q=2;")
    assert all(frame.endswith(b"\x1b\\") for frame in frames)


def test_small_display_and_validated_identity() -> None:
    frames = list(transmit(PNG[:20], 7, display=True, placement_id=13))
    assert len(frames) == 1
    assert frames[0].startswith(b"\x1b_Ga=T,f=100,t=d,i=7,q=2,p=13,m=0;")
    with pytest.raises(ValueError, match="PNG"):
        list(transmit(b"not a PNG", 1))
    with pytest.raises(ValueError, match="IDs"):
        list(transmit(PNG, 0))
    with pytest.raises(ValueError, match="placement ID"):
        list(transmit(PNG, 1, placement_id=2))


def test_scoped_placement_and_deletion_frames() -> None:
    assert placement(4, 11, 30, 5) == b"\x1b_Ga=p,i=4,p=11,c=30,r=5,C=1,q=2\x1b\\"
    assert placement(4, 11, 30, 5, virtual=True) == b"\x1b_Ga=p,i=4,p=11,c=30,r=5,U=1,q=2\x1b\\"
    assert delete(4, placement_id=11) == b"\x1b_Ga=d,d=i,i=4,p=11,q=2\x1b\\"
    assert delete(4, free=True) == b"\x1b_Ga=d,d=I,i=4,q=2\x1b\\"
    assert b"a=d" not in command(a="p", i=1)
    with pytest.raises(ValueError, match="dimensions"):
        placement(1, 1, 0, 2)


def test_graphics_query_and_ack_validation() -> None:
    frame = probe_request(99)
    assert frame.startswith(b"\x1b_Ga=q,f=32,s=1,v=1,i=99,t=d;")
    assert frame.endswith(b"AAAAAA==\x1b\\")
    assert parse_response(b"\x1b_Gi=99,p=8;OK\x1b\\", expected_id=99) == (99, 8)
    with pytest.raises(TransportRuntimeError, match="another image"):
        parse_response(b"\x1b_Gi=99;OK\x1b\\", expected_id=98)
    with pytest.raises(TransportRuntimeError, match="rejected"):
        parse_response(b"\x1b_Gi=99;ENOENT:not found\x1b\\", expected_id=99)
    with pytest.raises(TransportRuntimeError, match="Malformed"):
        parse_response(b"not an ACK")


def test_manager_upload_place_reuse_and_scoped_cleanup(monkeypatch) -> None:
    writes: list[bytes] = []
    numbers = iter([13, 9, 17])
    monkeypatch.setattr("wskr.protocol.kitty_native.secrets.randbelow", lambda _bound: next(numbers) - 1)
    manager = KittyImageManager(lambda frames: writes.extend(frames))
    image = manager.upload(PNG)
    physical = manager.place(image, columns=20, rows=4)
    virtual = manager.place(image, columns=18, rows=3, virtual=True)
    assert (image, physical, virtual) == (13, 9, 17)
    manager.place(image, columns=22, rows=5, placement_id=physical)
    manager.remove_placement(image, physical)
    assert b"d=i,i=13,p=9" in writes[-1]
    manager.close()
    assert b"d=I,i=13" in writes[-1]
    manager.close()
    assert not any(b"a=d,d=a" in frame for frame in writes)
    with pytest.raises(TransportRuntimeError, match="closed"):
        manager.upload(PNG)


def test_manager_rejects_foreign_ids_without_writing() -> None:
    writes: list[bytes] = []
    manager = KittyImageManager(lambda frames: writes.extend(frames))
    with pytest.raises(TransportRuntimeError, match="not owned"):
        manager.place(999, columns=1, rows=1)
    with pytest.raises(TransportRuntimeError, match="not owned"):
        manager.remove_image(999)
    assert not writes


def test_direct_transport_has_rich_ready_placement_but_no_premature_inline_claim(monkeypatch) -> None:
    writes: list[bytes] = []
    monkeypatch.setattr("wskr.protocol.kitty_native.secrets.randbelow", lambda _bound: 100)
    transport = NativeKittyTransport(writer=lambda frames: writes.extend(frames))
    assert transport.supports_virtual_placement
    assert not transport.supports_inline_placement
    image = transport.init_image(PNG)
    pid = transport.place_image(image, columns=3, rows=2, virtual=True)
    assert pid > 0
    assert any(b"U=1" in frame for frame in writes)
    transport.close()


def test_no_redirected_raw_output(monkeypatch) -> None:
    class PipeOutput:
        def isatty(self) -> bool:
            return False

    monkeypatch.setattr(sys, "stdout", PipeOutput())
    with pytest.raises(TransportUnavailableError, match="TTY"):
        kitty_io.send_frames([b"\x1b_Ga=p;\x1b\\"])
    with pytest.raises(TransportUnavailableError, match="foreground TTY"):
        NativeKittyTransport()


def test_input_ownership_required_for_query() -> None:
    with pytest.raises(TransportUnavailableError, match="exclusive"):
        kitty_io.query_support(probe_request(1), expected_id=1)


def test_placeholder_encoding_and_boundaries() -> None:
    from wskr.protocol.kitty_placeholders import diacritics, placeholder_rows

    table = diacritics()
    assert len(table) == 297
    assert table[0] == chr(0x0305)
    encoded = placeholder_rows(42, 7, columns=2, rows=2)
    assert len(encoded) == 2
    assert all(row.count(chr(0x10EEEE)) == 2 for row in encoded)
    assert f"{chr(27)}[38;2;0;0;42m" in encoded[0]
    assert f"{chr(27)}[58;2;0;0;7m" in encoded[0]
    assert table[0] + table[1] in encoded[0]
    high = placeholder_rows((2 << 24) + 42, 7, columns=1, rows=1)
    assert table[2] in high[0]
    with pytest.raises(ValueError, match="diacritic"):
        placeholder_rows(42, 7, columns=298, rows=1)
    with pytest.raises(ValueError, match="24-bit"):
        placeholder_rows(42, 0x1000000, columns=1, rows=1)


def test_owned_query_forwards_foreign_replies_and_restores_tty(monkeypatch) -> None:
    requests: list[bytes] = []
    handled: list[bytes] = []
    closed: list[int] = []
    restored: list[object] = []

    def response(image: int) -> bytes:
        return bytes((27,)) + b"_Gi=" + str(image).encode() + b";OK" + bytes((27, 92))

    replies = iter((response(8), response(9)))

    def fake_attributes(_fd):
        return [0, 0, 0, 0, 0, 0, [0] * 32]

    monkeypatch.setattr(kitty_io, "_require_tty", lambda: None)
    monkeypatch.setattr(kitty_io, "_open", lambda: 11)
    monkeypatch.setattr(kitty_io, "_send", lambda _fd, frame, _deadline: requests.append(frame))
    monkeypatch.setattr(kitty_io, "_read_reply", lambda *_args: next(replies))
    monkeypatch.setattr(kitty_io.termios, "tcgetattr", fake_attributes)
    monkeypatch.setattr(kitty_io.termios, "tcsetattr", lambda _fd, _how, attrs: restored.append(attrs))
    monkeypatch.setattr(kitty_io.os, "close", closed.append)

    assert kitty_io.query_support(probe_request(9), expected_id=9, owns_input=True, on_unmatched=handled.append)
    assert requests == [probe_request(9)]
    assert handled == [response(8)]
    assert closed == [11]
    assert len(restored) == 2


def test_native_request_does_not_silently_fall_back_to_noop(monkeypatch) -> None:
    from wskr.protocol.registry import get_image_protocol

    class Pipe:
        def isatty(self) -> bool:
            return False

    monkeypatch.setattr(sys, "stdout", Pipe())
    with pytest.raises(TransportUnavailableError, match="TTY"):
        get_image_protocol("kitty")


def test_virtual_placement_allocates_encodable_id(monkeypatch) -> None:
    bounds: list[int] = []

    def fake_randbelow(bound: int) -> int:
        bounds.append(bound)
        return bound - 1

    monkeypatch.setattr("wskr.protocol.kitty_native.secrets.randbelow", fake_randbelow)
    frames: list[bytes] = []
    manager = KittyImageManager(lambda chunks: frames.extend(chunks))
    image = manager.upload(PNG)
    virtual = manager.place(image, columns=1, rows=1, virtual=True)
    assert image == 0xFFFFFFFF
    assert virtual == 0xFFFFFF
    assert bounds == [0xFFFFFFFF, 0xFFFFFF]
    with pytest.raises(ValueError, match="24-bit"):
        manager.place(image, placement_id=0x1000000, columns=1, rows=1, virtual=True)

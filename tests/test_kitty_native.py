"""Deterministic tests for Phase 2 Kitty framing and ownership."""

from __future__ import annotations

import base64
import sys
from io import BytesIO

import pytest
from PIL import Image

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
from wskr.terminal.profile import Geometry

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
    manager = KittyImageManager(writes.extend)
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
    manager = KittyImageManager(writes.extend)
    with pytest.raises(TransportRuntimeError, match="not owned"):
        manager.place(999, columns=1, rows=1)
    with pytest.raises(TransportRuntimeError, match="not owned"):
        manager.remove_image(999)
    assert not writes


def test_direct_transport_has_rich_ready_placement_but_no_premature_inline_claim(monkeypatch) -> None:
    writes: list[bytes] = []
    monkeypatch.setattr("wskr.protocol.kitty_native.secrets.randbelow", lambda _bound: 100)
    transport = NativeKittyTransport(writer=writes.extend)
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
    manager = KittyImageManager(frames.extend)
    image = manager.upload(PNG)
    virtual = manager.place(image, columns=1, rows=1, virtual=True)
    assert image == 0xFFFFFFFF
    assert virtual == 0xFFFFFF
    assert bounds == [0xFFFFFFFF, 0xFFFFFF]
    with pytest.raises(ValueError, match="24-bit"):
        manager.place(image, placement_id=0x1000000, columns=1, rows=1, virtual=True)


def test_failed_upload_does_not_claim_owned_image(dummy_png) -> None:
    """A failed writer must not register an upload that Kitty never received."""

    def fail(frames) -> None:
        list(frames)
        msg = "simulated terminal write failure"
        raise OSError(msg)

    manager = KittyImageManager(fail)
    with pytest.raises(OSError, match="write failure"):
        manager.upload(dummy_png)
    assert manager._images == {}


def test_failed_placement_does_not_claim_owned_placement(dummy_png, monkeypatch) -> None:
    """Failed placement control must not corrupt the manager's local state."""
    calls = 0

    def write(frames) -> None:
        nonlocal calls
        calls += 1
        list(frames)
        if calls == 2:
            msg = "placement failed"
            raise OSError(msg)

    monkeypatch.setattr("wskr.protocol.kitty_native.secrets.randbelow", lambda _bound: 8)
    manager = KittyImageManager(write)
    image = manager.upload(dummy_png)
    with pytest.raises(OSError, match="placement failed"):
        manager.place(image, columns=2, rows=1, virtual=True)
    assert manager._images[image] == set()


@pytest.mark.parametrize(
    ("image_id", "placement_id", "columns", "rows"),
    [
        (42, 7, 2, 2),
        (0xFFFFFFFF, 0xFFFFFF, 4, 3),
        (1, 1, 1, 1),
        (33554474, 150, 7, 3),
    ],
)
def test_placeholder_colors_and_coordinates_for_full_id_range(image_id, placement_id, columns, rows) -> None:
    """Encode every placeholder cell with explicit high-ID and cell coordinates."""
    from wskr.protocol.kitty_placeholders import diacritics, placeholder_rows

    table = diacritics()
    rendered = placeholder_rows(image_id, placement_id, columns=columns, rows=rows)
    assert len(rendered) == rows
    high = image_id >> 24
    fg = f"\x1b[38;2;{(image_id >> 16) & 255};{(image_id >> 8) & 255};{image_id & 255}m"
    ul = f"\x1b[58;2;{(placement_id >> 16) & 255};{(placement_id >> 8) & 255};{placement_id & 255}m"
    for row, text in enumerate(rendered):
        assert text.startswith(fg + ul)
        assert text.endswith("\x1b[39;59m")
        assert text.count(chr(0x10EEEE)) == columns
        for column in range(columns):
            assert chr(0x10EEEE) + table[row] + table[column] + (table[high] if high else "") in text


def test_sized_anchor_and_relative_placement_codec() -> None:
    """Only a cursor-moving transparent anchor reserves terminal rows."""
    frames = list(transmit(PNG[:20], 5, display=True, placement_id=7, columns=24, rows=6))
    assert len(frames) == 1
    assert b"p=7,c=24,r=6,m=0;" in frames[0]
    assert placement(8, 9, parent=(5, 7)) == bytes([27]) + b"_Ga=p,i=8,p=9,P=5,Q=7,q=2" + bytes([27, 92])
    with pytest.raises(ValueError, match="both columns"):
        list(transmit(PNG, 5, display=True, columns=4))
    with pytest.raises(ValueError, match="Virtual"):
        placement(8, 9, columns=1, rows=1, parent=(5, 7), virtual=True)
    with pytest.raises(ValueError, match="dimensions"):
        placement(8, 9)


def test_fitted_kitty_anchor_survives_replacement_and_static_exit(monkeypatch) -> None:
    """Redraws refer to the same original placement, not the moved cursor."""
    monkeypatch.setattr(
        "wskr.protocol.kitty_native.read_geometry",
        lambda: Geometry(25, 80, 800, 500),
    )
    source = BytesIO()
    Image.new("RGB", (320, 100), "red").save(source, "PNG")
    frames: list[bytes] = []
    transport = NativeKittyTransport(writer=frames.extend)
    transport.send_anchored_image(source.getvalue())
    anchor = transport._anchor
    assert anchor is not None
    first = transport._display_image_id
    assert first is not None
    assert any(f"a=T,f=100,t=d,i={anchor[0]}".encode() in x and b"c=32,r=5" in x for x in frames)
    assert any(f"P={anchor[0]},Q={anchor[1]}".encode() in x for x in frames)
    assert not any(b"\\x1b[H" in x or b"\\x1b[?1049" in x for x in frames)

    transport.send_anchored_image(source.getvalue())
    second = transport._display_image_id
    assert second is not None
    assert second != first
    assert transport._anchor == anchor
    assert sum(b"a=T" in frame for frame in frames) == 1
    assert any(f"a=d,d=I,i={first}".encode() in x for x in frames)
    assert not any(f"a=d,d=I,i={anchor[0]}".encode() in x for x in frames)
    transport.retain_display()
    transport.close()
    assert not any(f"a=d,d=I,i={second}".encode() in x for x in frames)
    assert not any(f"a=d,d=I,i={anchor[0]}".encode() in x for x in frames)


def test_explicit_anchored_close_cleans_child_and_parent(monkeypatch) -> None:
    monkeypatch.setattr(
        "wskr.protocol.kitty_native.read_geometry",
        lambda: Geometry(25, 80, 800, 500),
    )
    source = BytesIO()
    Image.new("RGB", (320, 100), "blue").save(source, "PNG")
    frames: list[bytes] = []
    transport = NativeKittyTransport(writer=frames.extend)
    transport.send_anchored_image(source.getvalue())
    anchor = transport._anchor
    child = transport._display_image_id
    assert anchor is not None
    assert child is not None
    transport.close()
    assert any(f"a=d,d=I,i={child}".encode() in frame for frame in frames)
    assert any(f"a=d,d=I,i={anchor[0]}".encode() in frame for frame in frames)
    assert not any(b"a=d,d=a" in frame for frame in frames)

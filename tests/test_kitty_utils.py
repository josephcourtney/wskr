from __future__ import annotations

import wskr.kitty.utils as ku


def test_query_kitty_color(monkeypatch):
    def fake_query(request: bytes, more, timeout):  # noqa: ANN001 - test stub
        assert request == b"\x1b]21;background=?\x07"
        return b"\x1b]21;background=rgb:12/34/56\x07"

    monkeypatch.setattr(ku, "query_tty", fake_query)
    assert ku.query_kitty_color("background") == (0x12, 0x34, 0x56)


def test_query_colors(monkeypatch):
    def fake_query(request: bytes, more, timeout):  # noqa: ANN001 - test stub
        assert request == b"\x1b]21;foreground=?;background=?\x07"
        return b"\x1b]21;foreground=rgb:00/11/22;background=rgb:33/44/55\x07"

    monkeypatch.setattr(ku, "query_tty", fake_query)
    res = ku.query_colors(["foreground", "background"])
    assert res["foreground"] == (0x00, 0x11, 0x22)
    assert res["background"] == (0x33, 0x44, 0x55)

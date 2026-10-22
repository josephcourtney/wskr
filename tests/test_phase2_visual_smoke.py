"""Phase 2 GUI-smoke contract without launching Kitty or touching a TTY."""

from __future__ import annotations

import pytest

from scripts import phase2_visual_smoke as smoke

pytestmark = pytest.mark.small
_PNG = b"\x89PNG\r\n\x1a\n" + b"synthetic test payload"


def test_native_smoke_generates_png_without_terminal_io() -> None:
    assert smoke._png().startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.parametrize("mode", ["native-physical", "native-virtual"])
def test_native_smoke_emits_ready_marker_after_render(monkeypatch, tmp_path, capsys, mode) -> None:
    calls: list[tuple[int, int, bool]] = []

    class FakeTransport:
        def init_image(self, data: bytes) -> int:
            assert data == _PNG
            return 42

        def place_image(self, _image_id: int, *, columns: int, rows: int, virtual: bool) -> int:
            calls.append((columns, rows, virtual))
            return 17

    monkeypatch.setattr(smoke, "_png", lambda: _PNG)
    monkeypatch.setattr(smoke, "NativeKittyTransport", FakeTransport)
    monkeypatch.setattr(smoke, "placeholder_rows", lambda *_args, **_kwargs: ("ROW0", "ROW1"))

    reference = tmp_path / "reference.png"
    marker = tmp_path / "ready.txt"
    smoke.main(["--mode", mode, "--reference", str(reference), "--ready-file", str(marker)])

    assert marker.read_text(encoding="utf-8").strip() == "render-complete"
    assert reference.read_bytes() == _PNG
    assert calls == [(smoke._COLUMNS, smoke._ROWS, mode == "native-virtual")]
    text = capsys.readouterr().out
    assert "image id: 42; placement id: 17" in text
    assert ("ROW0" in text) == (mode == "native-virtual")

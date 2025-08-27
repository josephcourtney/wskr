from rich.console import Console

from wskr.kitty.rich.img import RichImage
from wskr.tty.base import ImageTransport


class DummyTransport(ImageTransport):
    def __init__(self):
        self.png = None
        self.counter = 0

    def init_image(self, png_bytes: bytes) -> int:
        self.png = png_bytes
        self.counter += 1
        return self.counter

    def get_window_size_px(self):
        return (0, 0)

    def send_image(self, png_bytes: bytes) -> None:
        pass


def test_rich_image_loads_from_filepath(tmp_path):
    data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 10
    p = tmp_path / "image.png"
    p.write_bytes(data)

    transport = DummyTransport()
    rich_img = RichImage(str(p), desired_width=3, desired_height=2, transport=transport)

    assert rich_img.image_id == 1
    assert transport.png == data

    console = Console(record=True)
    console.print(rich_img)
    output = console.export_text().splitlines()
    non_empty = [line for line in output if line.strip()]
    assert len(non_empty) == 2


def test_rich_image_fallback(tmp_path):
    data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 10
    p = tmp_path / "image.png"
    p.write_bytes(data)

    class FallbackTransport(ImageTransport):
        def __init__(self):
            self.sent = False

        def init_image(self, png_bytes: bytes) -> int:
            msg = "nope"
            raise RuntimeError(msg)

        def get_window_size_px(self):
            return (0, 0)

        def send_image(self, png_bytes: bytes) -> None:
            self.sent = True

    transport = FallbackTransport()
    rich_img = RichImage(str(p), desired_width=3, desired_height=2, transport=transport)

    console = Console(record=True)
    console.print(rich_img)
    assert transport.sent

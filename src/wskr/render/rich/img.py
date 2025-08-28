# ruff: noqa: PLW3201
from io import BytesIO
from pathlib import Path

from rich.console import Console, ConsoleOptions, RenderResult
from rich.measure import Measurement
from rich.text import Text

from wskr.protocol import ImageProtocol, get_image_protocol

# diacritics used to encode the row and column indices


# load diacritics table from external data file
_rcd_path = Path(__file__).with_name("rcd.txt")
RCD: str = _rcd_path.read_text(encoding="utf-8")


class RichImage:
    """Rich renderable: upload PNG once (init_image) then paint it cell-by-cell."""

    __slots__ = ("_fallback_sent", "_png", "desired_height", "desired_width", "image_id", "transport")

    image_number = 0

    def __init__(
        self,
        image_path: str | BytesIO,
        desired_width: int,
        desired_height: int,
        transport: ImageProtocol | None = None,
    ):
        self.desired_width = desired_width
        self.desired_height = desired_height
        self.transport = transport or get_image_protocol()

        if isinstance(image_path, BytesIO):
            image_path.seek(0)
            png = image_path.read()
        else:
            png = Path(image_path).read_bytes()
        self._png = png

        try:
            self.image_id = self.transport.init_image(png)
        except RuntimeError:
            self.image_id = -1
        self._fallback_sent = False

    def __rich_measure__(self, console: Console, options: ConsoleOptions) -> Measurement:  # noqa: D105
        return Measurement(self.desired_width, self.desired_width)

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:  # noqa: D105
        if self.image_id == -1 and not self._fallback_sent:
            self.transport.send_image(self._png)
            self._fallback_sent = True
            return

        # paint each row with the kitty color trick
        for row in range(self.desired_height):
            esc = f"\x1b[38;5;{self.image_id}m"
            line = (
                esc
                + "".join(f"\U0010eeee{RCD[row]}{RCD[col]}" for col in range(self.desired_width))
                + "\x1b[39m"
            )
            yield Text.from_ansi(line)

# ruff: noqa: PLW3201
from io import BytesIO
from pathlib import Path
from typing import ClassVar

from rich.console import Console, ConsoleOptions, RenderResult
from rich.measure import Measurement
from rich.table import Table
from rich.text import Text

from wskr.tty.registry import get_image_transport
from wskr.tty.transport import ImageTransport

# diacritics used to encode the row and column indices


# load diacritics table from external data file
_rcd_path = Path(__file__).with_name("rcd.txt")
RCD: ClassVar[str] = _rcd_path.read_text(encoding="utf-8")


class RichImage:
    """Rich renderable: upload PNG once (init_image) then paint it cell-by-cell."""

    __slots__ = ("_fallback_sent", "_png", "desired_height", "desired_width", "image_id", "transport")

    image_number = 0

    def __init__(
        self,
        image_path: str | BytesIO,
        desired_width: int,
        desired_height: int,
        transport: ImageTransport | None = None,
    ):
        self.desired_width = desired_width
        self.desired_height = desired_height
        self.transport = transport or get_image_transport()

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


if __name__ == "__main__":
    console = Console()
    placeholder_0 = RichImage("./test.png", 7, 4)

    placeholder_1 = RichImage("./test.png", 8, 5)

    placeholder_2 = RichImage("./test.png", 11, 6)

    table = Table(title="Star Wars Movies", show_lines=True)

    table.add_column("Released", justify="right", style="cyan", no_wrap=True)
    table.add_column("Title", justify="center", style="magenta")
    table.add_column("Box Office", justify="left", style="green")

    table.add_row("Dec 20, 2019", "Star Wars: The Rise of Skywalker", "$952,110,690")
    table.add_row(placeholder_0, placeholder_1, placeholder_2)
    table.add_row("Dec 15, 2017", "Star Wars Ep. VIII: The Last Jedi", "$1,332,539,889")
    table.add_row("Dec 16, 2016", "Rogue One: A Star Wars Story", "$1,332,439,889")

    console.print(table)

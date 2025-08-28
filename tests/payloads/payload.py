import argparse
import os
from pathlib import Path

from PIL import Image, ImageDraw

import wskr.protocol.kitty  # noqa: F401  ensure Kitty protocol registers itself
from wskr.protocol.registry import get_image_protocol


def draw_circle(size):
    im = Image.new("RGB", size, "black")
    draw = ImageDraw.Draw(im)
    cx, cy = size[0] // 2, size[1] // 2
    r = min(size) // 4
    bbox = (cx - r, cy - r, cx + r, cy + r)
    draw.ellipse(bbox, fill="white")
    return im


def draw_checker(size, squares=8):
    im = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(im)
    w, h = size
    sx, sy = w // squares, h // squares
    for i in range(squares):
        for j in range(squares):
            if (i + j) % 2 == 0:
                draw.rectangle([i * sx, j * sy, (i + 1) * sx, (j + 1) * sy], fill="black")
    return im


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--scenario", choices=["circle", "checker"], required=True)
    p.add_argument("--width", type=int, default=200)
    p.add_argument("--height", type=int, default=200)
    p.add_argument("--zoom", type=float, default=1.0)
    p.add_argument("--transport", default=os.getenv("WSKR_TRANSPORT", "kitty"))
    args = p.parse_args()

    # pick image
    size = (int(args.width * args.zoom), int(args.height * args.zoom))
    im = draw_circle(size) if args.scenario == "circle" else draw_checker(size)

    # write to a temp file that Kitty will display
    out = Path.cwd() / "payload.png"
    im.save(out)

    # send via wskr
    png = out.read_bytes()
    get_image_protocol(args.transport).send_image(png)
    Path(os.environ["KITTY_DEMO_DONE_FILE"]).write_text("done", encoding="utf-8")
    input("press ENTER…")

    # signal done
    done = os.environ["KITTY_DEMO_DONE_FILE"]
    Path(done).write_text("done", encoding="utf-8")

    # wait for user (so we can screenshot)
    input("enter to finish…")


if __name__ == "__main__":
    main()

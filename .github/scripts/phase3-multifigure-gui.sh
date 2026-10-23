#!/usr/bin/env bash
# Prove two independent Matplotlib figures occupy distinct fitted Kitty tiles.
set -Eeuo pipefail

out="${RUNNER_TEMP:-/tmp}/wskr-phase3-multifigure"
mkdir -p "$out"
ready="$out/ready"
proceed="$out/proceed"
closed="$out/closed"
log="$out/kitty.log"
rm -f "$ready" "$proceed" "$closed"

WSKR_FIT=contain kitty --config NONE --title "wskr-multifigure-acceptance" --hold \
  uv run python scripts/phase3_multifigure_smoke.py \
    --ready "$ready" --proceed "$proceed" --closed "$closed" >"$log" 2>&1 &
pid=$!
finish() {
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" || true
    wait "$pid" || true
  fi
}
trap finish EXIT

for _ in $(seq 1 120); do
  if [[ -s "$ready" ]]; then break; fi
  if ! kill -0 "$pid" 2>/dev/null; then break; fi
  sleep 0.1
done
if [[ ! -s "$ready" ]]; then
  cat "$log" >&2
  echo "Two figures did not reach the alternate-screen handoff" >&2
  exit 1
fi
sleep 0.4
xwd -root -silent -out "$out/contact.xwd"
convert "$out/contact.xwd" "$out/contact.png"
touch "$proceed"

for _ in $(seq 1 120); do
  if [[ -s "$closed" ]]; then break; fi
  if ! kill -0 "$pid" 2>/dev/null; then break; fi
  sleep 0.1
done
if [[ ! -s "$closed" ]]; then
  cat "$log" >&2
  echo "Contact-sheet close did not restore terminal" >&2
  exit 1
fi
sleep 0.3
xwd -root -silent -out "$out/restored.xwd"
convert "$out/restored.xwd" "$out/restored.png"

uv run python - "$out/contact.png" "$out/restored.png" <<'PY'
import sys
from PIL import Image


def positions(path):
    with Image.open(path) as image:
        raster = image.convert("RGB")
        points = {"red": [], "blue": []}
        for y in range(raster.height):
            for x in range(raster.width):
                r, g, b = raster.getpixel((x, y))
                if r > 215 and g < 50 and b < 50:
                    points["red"].append(x)
                if b > 215 and r < 50 and g < 50:
                    points["blue"].append(x)
        return points


present = positions(sys.argv[1])
restored = positions(sys.argv[2])
print("contact sheet:", {kind: (len(x), min(x) if x else None, max(x) if x else None) for kind, x in present.items()})
print("restored:", {kind: len(x) for kind, x in restored.items()})
assert len(present["red"]) > 4000, "first/red figure not visible"
assert len(present["blue"]) > 4000, "second/blue figure not visible"
assert max(present["red"]) + 2 < min(present["blue"]), "figures overlap or wrong horizontal order"
assert sum(len(x) for x in restored.values()) < 80, "figures remained after closing"
PY

finish
trap - EXIT
echo "Real Kitty two-figure contact sheet and restored primary screen passed."

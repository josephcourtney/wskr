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


def counts(path):
    with Image.open(path) as image:
        raster = image.convert("RGB")
        halves = [{"red": 0, "blue": 0}, {"red": 0, "blue": 0}]
        for y in range(raster.height):
            for x in range(raster.width):
                r, g, b = raster.getpixel((x, y))
                slot = halves[int(x >= raster.width // 2)]
                if r > 215 and g < 50 and b < 50:
                    slot["red"] += 1
                if b > 215 and r < 50 and g < 50:
                    slot["blue"] += 1
        return halves


present = counts(sys.argv[1])
restored = counts(sys.argv[2])
print(f"contact sheet color separation: {present}; restored: {restored}")
assert present[0]["red"] > 4000, "first/red figure not visible on left"
assert present[1]["blue"] > 4000, "second/blue figure not visible on right"
assert present[0]["blue"] < 40, "blue figure overlaps red figure"
assert present[1]["red"] < 40, "red figure overlaps blue figure"
assert sum(sum(half.values()) for half in restored) < 80, "figures remained after closing"
PY

finish
trap - EXIT
echo "Real Kitty two-figure contact sheet and restored primary screen passed."

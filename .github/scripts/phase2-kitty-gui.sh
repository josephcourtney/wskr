#!/usr/bin/env bash
# Hosted graphical validation of native physical and Unicode virtual placement.
set -Eeuo pipefail

out="${RUNNER_TEMP:-/tmp}/wskr-kitty-gui"
mkdir -p "$out"

for mode in native-physical native-virtual; do
  ready="$out/$mode.ready"
  reference="$out/$mode-reference.png"
  log="$out/$mode-kitty.log"
  screen="$out/$mode-screen.png"
  rm -f "$ready"
  kitty --config NONE --title "wskr-$mode" --hold     uv run python scripts/phase2_visual_smoke.py       --mode "$mode" --ready-file "$ready" --reference "$reference"       >"$log" 2>&1 &
  pid=$!

  finish() {
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" || true
      wait "$pid" || true
    fi
  }
  trap finish EXIT
  seen=0
  for _ in $(seq 1 120); do
    if [[ -s "$ready" ]]; then
      seen=1
      break
    fi
    if ! kill -0 "$pid" 2>/dev/null; then
      break
    fi
    sleep 0.25
  done
  if [[ "$seen" != 1 ]]; then
    echo "Kitty failed to render $mode; diagnostics:" >&2
    cat "$log" >&2
    exit 1
  fi
  sleep 0.7
  xwd -root -silent -out "$out/$mode.xwd"
  convert "$out/$mode.xwd" "$screen"

  uv run python - "$screen" "$reference" "$mode" <<'PY'
import sys
from PIL import Image

screenshot, reference, mode = sys.argv[1:]
counts = {"cyan": 0, "magenta": 0, "yellow": 0}
image = Image.open(screenshot).convert("RGB")
for red, green, blue in image.getdata():
    if red < 100 and green > 130 and blue > 130:
        counts["cyan"] += 1
    if red > 130 and green < 100 and blue > 130:
        counts["magenta"] += 1
    if red > 130 and green > 130 and blue < 100:
        counts["yellow"] += 1
with Image.open(reference) as src:
    assert src.size[0] > 0 and src.size[1] > 0
print(f"{mode}: screenshot={image.size}, detected colored pixels={counts}")
if min(counts.values()) < 40:
    raise SystemExit(f"{mode}: expected PNG bar colors absent from Kitty capture")
PY
  finish
  trap - EXIT
done

echo "Both native Kitty image-placement screenshots have the reference bar colors."

#!/usr/bin/env bash
# Verify live, event-pumped nonblocking resize with real Kitty raster screenshots.
set -Eeuo pipefail

out="${RUNNER_TEMP:-/tmp}/wskr-phase3-nonblocking"
mkdir -p "$out"
rm -f "$out/"{launch.ready,launch.proceed,initial.ready,resize.proceed,resized.ready,resized.proceed,finished,frames.json}
log="$out/kitty.log"
title="wskr-event-pump-acceptance"

WSKR_FIT=contain WSKR_GUI_LOG_DIR="$out" kitty --config NONE --title "$title" --hold \
  uv run python scripts/phase3_nonblocking_resize_smoke.py --directory "$out" >"$log" 2>&1 &
pid=$!
finish() {
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" || true
    wait "$pid" || true
  fi
}
trap finish EXIT

await_marker() {
  local marker="$1"
  for _ in $(seq 1 180); do
    if [[ -s "$out/$marker" ]]; then return 0; fi
    if ! kill -0 "$pid" 2>/dev/null; then break; fi
    sleep 0.1
  done
  echo "Real Kitty nonblocking stage $marker did not finish:" >&2
  cat "$log" >&2
  if [[ -s "$out/python-error.txt" ]]; then cat "$out/python-error.txt" >&2; fi
  exit 1
}

capture() {
  local name="$1"
  sleep 0.35
  xwd -root -silent -out "$out/$name.xwd"
  convert "$out/$name.xwd" "$out/$name.png"
}

await_marker launch.ready
window=""
for _ in $(seq 1 60); do
  window="$(xdotool search --name "$title" 2>/dev/null | head -n 1 || true)"
  if [[ -n "$window" ]]; then break; fi
  sleep 0.1
done
if [[ -z "$window" ]]; then
  cat "$log" >&2
  echo "Cannot locate the real Kitty X11 window" >&2
  exit 1
fi

# Change actual X11 window dimensions, then let Kitty update TIOCGWINSZ.
xdotool windowsize --sync "$window" 1000 700
sleep 0.4
touch "$out/launch.proceed"
await_marker initial.ready
capture initial

xdotool windowsize --sync "$window" 620 440
capture before_redraw
touch "$out/resize.proceed"
await_marker resized.ready
capture resized
touch "$out/resized.proceed"
await_marker finished
capture exited

uv run python - "$out/initial.png" "$out/before_redraw.png" "$out/resized.png" "$out/exited.png" "$out/frames.json" <<'PY'
import json
import sys
from pathlib import Path
from PIL import Image


def counts(path):
    red = blue = 0
    with Image.open(path) as source:
        for r, g, b in source.convert("RGB").getdata():
            if r > 215 and g < 55 and b < 55:
                red += 1
            if b > 215 and r < 55 and g < 55:
                blue += 1
    return {"red": red, "blue": blue}


initial, before_redraw, resized, exited = (counts(path) for path in sys.argv[1:5])
frames = json.loads(Path(sys.argv[5]).read_text(encoding="utf-8"))
print("Kitty nonblocking visible colors:", initial, before_redraw, resized, exited)
print("Measured fitted PNG frames:", frames)
assert len(frames) == 2, "unstable resize uploaded too many or too few images"
assert frames[1]["viewport"][0] < frames[0]["viewport"][0] - 150, "actual window width did not shrink"
assert frames[1]["raster"][0] < frames[0]["raster"][0] - 80, "redraw used stale PNG dimensions"
for stage, colors in (("initial", initial), ("resized", resized), ("exited", exited)):
    assert min(colors.values()) > 800, f"{stage}: plotted red/blue bars not visible in Kitty"
PY

finish
trap - EXIT
echo "Real Kitty event-pumped nonblocking resize and retained final plot passed."

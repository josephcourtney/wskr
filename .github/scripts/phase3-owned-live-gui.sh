#!/usr/bin/env bash
# Verify the exclusive live viewport stays visible, then restores shell output.
set -Eeuo pipefail

out="${RUNNER_TEMP:-/tmp}/wskr-phase3-owned-live"
mkdir -p "$out"
rm -f "$out/"{launch.ready,launch.proceed,initial.ready,resize.proceed,resized.ready,expand.proceed,expanded.ready,exit.proceed,finished,frames.json}
title="wskr-owned-live-viewport"
log="$out/kitty.log"

WSKR_FIT=contain WSKR_GUI_LOG_DIR="$out" kitty --config NONE --title "$title" --hold \
  uv run python scripts/phase3_owned_live_smoke.py --directory "$out" >"$log" 2>&1 &
pid=$!
finish() {
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" || true
    wait "$pid" || true
  fi
}
trap finish EXIT

await_marker() {
  for _ in $(seq 1 180); do
    if [[ -s "$out/$1" ]]; then return 0; fi
    if ! kill -0 "$pid" 2>/dev/null; then break; fi
    sleep 0.1
  done
  echo "Owned viewport did not reach $1" >&2
  cat "$log" >&2
  if [[ -s "$out/python-error.txt" ]]; then cat "$out/python-error.txt" >&2; fi
  exit 1
}

capture() {
  sleep 0.35
  xwd -root -silent -out "$out/$1.xwd"
  convert "$out/$1.xwd" "$out/$1.png"
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
  exit 1
fi

xdotool windowsize --sync "$window" 1000 700
sleep 0.4
touch "$out/launch.proceed"
await_marker initial.ready
capture initial

xdotool windowsize --sync "$window" 620 440
touch "$out/resize.proceed"
await_marker resized.ready
capture resized

xdotool windowsize --sync "$window" 1000 700
touch "$out/expand.proceed"
await_marker expanded.ready
capture expanded
touch "$out/exit.proceed"
await_marker finished
capture restored

uv run python - "$out" <<'PY'
import json
import sys
from pathlib import Path
from PIL import Image

directory = Path(sys.argv[1])

def colors(stage):
    red = blue = 0
    with Image.open(directory / f"{stage}.png") as source:
        for r, g, b in source.convert("RGB").getdata():
            if r > 215 and g < 55 and b < 55:
                red += 1
            if b > 215 and r < 55 and g < 55:
                blue += 1
    return red, blue

frames = json.loads((directory / "frames.json").read_text(encoding="utf-8"))
counts = {stage: colors(stage) for stage in ("initial", "resized", "expanded", "restored")}
print("Owned viewport transfers:", frames)
print("Owned viewport screenshot colors:", counts)
assert len(frames) == 3, "unexpected redraws"
assert [frame["raster"][0] for frame in frames] == [900, 612, 900], frames
for stage in ("initial", "resized", "expanded"):
    assert min(counts[stage]) > 800, f"{stage}: live plot not visible"
assert max(counts["restored"]) < 800, "owned plot leaked into restored shell history"
PY

finish
trap - EXIT
echo "Real Kitty explicitly owned viewport shrink/expand/restore passed."

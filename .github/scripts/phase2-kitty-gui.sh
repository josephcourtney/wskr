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

# Unlike the two paused scenarios, this script genuinely exits. The ready
# marker is written after Matplotlib's atexit figure-manager cleanup.
ready="$out/phase3-exit.ready"
log="$out/phase3-exit-kitty.log"
screen="$out/phase3-exit-screen.png"
rm -f "$ready"
kitty --config NONE --title "wskr-phase3-exit" --hold \
  uv run python scripts/phase3_exit_smoke.py --ready-file "$ready" >"$log" 2>&1 &
pid=$!
trap finish EXIT
exited=0
for _ in $(seq 1 120); do
  if [[ -f "$ready" ]] && grep -q "python-exited" "$ready"; then
    exited=1
    break
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    break
  fi
  sleep 0.25
done
if [[ "$exited" != 1 ]]; then
  echo "Kitty process did not produce an after-cleanup exit marker:" >&2
  cat "$log" >&2
  exit 1
fi
sleep 0.7
xwd -root -silent -out "$out/phase3-exit.xwd"
convert "$out/phase3-exit.xwd" "$screen"
uv run python - "$screen" <<'PY'
import sys
from PIL import Image

counts = {"cyan": 0, "magenta": 0, "yellow": 0}
with Image.open(sys.argv[1]) as source:
    for red, green, blue in source.convert("RGB").getdata():
        if red < 100 and green > 130 and blue > 130:
            counts["cyan"] += 1
        if red > 130 and green < 100 and blue > 130:
            counts["magenta"] += 1
        if red > 130 and green > 130 and blue < 100:
            counts["yellow"] += 1
print(f"phase3-exit: after-Python-shutdown colors={counts}")
if min(counts.values()) < 40:
    raise SystemExit("Static Kitty output disappeared after Matplotlib shutdown")
PY
finish
trap - EXIT

# A full-resolution user-owned figure (1800x1800) must be fit to the
# *actual* pixel viewport with opt-in WSKR_FIT, not resized in Matplotlib.
ready="$out/phase3-fit.ready"
fit_file="$out/phase3-fit-dimensions.txt"
log="$out/phase3-fit-kitty.log"
rm -f "$ready" "$fit_file"
WSKR_FIT=contain kitty --config NONE --title "wskr-phase3-fit" --hold \
  uv run python scripts/phase3_exit_smoke.py --ready-file "$ready" --fit-file "$fit_file" >"$log" 2>&1 &
pid=$!
trap finish EXIT
seen=0
for _ in $(seq 1 120); do
  if [[ -s "$ready" && -s "$fit_file" ]]; then
    seen=1
    break
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    break
  fi
  sleep 0.25
done
if [[ "$seen" != 1 ]]; then
  echo "Oversized figure not fitted against live Kitty geometry:" >&2
  cat "$log" >&2
  exit 1
fi
echo "phase3-fit real Kitty measured dimensions: $(cat "$fit_file")"
sleep 0.7
xwd -root -silent -out "$out/phase3-fit.xwd"
convert "$out/phase3-fit.xwd" "$out/phase3-fit.png"
uv run python - "$out/phase3-fit.png" <<'PY'
import sys
from PIL import Image

counts = {"cyan": 0, "magenta": 0, "yellow": 0}
with Image.open(sys.argv[1]) as source:
    for red, green, blue in source.convert("RGB").getdata():
        if red < 100 and green > 130 and blue > 130:
            counts["cyan"] += 1
        if red > 130 and green < 100 and blue > 130:
            counts["magenta"] += 1
        if red > 130 and green > 130 and blue < 100:
            counts["yellow"] += 1
print(f"phase3-fit: pixel colors={counts}")
if min(counts.values()) < 40:
    raise SystemExit("Contained Matplotlib bars missing from real Kitty capture")
PY
finish
trap - EXIT

echo "Native placement, persistent output and live-pixel viewport fit passed."

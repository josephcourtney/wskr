#!/usr/bin/env bash
# Capture actual Kitty paging before/after and verify isolated contact-sheet pages.
set -Eeuo pipefail
out="${RUNNER_TEMP:-/tmp}/wskr-phase3-paging"
mkdir -p "$out"
rm -f "$out/page0.ready" "$out/page0.proceed" "$out/page1.ready" "$out/page1.proceed" "$out/closed"
log="$out/kitty.log"
WSKR_FIT=contain kitty --config NONE --title "wskr-paging-acceptance" --hold \
  uv run python scripts/phase3_paging_smoke.py --directory "$out" >"$log" 2>&1 &
pid=$!
finish() {
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" || true
    wait "$pid" || true
  fi
}
trap finish EXIT

capture() {
  local stage="$1"
  for _ in $(seq 1 150); do
    if [[ -s "$out/$stage.ready" || -s "$out/$stage" && "$stage" == "closed" ]]; then break; fi
    if ! kill -0 "$pid" 2>/dev/null; then break; fi
    sleep 0.1
  done
  if [[ ! -s "$out/$stage.ready" && ! -s "$out/$stage" ]]; then
    echo "Kitty paging stage $stage unavailable" >&2
    cat "$log" >&2
    exit 1
  fi
  sleep 0.3
  xwd -root -silent -out "$out/$stage.xwd"
  convert "$out/$stage.xwd" "$out/$stage.png"
  if [[ "$stage" != "closed" ]]; then touch "$out/$stage.proceed"; fi
}
capture page0
capture page1
capture closed

uv run python - "$out/page0.png" "$out/page1.png" "$out/closed.png" <<'PY'
import sys
from PIL import Image


def count_colors(path):
    counts = {"red": 0, "blue": 0, "green": 0}
    with Image.open(path) as image:
        for r, g, b in image.convert("RGB").getdata():
            if r > 210 and g < 50 and b < 50:
                counts["red"] += 1
            if b > 210 and r < 50 and g < 50:
                counts["blue"] += 1
            if 80 < g < 170 and r < 50 and b < 50:
                counts["green"] += 1
    return counts


first, second, closed = map(count_colors, sys.argv[1:])
print("paged Kitty colors: first=", first, "second=", second, "restored=", closed)
assert first["red"] > 2000 and first["blue"] > 2000, "first page lost its panels"
assert first["green"] < 100, "second page leaked onto first"
assert second["green"] > 2000, "single-panel second page missing"
assert second["red"] < 100 and second["blue"] < 100, "first-page graphics leaked onto next"
assert sum(closed.values()) < 100, "paged graphics not removed when the session closed"
PY
finish
trap - EXIT
echo "Native Kitty paged contact-sheet screenshot acceptance passed."

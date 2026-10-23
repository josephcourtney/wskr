#!/usr/bin/env bash
# Demonstrate real Kitty alternate-screen cleanup restores primary text rows.
set -Eeuo pipefail

out="${RUNNER_TEMP:-/tmp}/wskr-phase3-alternate-screen"
mkdir -p "$out"
ready="$out/alternate.ready"
proceed="$out/alternate.proceed"
closed="$out/primary.closed"
log="$out/kitty.log"
rm -f "$ready" "$proceed" "$closed"

kitty --config NONE --title "wskr-alt-screen-acceptance" --hold \
  uv run python scripts/phase3_alternate_screen_smoke.py \
    --ready "$ready" --proceed "$proceed" --closed "$closed" \
  >"$log" 2>&1 &
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
  echo "Kitty never reached the alternate-screen prompt:" >&2
  cat "$log" >&2
  exit 1
fi

sleep 0.3
xwd -root -silent -out "$out/alternate.xwd"
convert "$out/alternate.xwd" "$out/alternate.png"
touch "$proceed"

for _ in $(seq 1 120); do
  if [[ -s "$closed" ]]; then break; fi
  if ! kill -0 "$pid" 2>/dev/null; then break; fi
  sleep 0.1
done
if [[ ! -s "$closed" ]]; then
  echo "Kitty never restored the primary screen:" >&2
  cat "$log" >&2
  exit 1
fi
sleep 0.3
xwd -root -silent -out "$out/primary.xwd"
convert "$out/primary.xwd" "$out/primary.png"

uv run python - "$out/alternate.png" "$out/primary.png" <<'PY'
import sys
from PIL import Image


def sample(path):
    with Image.open(path) as source:
        image = source.convert("RGB")
        result = {kind: [] for kind in ("cyan", "magenta", "yellow", "green", "red")}
        for y in range(image.height):
            for x in range(image.width):
                r, g, b = image.getpixel((x, y))
                if r < 100 and g > 130 and b > 130:
                    result["cyan"].append(y)
                if r > 130 and g < 100 and b > 130:
                    result["magenta"].append(y)
                if r > 130 and g > 130 and b < 100:
                    result["yellow"].append(y)
                if r < 80 and g > 220 and b < 80:
                    result["green"].append(y)
                if r > 220 and g < 80 and b < 80:
                    result["red"].append(y)
        return result


alternate = sample(sys.argv[1])
primary = sample(sys.argv[2])
print("alternate:", {key: len(value) for key, value in alternate.items()})
print("restored primary:", {key: len(value) for key, value in primary.items()})

for kind in ("cyan", "magenta", "yellow"):
    assert len(alternate[kind]) >= 40, f"missing {kind} plot bars in alternate screen"
    assert len(primary[kind]) < 40, f"{kind} plot bars leaked into primary screen"

for kind in ("green", "red"):
    assert len(primary[kind]) >= 40, f"lost {kind} primary-screen text marker"

gap = min(primary["red"]) - min(primary["green"])
print("primary before/after marker row separation:", gap)
assert 0 < gap < 90, "terminal rows were not restored contiguously"
PY

finish
trap - EXIT
echo "Kitty alternate-screen plot and gap-free primary-screen restoration passed."

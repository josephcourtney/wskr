# Native macOS — owned live Kitty viewport acceptance

This tests the separate, explicit foreground-owned `owned_viewport(fig)`
mode introduced by PR #40. Unlike ordinary inline Matplotlib output, this
mode owns Kitty's alternate screen and restores the original terminal screen
when the session exits.

## Procedure

From a fresh Kitty window with `wskr` checked out and `uv sync` complete:

```sh
kitty --version
just owned-native unmanaged 2
just owned-native unmanaged 6
just owned-native yabai 2
just owned-native yabai 6
```

Use a **separate Kitty window for each run**. `unmanaged` means the
window is not controlled by yabai; `yabai` means the window is managed by
yabai and resized using yabai. **The argument is a label only**: the
harness does not configure yabai or verify the current window-manager policy.
Test the actual configuration before claiming success.

The test requires a real macOS Kitty foreground TTY, valid measured cell
and pixel sizes, and `WSKR_FIT=contain`. It checks that attempting to
acquire an owned viewport from a redirected, noninteractive subprocess
fails without emitting terminal graphics escape sequences.

It asks you to select the Kitty window through macOS's interactive
window-only screenshot picker. Grant Screen Recording permission to the
calling terminal process if required. Window-size instructions are shown
in separate macOS dialogs, avoiding writes to Kitty while the alternate
screen is active.

## Stages

1. **primary_before:** original main terminal screen.
2. **initial:** an owned viewport showing red and blue bars in a wide
   Kitty window (at least 950 physical pixels wide and 650 tall).
3. **resized:** window under 790 physical pixels wide, with at least
   320 pixels height (500 for the taller 9×6 figure).
4. **expanded:** after expansion beyond 950 physical pixels wide.
5. **primary_restored:** after leaving the owned viewport and restoring
   the original terminal screen.

The harness records per-stage terminal geometry, PNG upload dimensions,
visible red/blue pixel counts, version strings, and failed assertions.
It verifies exactly three uploads, raster shrink/expand, viewport
containment and unchanged original Figure size/DPI. It also compares
the restored screen's red/blue pixel coverage against the original
primary screen to detect residual plot graphics.

Near-black screenshot-picker artifacts are retried up to three times and
retained as rejected PNGs. The final run writes `report.json`, any
`error.txt`, and an evidence ZIP under
`artifacts/phase3-owned-live-native/`.

## Acceptance and limitations

Review every screenshot manually: pixel-count checks cannot establish
correct z-order, clipping, plot position, full shell restoration or
absence of overlapping foreign content. The terminal's current
fullscreen presentation may affect interactive screenshot selection.

An automated pass is not full native acceptance without human review,
and `mode=yabai` alone does not establish that yabai managed the window.
A run on hosted Linux Kitty/Xvfb does not replace native macOS testing.

This harness deliberately **does not modify** the wskr runtime and does
not change ordinary history-relative nonblocking placement. Historical
scrollback behavior remains tracked in issue #31; owned live viewport
native qualification is tracked in issue #41.

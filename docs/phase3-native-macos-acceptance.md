# Phase 3 — Native macOS Kitty resize acceptance

This is the **local GUI qualification** missing from hosted Linux Kitty/Xvfb
coverage. It is separate from portable PTY/unit tests and from wheel packaging.

## Run

Use a **fresh Kitty terminal window**, with minimal scrollback. From the
`wskr` checkout (after `git pull --ff-only && uv sync`):

```sh
kitty --version
just native-resize unmanaged 2
just native-resize unmanaged 6
just native-resize yabai 2
just native-resize yabai 6
```

Run each case in a freshly opened window. For `unmanaged`, disable yabai
management of that Kitty window; for `yabai`, use an actively managed Kitty
window and resize it via yabai. **The mode argument labels evidence; it does
not toggle or attest the current yabai configuration.** Test with Kitty 0.31+
for parent-relative image placement.

Each run launches a real Matplotlib backend in a **separate Python process**,
enforcing `WSKR_FIT=contain`. It will not display the source code in terminal
scrollback and it never changes Matplotlib `figsize`/`dpi`.

The harness prompts for a window **at least 950 physical pixels wide and
650 pixels tall** initially. It then asks you to shrink below **790 physical
pixels wide**, keeping at least **320 pixels tall**, and finally expand above
950 pixels wide. It prints the **actual TIOCGWINSZ width/height**; macOS
Retina pixel counts are not equivalent to window-manager logical point sizes.

Once the plot is displayed, resize instructions appear in native macOS dialogs (via `osascript`) rather than being printed into Kitty. The harness intentionally avoids new terminal text during resize, because writing multi-line prompts into a small viewport can scroll the original image anchor out of view and confound the test. Click **Continue** in each dialog after resizing.

At each stage, the system's `screencapture -i -w` picker asks you to click
**the Kitty window**. Only that selected window is saved (not the entire
desktop). If macOS denies screenshot access, grant Screen Recording
permission to the calling application, restart as required, and rerun.

The five stored screenshots are:

1. `initial.png`: image displayed before resizing.
2. `before_redraw.png`: resized window, original image still anchored,
   before an event-pumped replacement; clipping here is diagnostic.
3. `resized.png`: after the debounced fitted PNG redraw in the smaller
   window.
4. `expanded.png`: after redraw following expansion.
5. `after_python_exit.png`: the **separate plotting Python interpreter**
   has exited, and the parent harness captures the retained image.

If a post-redraw screenshot has no visible plot, the harness **records the visual failure and continues** through expansion and plotting-process exit rather than terminating immediately. The final result still fails visual acceptance, and the archive contains all stages. This distinguishes a temporarily off-viewport anchor from permanent image loss. A blank or black screenshot-picker capture should not be treated as definitive evidence without reviewing the image.

The harness also stores `report.json` with original figure dimensions,
measured geometries, transmitted PNG dimensions, pixel counts for red/blue
bars, and per-stage screenshot paths. A passing automated check requires
an actual PNG shrink and expansion, three transfers, no `figsize`/`dpi`
mutation, a contained raster and visible red/blue pixels at initial,
post-redraw, expanded and post-child-exit stages. The checkpoint
`before_redraw` is evidence-only: resizing can clip an old placement.

Artifacts are stored in `artifacts/phase3-native-resize/<timestamp>-<mode>-h<height>/`.
Screenshots may contain terminal text or other personal information within
the Kitty window; inspect them before sharing. **Automated pixel checks are
not a substitute for reviewing position, cropping, text overlap, scrollback
and shell-prompt behavior**; complete the issue's acceptance only after
manual screenshot review.

If a run fails, send the `report.json`, any `error.txt`, and screenshots
from the evidence directory along with `kitty --version`. Do not classify
a test conducted with too little width change as a wskr defect: this
harness explicitly requires narrowing the viewport below the source
figure's 900-pixel width.

## Observed native regression (October 24, 2026)

The first user-run **unmanaged** Kitty 0.49.2 test on macOS 27.0.1 reached a measured **672×486 px** viewport from **1638×1836 px** and transmitted a correctly contained **672×149** replacement PNG (initial **900×200**), but **both bars were absent** in the resized Kitty screenshot. The initial screenshot contained 42,183 red and 55,917 blue pixels; resized contained zero of either. The pre-redraw screenshot was black, so it does not reliably establish the instant at which the plot left view.

The original anchor may have moved into scrollback as the terminal row count fell from 68 to 18, with relative placements following their parent. This remains a **hypothesis**, not an established root cause. Real Kitty/Xvfb Linux acceptance had passed and remains distinct from this native Mac failure. [Tracking issue #31](https://github.com/josephcourtney/wskr/issues/31).

Do not claim native macOS visual acceptance until resolved and rerun. For diagnostic reruns, preserve the expanded and post-exit stages even if the resized image disappears. The revised harness continues through both states after recording an earlier visual failure; it reports failure after collecting the complete archive.

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

For the **clean-history diagnostic only**, launch a new disposable Kitty window and use:

```sh
just native-resize-clean unmanaged 2
```

**Warning:** This opt-in command erases the test window's visible text and
scrollback immediately before the figure is displayed. Do not run it in a
window whose history you want to retain. The normal `native-resize` command
does **not** clear history. Compare a clean run with a normal run to determine
whether existing terminal content and reflow affect placement.

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

## Follow-up native macOS evidence, October 24, 2026

The second unmanaged 9×2 run on Kitty 0.49.2, macOS 27.0.1, using PR #36's
external prompts and persistent evidence collection, measured:

| Stage | Viewport | Fitted raster | Red/blue chart pixels |
| --- | --- | --- | --- |
| Initial | 1638×1863, 117×69 cells | 900×200 | 42,183 / 55,917 |
| Before redraw, after shrink | 686×432, 49×16 cells | original image | 0 / 0 |
| After redraw | 686×432, 49×16 cells | **686×152** | **0 / 0** |
| After expansion | 1316×945, 94×35 cells | 900×200 | 0 / 0, but captured image was almost entirely black |
| After child Python exits | 1316×945, 94×35 cells | retained 900×200 | **42,183 / 55,917** |

The image was not visible in the valid resized screenshot even though its
correctly fitted bytes were sent; it **reappeared** after the plotting
interpreter exited. This does not establish why visibility changed.
The expanded-stage capture is invalid as evidence because 97.4% of the
screenshot pixels were near-black, consistent with an incorrect window
capture/picker overlay. The revised harness rejects/retries near-black
screenshots and preserves invalid attempts with `.invalid-*.png` names.

The **clean-scrollback** mode deliberately isolates reflow of pre-existing
terminal text. It is only a diagnostic, not a claim that ordinary
scrollback-rich REPL use is fixed. Do not close issue #31 based on a clean-only
pass; separately qualify normal-history usage or explicitly document its
scrollback semantics.

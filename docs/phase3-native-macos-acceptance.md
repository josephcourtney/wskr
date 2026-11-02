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

The P3 owner-only theme refresh and multi-manager event-pump changes are
portable/hosted-validated separately; a passing owned-viewport test does not
prove history-anchored image visibility or shell prompt safety. For Kitty
versions without relative P/Q placement, use `WSKR_KITTY_PARENT=off`
and report the fallback as a distinct mode.

For controlled history-dependent placement testing, see
[the Phase 3 placement contract and A/B protocol](phase3-placement-semantics.md).
The matching experiments use separate disposable windows:

```sh
just native-resize-clean unmanaged 2
just native-resize-history unmanaged 2 96
```

Both erase the test window's screen/scrollback; the second then adds 96
deterministic long history lines before displaying the plot. This isolates
history/reflow more systematically than comparing arbitrary shell scrollback.
The history experiment may legitimately record missing visible pixels without
losing image data: inspect the entire evidence package and distinguish the
history-position contract from a viewport-pinning requirement.

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

## Native yabai seeded-history result — November 1, 2026

A user-run **yabai-managed** Kitty 0.49.2 test on macOS 27.0.1, with 96 seeded
112-column lines and a 9×2 figure, reported `passed_protocol_checks: true`
and `visual_failures: []`. The five actual screenshots were reviewed.
Those automated flags are **not sufficient for visual acceptance**.

| Stage | Measured terminal (pixels, cells) | PNG (pixels) | Observation |
| --- | --- | --- | --- |
| Initial | 2282×1890, 163×70 | 900×200 | Bars visible below line 0095 |
| Before redraw | 616×1890, 44×70 | Original PNG | Horizontally clipped; bars partly visible |
| Resized | 616×1890, 44×70 | 616×137 | **Both bars visible, but plot overlays wrapped history around line 0094; line 0095 appears below the image** |
| Expanded | 2394×1890, 171×70 | 900×200 | Figure visible again below seeded history |
| After child exit | 2394×1890, 171×70 | Retained final PNG | Figure remains visible |

The viewport narrowed horizontally without losing rows. This distinguishes the
new **history overlap** failure from the earlier narrow-and-short offscreen
visibility failure. In particular, the resized screenshot contains 19,537 red
and 26,208 blue chart pixels, so checking only colored-pixel presence produces
a false acceptance. The figure overlay should not be called prompt-safe.

The follow-up harness adds a conservative text-after-plot detector to fail
this known seeded-history case; negative detection still requires manual
screenshot review. Do not infer a specific Kitty internal implementation
fault from these screenshots alone. See [issue #31](https://github.com/josephcourtney/wskr/issues/31).

## Controlled native yabai A/B — November 1, 2026 (second comparison)

The user repeated both cases after [PR #47](https://github.com/josephcourtney/wskr/pull/47)
merged. Both ran with Kitty 0.49.2 and macOS 27.0.1 in yabai-managed
windows, with 70 terminal rows at every stage. Each run began with cleared
screen and scrollback and used a 9×2-inch figure.

| Stage | 0 seeded history lines | 96 seeded history lines |
| --- | --- | --- |
| Initial | 171 columns, 2394×1890 px; 900×200 plot visible | 149 columns, 2086×1890 px; 900×200 plot visible |
| Before redraw | 39 columns, 546×1890 px; old image clipped | 40 columns, 560×1890 px; old image clipped |
| Resized | 546×121 plot visible with no overlapping text | **560×124 plot visible but overlaps reflowed history; line 0095 appears below** |
| Expanded | 149 columns; 900×200 plot visible | 161 columns; 900×200 plot visible |
| After Python exit | 900×200 plot persists | 900×200 plot persists |

The 0-history run reports zero visual failures and passes. The 96-history
run records `history_after_plot: true` with one visual failure and exits 1.
**This nonzero exit is the intended acceptance result**, not a Python crash.
The evidence proves a difference involving preceding history even when
the number of terminal rows is constant. The initial and expanded widths
were not exactly equal between conditions; do not represent this as
pixel-identical A/B geometry. This is evidence about ordering and placement,
not a demonstration that Kitty violated its protocol.

The first test had two invalid nearly black screenshot-picker attempts for
`before_redraw`, retried automatically. The five selected valid screenshots
show the expected clean behavior.

## Experimental Unicode parent — native signoff not yet obtained

Kitty's protocol allows a one-cell transparent **virtual placement** with an
encoded Unicode placeholder. The glyph follows terminal text when it reflows;
a real child image can then use `P/Q` to follow that placeholder instead of
an original physical parent.

The opt-in `WSKR_KITTY_ANCHOR=unicode` experiment changes **only the first
anchor**. It prints one transparent placeholder plus enough newlines to
reserve the initial plot's vertical footprint. Later redraws still replace
the child at the original parent and do not read input or reposition the
shell cursor. The default remains `physical` and `WSKR_KITTY_PARENT=off`
still bypasses relative positioning entirely.

Test this in a **new disposable Kitty window** and compare against the
known failing 96-history physical case:

```sh
WSKR_KITTY_ANCHOR=unicode just native-resize-history yabai 2 96
```

If successful, repeat with no history and with 9×6, verifying redraw,
scrollback ordering, shell prompt safety, after-process persistence and
explicit-close cleanup. This is an experiment, **not a certified fix**.

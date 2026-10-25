# Phase 3 — Terminal image placement contracts

## Distinguish position, size, and visibility

Kitty graphics placements are part of terminal text history. Its protocol
requires images to scroll with text, and a relative placement (`P/Q`) follows
its parent image placement. A successful graphics transfer does not establish
that the placement is visible in the current viewport.

Protocol reference: <https://sw.kovidgoyal.net/kitty/graphics-protocol/>
(see **Relative placements** and **Interaction with other terminal actions**).

Three properties must be evaluated independently:

1. **Raster containment:** a fitted PNG is no larger than the measured
   terminal pixel geometry at transmission time. This is provided by
   `WSKR_FIT=contain` and independently tested.
2. **Placement identity/lifetime:** old child images are released, the latest
   child follows its original transparent parent, explicit close cleans
   scoped resources, and noninteractive process exit retains the final parent
   and child. This is the current nonblocking Kitty transport contract.
3. **Viewport visibility:** a screenshot of the *current visible screen*
   contains the plot. This is **not guaranteed by history-relative
   placement**, even if the upload and placement identity are correct.

## Current behaviors

| Operation | Position ownership | Visibility guarantee | Persistence |
| --- | --- | --- | --- |
| Ordinary nonblocking `show(block=False)` | Terminal history, relative to original physical parent | Not pinned to viewport; may leave view when history is scrolled or reflowed | Noninteractive final plot retained after process exit |
| `canvas.flush_events()` or `plt.pause()` | Same parent as previous nonblocking display | Debounced retransmission only; does **not** relocate an offscreen anchor | Same as nonblocking display |
| Fitted `show(block=True)` | Foreground-owned alternate-screen session, with explicit cursor/layout management | Repaints within managed viewport on measured resize, subject to Kitty/geometry acceptance | Session closes and main screen is restored |

**Not implemented:** nonblocking **viewport-pinned** placement with ongoing
independent repositioning. It would require a deliberate owner of a live
display area or terminal/shell integration, and a policy for coordinating
cursor/scrollback state. Silently emitting arbitrary cursor movements from
a nonblocking backend is not acceptable: it could overwrite another
application's prompt or unrelated output. Do not claim that a history
placement that has moved out of view has become a viewport-following plot.

## Native macOS evidence and hypotheses

- Linux Kitty/Xvfb visual qualification passes ordinary nonblocking fitted
  shrink/expand with 9×2 and 9×6 figures.
- macOS Kitty 0.49.2 ordinary-history 9×2: fitting succeeds but the image is
  absent from the shrunk viewport; post-exit screenshot shows it again.
- macOS Kitty 0.49.2 **cleaned scrollback** 9×2: the image remains visible
  after shrink, expansion, and interpreter exit.
- A controlled native 9×2 comparison using the same Kitty environment,
  cleared initial scrollback, and either 0 or 96 deterministic 112-column
  history lines now **reproduces history-dependent visibility**: the clean
  figure stays visible during fitting, while the seeded-history figure leaves
  the narrow viewport and returns when the window expands. This does not
  establish a Kitty implementation bug or the exact internal location of
  the anchor.

Issue: <https://github.com/josephcourtney/wskr/issues/31>.

## Controlled history A/B experiment

Run each condition in a separate **disposable** Kitty window on the same
machine, with the same initial/target pixel geometry, Kitty version,
font size, yabai policy and source figure:

```sh
just native-resize-clean unmanaged 2
just native-resize-history unmanaged 2 96
```

Both conditions first erase the test window's screen and scrollback.
The history condition then prints **96 deterministic 112-column text lines
before constructing the figure**. Those lines fit the initial wide viewport
but will wrap into additional terminal rows at the narrow size. Neither
condition prints extra terminal prompts after the plot appears.

The history experiment is opt-in and destructive *only in the test window*.
`--history-lines` requires `--clean-scrollback`, and the count is bounded
to 200. The evidence report records `history_lines` and the fixture's
logical line width so results remain comparable.

For each condition, collect the initial, after-shrink/before-redraw,
after-redraw, after-expansion, and after-child-exit selected-window
screenshots plus `report.json`. A screenshot-picker overlay that is
predominantly black is **invalid evidence** and must be retried.
The raster should shrink/expand in both cases; independently record whether
each stage is visible. Do not infer a change in parent placement from
a zero color count alone.

If seeded history makes the plot leave the viewport whereas the zero-history
control does not, the experiment establishes a **reproducible
history-dependent visibility limitation**, not a loss of image data.
If both pass, the earlier ordinary-history reproduction requires another
controlled variable (for example, interactive shell output or window
scroll position). A clean-only passing run is not sufficient to close issue
#31 or claim general REPL viewport behavior.

For future native acceptance, repeat the 9×6 figure and yabai-managed
windows. The historical-output contract and a potential future
viewport-pinned live-display mode should have **separate acceptance gates**.

## Controlled native result — October 25, 2026 UTC

Two unmanaged 9×2-inch macOS Kitty 0.49.2 runs, using `just native-resize-clean unmanaged 2` (0 seeded lines) versus `just native-resize-history unmanaged 2 96`, both cleared the terminal history initially. They use slightly different but comparable terminal dimensions.

| Stage | 0 history lines | 96 history lines |
| --- | --- | --- |
| Initial | 2520×1377 viewport; visible 900×200 PNG | 2142×1350 viewport; visible 900×200 PNG |
| Before redraw | 574×351; plot still visible, partly clipped | 588×324; final history text visible, plot absent |
| After fitted redraw | 574×128 PNG, **plot visible** | 588×131 PNG, **plot absent** |
| After expansion | 2142×1350; 900×200 visible | 1890×1296; 900×200 visible again |
| After Python exit | Final image retained and visible | Final image retained and visible |

For the clean run, red/blue bar pixels in the resized screenshot were
**16,767 / 22,671**; the 96-line run had **0 / 0** despite the correct raster
upload. Its resized screenshot clearly shows `WSKR_HISTORY_0093` through
`0095`, establishing that this is not a blank screenshot-picker capture.
In the initial seeded-history screenshot the plot sits near the viewport's
bottom (red/blue pixel y≈1161–1331), compared with near the top (y≈28–198)
in the clean run. After expansion it reappears near the bottom.

The comparison demonstrates **history-dependent viewport visibility**. It
does not measure Kitty's internal scrollback anchor position, distinguish
all possible terminal reflow mechanisms, or establish that relative
placement semantics are violated. Preserve the distinction between a
history-resident figure and an intentionally viewport-pinned live figure.
The latter is not currently implemented, and should require a separate
explicit ownership and acceptance contract.

Source evidence archives: `20261025T030202Z-unmanaged-h2-clean.zip` and
`20261025T030304Z-unmanaged-h2-clean-history96.zip`, supplied during
native acceptance review. See [issue #31](https://github.com/josephcourtney/wskr/issues/31).

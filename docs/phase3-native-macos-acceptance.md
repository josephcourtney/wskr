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

## Unicode-placeholder parent native result — November 1, 2026

The opt-in `WSKR_KITTY_ANCHOR=unicode` experiment from
[PR #48](https://github.com/josephcourtney/wskr/pull/48) passed its **first**
native history-reflow visual test. Full user-supplied evidence:
`20261102T002247Z-yabai-h2-clean-history96.zip` (not committed because
window screenshots may contain private terminal content).

Environment: macOS 27.0.1, Kitty 0.49.2 (verified separately; the report's
`kitty_version` field was `unknown`), yabai-managed window, a 9×2-inch
Matplotlib figure, 96 seeded history lines of 112 characters, 70 terminal
rows at every stage.

| Stage | Measured terminal geometry | Transmitted PNG | Native visual observation |
| --- | --- | --- | --- |
| Initial | 161×70 cells; 2254×1890 px | 900×200 | Visible below seeded history |
| Before redraw | 49×70 cells; 686×1890 px | Previous 900×200 | Horizontally clipped, as expected |
| Resized | 49×70 cells; 686×1890 px | 686×152 | **Pass:** history line 0095 is entirely above the chart; no overlap |
| Expanded | 168×70 cells; 2352×1890 px | 900×200 | Visible below history |
| After Python exit | 168×70 cells; 2352×1890 px | Retained 900×200 | Visible and correctly ordered |

The resized PNG has 24,056 red and 31,993 blue pixels in the screenshot.
The harness reported `visual_failures: []` and
`passed_protocol_checks: true`. All five valid screenshots were reviewed
individually; the single `before_redraw.invalid-1.png` picker capture was
correctly excluded. The Unicode anchor avoids the text overlap reproduced
with the physical parent in the preceding 96-line yabai run. Its result is
**not** evidence of independent viewport pinning, nor confirmation that all
shell prompt behaviors are safe.

**Qualification scope:** Native 9×2 / yabai / 96-history case only.
The Unicode mode remains **explicitly opt-in** pending native 9×6,
unmanaged, clean-history control, interactive shell/prompt, and
multi-figure/explicit-close signoff. Keep issue #31 open.

## Unicode-placeholder parent native 9x6 result — November 1, 2026

A second user-run opt-in `WSKR_KITTY_ANCHOR=unicode` native test passed
**9x6-inch fitting with 96 seeded 112-character history lines** using a
yabai-managed Kitty 0.49.2 window on macOS 27.0.1. Source evidence:
`20261102T003900Z-yabai-h6-clean-history96.zip`; window screenshots were
reviewed, but are not committed.

| Stage | Measured viewport | PNG raster | Review |
| --- | --- | --- | --- |
| Initial | 79x69 cells; 1106x1863 px | 900x600 | Plot below history |
| Before redraw | 40x69 cells; 560x1863 px | Previous PNG | Old image horizontally clipped |
| Resized | 40x69 cells; 560x1863 px | 560x373 | **Pass:** complete line 0095 above chart, no overlap |
| Expanded | 85x69 cells; 1190x1863 px | 900x600 | Correct plot order restored |
| After plotting Python exit | 85x69 cells; 1190x1863 px | Retained 900x600 | Plot remains visible |

At the narrow size the screenshot contained 48,280 red and 64,757 blue
pixels; `visual_failures: []` and `passed_protocol_checks: true`. The
two almost-black `before_redraw.invalid-*.png` picker captures were
excluded from the valid five-stage evidence. The 112-character fixture already
wraps at the initial width of 79 columns; shrinking to 40 columns introduces
further reflow. This is a **native visual pass for one 9x6/yabai/history case**,
in addition to the preceding 9x2 native pass, not general shell or viewport
acceptance.

The title and some axis text are visibly low-contrast against the dark Kitty
background. That is a separate appearance issue and not a graphics-placement
acceptance failure. The fifth screenshot is taken after the plotting child
exits but before the outer harness has returned to the user's shell; it
does **not** establish that the restored shell prompt is positioned safely.

Still pending for issue #31: native Unicode zero-history controls, unmanaged
window tests, actual shell prompt position after the harness returns, explicit
figure close and multi-figure behavior. The physical-parent default and
nonblocking history-versus-viewport contract remain unchanged.

## Unicode-placeholder parent, unmanaged-labelled native 9x6 — November 1, 2026

The opt-in Unicode anchor also passed a **9x6 / 96-history native Kitty run
labelled `unmanaged`** on macOS 27.0.1. Evidence:
`20261102T010556Z-unmanaged-h6-clean-history96.zip`.
The harness labels the requested mode, but does not independently verify
whether yabai has actually relinquished management of this window. All five
valid screenshots were inspected, excluding two invalid nearly black
`before_redraw.invalid-*.png` picker captures.

| Stage | Measured viewport | PNG raster | Visual observation |
| --- | --- | --- | --- |
| Initial | 168x70 cells; 2352x1890 px | 900x600 | Chart below history |
| Before redraw | 40x70 cells; 560x1890 px | Previous image | Expected horizontal clipping |
| Resized | 40x70 cells; 560x1890 px | 560x373 | **Pass:** line 0095 and wrapped text remain entirely above the image |
| Expanded | 111x70 cells; 1554x1890 px | 900x600 | Chart correctly positioned below history |
| After plotting child exits | 111x70 cells; 1554x1890 px | Retained 900x600 | Chart persists; cursor below image |

The resized screenshot shows 48,280 red and 64,757 blue bar pixels, and the
harness reports `visual_failures: []` and
`passed_protocol_checks: true`. This is additional evidence that
the Unicode-placeholder parent tolerates history wrapping at the same narrow
40-column size as the previous yabai 9x6 pass.

**Do not infer post-harness shell-prompt safety from `after_python_exit`.**
The harness takes its fifth screenshot after its plotting child exits but
before the outer harness prints its own results and returns to the user's
shell. A separate screenshot of the actual prompt remains necessary.
The title and axis labels also remain low-contrast on the dark background;
that appearance issue is independent of this placement result.

Unicode anchoring remains opt-in, and issue #31 remains open for zero-history
controls, independent management-mode verification as needed, complete
shell-prompt acceptance, explicit-close cleanup, and multi-figure behavior.

## Unicode-anchor native 9x2 — post-harness prompt evidence, November 1, 2026

The user supplied a **separate screenshot after the outer harness returned to
an interactive zsh shell** for the opt-in Unicode 9x2 / 96-line run labelled
`unmanaged`. The output identifies the archive as
`20261102T011410Z-unmanaged-h2-clean-history96.zip` and prints
`PROTOCOL + SCREENSHOT PIXEL CHECKS PASSED`. The archive and report from
this particular run have **not** been supplied for inspection; this is
not independent review of all five intermediate resize stages.

Visual inspection of the post-harness screenshot establishes that history
line `WSKR_HISTORY_0095` precedes the retained bar plot, the harness
prints its result and archive path below the plot, and the actual interactive
zsh prompt and input cursor appear below the harness output. There is no
visible plot/history, plot/output or plot/prompt overlap. **Post-outer-harness
shell-prompt placement passes in this one configuration**, rather than
merely asserting persistence after the plotting child exits.

The image does not independently establish whether the window was excluded
from yabai management (the harness `mode=unmanaged` argument is descriptive),
nor qualify the 9x2 resized-stage screenshots absent their ZIP.
Zero-history Unicode controls, explicit-close behavior, multi-figure
redraw, and REPL integration remain open. Do not declare general viewport
pinning or change the default anchor based on this result.

## Native multi-figure lifecycle and explicit-close acceptance

The separate opt-in `just native-lifecycle unmanaged` command tests
Matplotlib's nonblocking multi-figure ownership and cleanup. It is **not** a
resize test. Run it in a fresh **disposable** Kitty window: it deliberately
clears that window's visible screen and saved scrollback.

```sh
git switch main && git pull --ff-only && uv sync
just native-lifecycle unmanaged
```

The recipe selects the experimental `WSKR_KITTY_ANCHOR=unicode`, enables
`WSKR_IDLE_REDRAW=coalesce` and fits images into measured viewport geometry.
To compare the alternative parent mode, run the **module** from the
repository root with the same environment but `WSKR_KITTY_ANCHOR=physical`:

```sh
WSKR_FIT=contain WSKR_IDLE_REDRAW=coalesce WSKR_KITTY_ANCHOR=physical \
  MPLBACKEND=wskr_kitty uv run python -m scripts.phase3_native_macos_lifecycle --mode unmanaged
```

Save that evidence separately. Do not run simultaneous native GUI screenshot harnesses.

The harness uses two independent red/blue figures and produces five
Kitty-window screenshots, selected through the macOS window picker:

1. `initial`: both figures visible after `plt.show(block=False)`.
2. `pumped`: each figure has a changed bar height; a **single**
   `red_fig.canvas.flush_events()` updates both queued canvases.
3. `after_red_close`: `plt.close(red_fig)` deletes only red's placement;
   blue must remain visible.
4. `after_blue_close`: `plt.close(blue_fig)` deletes blue's placement;
   neither bar should remain visible.
5. `after_child_exit`: neither figure reappears when the plotting Python
   process exits.

The JSON evidence records PNG transmission counts by figure (1 each after
initial show; 2 each after one pump), pixel containment, source figure
dimensions, bounded manager image ownership and stage-specific red/blue
pixel counts. Resource counts must be 2+2, 2+2, 0+2, then 0+0. A mismatch
fails protocol acceptance. Color failures are recorded without dropping
remaining screenshots. The outer command ZIPs the results under
`artifacts/phase3-native-lifecycle/`.

The test still requires inspection for overlapping images, correct prompt
placement, text readability, retained blank cells after image deletion,
and unintended screen clearing. Its `mode` argument merely labels
the intended yabai configuration and does not establish it.

Upload the evidence ZIP, including failed runs. A screenshot of the actual
shell prompt **after the outer command returns** separately qualifies
shell prompt behavior; the harness's `after_child_exit` stage cannot do so.
Do not claim full native multi-figure or close acceptance from the portable
tests or the availability of this script alone.

## Native two-figure lifecycle result — November 1, 2026

A user-run `just native-lifecycle unmanaged` test passed on macOS 27.0.1
with `WSKR_KITTY_ANCHOR=unicode` and `WSKR_IDLE_REDRAW=coalesce`.
Evidence: `20261102T020928Z-unmanaged-unicode.zip`, containing the five
screen captures and JSON report; private window captures are not committed.
The harness-reported mode is `unmanaged` but does not itself attest the
window manager's configuration. Previously checked Kitty version 0.49.2;
`kitty_version` in this report is `unknown`.

All screenshots show the same terminal geometry: 118×34 cells,
1652×918 measured terminal pixels. Each figure transmitted 500×200 PNGs.

| Stage | Native screenshot observation | Managed images (red / blue) |
| --- | --- | --- |
| `initial` | Two distinct vertically stacked figures: red bar height 3, blue height 4 | 2 / 2 |
| `pumped` | Both figures updated after one event pump: red height 4, blue height 2 | 2 / 2 |
| `after_red_close` | Only red removed; blue stays at its original location | 0 / 2 |
| `after_blue_close` | Neither figure visible | 0 / 0 |
| `after_child_exit` | Neither figure reappears | 0 / 0 |

The single pump caused exactly one additional upload per figure: final
`uploads = {"red": 2, "blue": 2}`. The resized geometry is unchanged;
this is a **lifecycle test, not a terminal-resize test**. There is no
figure/figure overlap in the native captures. The report records
`visual_failures: []` and `passed_protocol_checks: true`, which
agrees with visual inspection.

**Native acceptance granted for this specific multi-figure update and
explicit-close sequence.** Graphics-resource deletion leaves the
historical terminal rows in place; `plt.close` does not retract those
rows, even though no image pixels persist. This behavior is consistent
with nonblocking scrollback rather than a missing image cleanup.

The plot titles and some labels are low contrast against the dark terminal
background, a separate style issue. This experiment did not capture the
actual shell prompt *after the outer harness returns*, independently verify
unmanaged yabai mode, test blocking multi-page navigation, or establish
unattended REPL/IPython event scheduling. Those acceptance gates remain open.

## Native blocking multi-figure paging — opt-in acceptance, pending real GUI

The native macOS paging harness checks what the existing foreground PTY tests
cannot see: actual Kitty contact-sheet content, navigated page identity,
changes in page capacity on window resize, and primary-screen restoration
after the terminal's **alternate screen** exits.

In a fresh **disposable** Kitty window, run:

```sh
git pull --ff-only
uv sync
just native-paging unmanaged
```

**This erases the test window's visible screen and scrollback.** The mode
argument labels the intended yabai configuration but does not configure or
independently verify it. A new native window and deliberate window sizing are
required. macOS Screen Recording permission may be needed to capture the
selected Kitty window.

The outer process uses native `osascript` instructions and screenshots; the
plotting child alone reads actual `n`, `p` and blank-Enter lines from the
foreground Kitty terminal. The parent receives only one-byte render/restore
signals through a separate pipe. No input is injected and the shell's TTY
is not read by the coordinator.

The test accepts **any ordinary Kitty window at least 400×240 terminal pixels**,
with no upper height limit or exact cell-based pixel target. It measures the
actual window and generates enough distinctly colored, numbered figures to
guarantee at least two pages, including on tall external monitors. After each screenshot and native instruction,
focus the Kitty window and type the requested command, ending with Enter:

1. Capture `primary_before` with a text sentinel on the normal screen.
2. Capture `initial_page` (first contact-sheet page).
3. Type `n` and Enter, capturing `next_page`.
4. Type `p` and Enter, capturing `previous_page`.
5. Make the Kitty window **at least 15% narrower than its starting width**.
   The height may remain unchanged. Capture `resized_page` after the fitted
   redraw. If the actual geometry crosses the landscape threshold, this also
   changes two-column layout to one column; otherwise the report records
   that page capacity did not change.
6. Type `n` and Enter again, capturing `next_page_small`.
7. Expand to approximately the original width (at least 85% of the initial
   measured width) and capture `expanded_page`.
8. On a **blank input line**, press Enter to quit paging and capture
   `restored_primary`.

The dynamically generated color tiles identify pages; expected indices are computed
from actual `Geometry` and `plan_sheet_pages`. The report separately records
`page_capacity_changed` so a resize that does not cross the column/row
capacity threshold cannot be misrepresented as changing page capacity. Each contact-sheet PNG is
recorded with its measured dimensions and SHA-256 digest. The report checks
color presence and absence in captured screenshots; it also rejects any
contact-sheet tile remaining on the primary screen and checks that the
source figures' explicit size/DPI were preserved. Screenshots and reports
are bundled into one ZIP in `artifacts/phase3-native-paging/`, even on a
recoverable failure.

**Inspect the eight actual screenshots** for page order, clipping, prompt
placement, restore behavior, and unwanted blank text rows. A passing PNG
upload or color counter does not itself establish native visual acceptance.
The final screenshot occurs after the plotting worker restored the primary
screen but before the outer command returns to the shell; capture the actual
returned prompt separately if that behavior must be qualified.

This test is distinct from nonblocking Unicode history placement, and
it does not modify its default. The existing portable PTY test already checks
real canonical paging commands and balanced alternate-screen escape sequences;
native visual signoff remains pending until the evidence is reviewed.

## Native blocking paging startup failure — November 1, 2026

User-provided run `20261102T025857Z-unmanaged.zip` exited before the
first contact-sheet render. The parent successfully measured the native Kitty
window at **160 columns × 18 rows, 2240 × 486 terminal pixels** and captured
`primary_before.png`. That confirms the relaxed window-geometry gate worked.

The child was launched with `--worker`, `--event-fd`, `--directory`
and `--figure-count`, but omitted the parser-required `--mode` option.
Its argument parser terminated with exit code 2, and the parent recorded
`Plotting child closed before expected new page PNG` in `error.txt`.
No paging frames were generated, so the archive is **not** evidence of
native paging, resize, or restoration success or failure.

The fix passes the parent's mode through to the child and tests that
the constructed subprocess arguments actually satisfy the production
argument parser for both `unmanaged` and `yabai`. Repeat
`just native-paging unmanaged` in a fresh disposable Kitty window;
full native screenshot acceptance remains pending.

## Native blocking paging — first complete visual sequence, November 1, 2026

User evidence: `20261102T030748Z-unmanaged.zip` on macOS 27.0.1
in a Kitty window labelled unmanaged (the harness does not independently
verify yabai state). The eight genuine Kitty-window screenshots and
`report.json`/`worker.json` were inspected. **The navigation, fitted resize,
and alternate-screen restoration are visually correct in this run.**

| Stage | Terminal pixels and cells | Transmitted raster | Visible output |
| --- | --- | --- | --- |
| `primary_before` | 2240×486, 160×18 | No graphic | Original primary-screen sentinel |
| `initial_page` | 2240×486, 160×18 | 2240×432 | Figures 1–4, page 1/3 |
| `next_page` | 2240×486, 160×18 | 2240×432 | Figures 5–8, page 2/3 |
| `previous_page` | 2240×486, 160×18 | 2240×432 | Figures 1–4, page 1/3 |
| `resized_page` | 868×486, 62×18 | 868×432 | Figures 1–4, fitted |
| `next_page_small` | 868×486, 62×18 | 868×432 | Figures 5–8, fitted |
| `expanded_page` | 2548×486, 182×18 | 2548×432 | Figures 5–8 |
| `restored_primary` | 2548×486, 182×18 | No graphic | Original sentinel and `WSKR_PAGING_DONE` |

The worker produced all six expected PNG receipts, each with an individually
recorded SHA-256 and measured geometry; `finished: true`. The terminal
height remained 486 px. `page_capacity_changed: false`: four figures still
fit on each page when narrowed, so this run does **not** qualify an actual
page-capacity change or two-column to one-column transition. The screenshot
after alternate-screen restoration does not show the full interactive shell
prompt after the outer harness returns.

The original acceptance result was **false negative**. macOS window capture
transformed panel colors compared with the requested Matplotlib RGB.
For example, source red `(237, 36, 68)` was captured as `(218, 60, 74)`.
The former 12-unit per-channel pixel check returned zero counts despite
visibly present figures. Other visible panel colors showed similar shifts.
The fixed detector assigns sampled pixels exclusively to their nearest
palette entry within bounded RGB distance, retains wrong-page/ghost
rejection, and uses brighter, more separated generated colors for tall
windows. Tests use synthetic color-converted pixels rather than committing
the user screenshot archive.

**Qualified by screenshot inspection:** page navigation via `n`/`p`,
non-clipped fitted content across the tested resize and restoration of the
primary screen. **Still open:** true changes in page capacity, actual
post-harness shell prompt, and broader window-manager/terminal geometries.

## ICC-aware screenshot evidence — November 2, 2026

The prior 8-stage paging evidence
`20261102T030748Z-unmanaged.zip` establishes the source of the apparent
color mismatch. All eight unmodified macOS screenshots contain the same
4,032-byte ICC profile named `Display`. The screenshots' raw RGB values
are **display-profile coordinates**, not the sRGB coordinates in the PNG
submitted to Kitty. On these captures, Pillow/LittleCMS
`ImageCms.profileToProfile(display, sRGB)` recovers the requested colors
to within 0–1 8-bit channel units on solid tile interiors:

| Requested source sRGB | Captured display RGB | Recovered sRGB |
| --- | --- | --- |
| (237, 36, 68) | (218, 60, 74) | (237, 36, 68) |
| (35, 140, 219) | (69, 138, 213) | (34, 140, 219) |
| (55, 187, 103) | (97, 184, 111) | (55, 187, 103) |
| (233, 138, 40) | (220, 143, 64) | (233, 138, 39) |

This explains the old false-negative color counts far more specifically than
a loose RGB tolerance. The shared `scripts/phase3_screenshot_color.py`
reader converts tagged window captures to sRGB **before** testing palette,
red/blue presence, and history ordering. It does **not** change the PNG
sent to Kitty or modify the original screenshot. Every paging/resize stage
records the conversion mode, ICC profile description, and SHA-256 of the
embedded profile (not the profile bytes separately). Tagged screenshots
are tested with a tight 8-unit RGB Euclidean radius and exclusive
nearest-palette assignment. Untagged captures retain the documented
80-unit fallback and are marked `untagged_assumed_srgb`; malformed
embedded ICC profiles are errors, not an implicit fallback.

In an offline reclassification of the eight supplied screenshots,
the initial, previous and resized pages each yield four correct
sRGB color tiles (approximately 37,500 classified pixels per tile);
the next-page and expanded stages each yield the other four. The
restored-primary screenshot has **zero** classified tile pixels.
This supports the ICC conversion's accuracy for this particular
profile and monitor. It does not determine exactly which process
performed the display-space conversion (Kitty versus compositor versus
capture), nor prove the same transform on a different monitor.

The existing private original screenshots are sufficient to reproduce
these checks; they are not committed. A future native run will additionally
embed profile provenance in its JSON report. Keep manual screenshot review
and the separate page-capacity/prompt acceptance limits.

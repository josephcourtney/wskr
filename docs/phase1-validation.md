# Phase 1 — Local validation evidence

This file records observed outcomes. It does not replace [STATUS.md](../STATUS.md), [PLAN.md](../PLAN.md), or the final Phase 1 acceptance gates.

## First macOS run — October 20, 2026, `d10040b`

- `uv sync` passed; real Kitty suite: **5 passed**.
- `just phase1`: **43 passed, 2 failed, 1 skipped**. The PTY restoration comparisons differed in macOS's kernel-maintained `PENDIN` flag.
- `just test-tty` hung inside the legacy `tcdrain` path; the five-second per-test timeout stopped it.
- `just check` stopped at formatting/lint. Following local `just fix`, **19 Ruff issues** remained; `ty` and pytest were not reached.
- A local formatting commit was pushed, so subsequent edits were made on top of `d10040b`.

## Second macOS run — October 20, 2026, `16455ccc`

| Command | Observed result | Qualification |
| --- | --- | --- |
| `uv sync` | **PASS** | 57 packages resolved; 43 checked |
| `just phase1` | **45 passed, 1 skipped** | The opt-in dark-mode TTY test was skipped; medium-size share 28.26% advisory |
| `just check` | **FAIL** | After local format autofix, syntax and Ruff formatting passed; Ruff lint stopped at one ambiguous regex assertion; `ty`/full pytest not run |
| `just test-tty` | **35 passed** | The previous `tcdrain` hang is not observed; 26 missing size-marker warnings from legacy TTY tests |
| `just test-kitty` | **5 passed** | Includes live Kitty image and screenshot checks; 5 legacy size-marker warnings |
| Regular pyplot/Rich visual inspection | **NOT VERIFIED** | Live Kitty test uses the Python-logo image, not a representative plot or Rich panel |

The log included a local `just fix` formatting change to `tests/test_dark_mode.py`. Those uncommitted user changes were not retrieved or overwritten by the GitHub patch.

## Subsequent correction (not locally rerun)

- Converted the malformed OSC response test into per-case explicit error checks (`Unexpected OSC` versus `Oversized OSC`), avoiding regex alternation that Ruff classified as ambiguous.
- Separated the real-TTY strategy construction and assertion to retain exact behavior without formatter churn.
- The branch's updated tests and full quality gate **remain unverified on macOS**.


## Third macOS run — October 20, 2026, `a2f12f5`

The user supplied a fresh copout execution log from the Phase 1 branch. The working tree was reported clean at the start of validation, and all four gates completed successfully.

| Command | Observed result | Qualification |
| --- | --- | --- |
| `just check` | **PASS** | Compileall, Ruff format (80 files), Ruff lint, `ty`, and full pytest all passed |
| Full pytest (inside `just check`) | **181 passed, 3 skipped, 137 warnings** | Skips: opt-in dark-mode TTY and two opt-in Kitty E2E cases; size marker warnings are nonfatal |
| `just phase1` | **45 passed, 1 skipped** | One opt-in dark-mode TTY test skipped; medium-size distribution advisory |
| `just test-tty` | **35 passed, 26 warnings** | Previous `tcdrain` hang no longer observed |
| `just test-kitty` | **5 passed, 5 warnings** | Real Kitty image submission and screenshot-content verification |
| Ordinary pyplot/Rich visual display | **NOT VERIFIED** | Image-content tests use the Python-logo payload, not a stock plotted figure or Rich panel |

**Interpretation:** The executable portion of the Phase 1 safety/profile gate is now green on macOS. The package still does not prove terminal-derived font/palette/artist defaults are applied correctly to new plots or that Rich and ordinary Matplotlib appear correctly. No actual figure/artist/Rich screenshot was supplied.

**Outstanding:** validate Phase 1 style precedence and backend-owned artist defaults, capture stock Matplotlib/Rich visuals, then repeat checks against the resulting implementation commit. The project has not completed Phase 1 or advanced to the Phase 2 Kitty codec migration.

## Required completion evidence

The previously failing checks now pass at `a2f12f5`. After implementing the remaining Phase 1 backend-owned style work, rerun `just check`, `just phase1`, `just test-tty` and `just test-kitty` on the resulting commit. Record normal Matplotlib and Rich visuals independently of Kitty-logo checks. Warnings and skipped cases are tracked separately.

## Fourth macOS run — October 20, 2026, `d9b1e32`

The user ran all four local verification commands and two proposed visual smoke scripts in the same feature-branch checkout, starting with a clean working tree.

| Command | Result | Interpretation |
| --- | --- | --- |
| `uv sync` | **PASS** | Environment resolved and installed |
| `just check` | **PASS** | Compileall, Ruff format (80 files), Ruff lint, `ty`, and full pytest (**181 passed, 3 skipped, 137 test-size warnings**) |
| `just phase1` | **PASS** | **45 passed, 1 skipped**; medium-size distribution advisory |
| `just test-tty` | **PASS** | **35 passed, 26 warnings** |
| `just test-kitty` | **PASS** | **5 passed, 5 warnings** |
| Stock Matplotlib `plt.show()` script | **EXIT 0; DISPLAY UNKNOWN** | No captured text or errors; terminal images may appear without textual logs, and no screenshot was supplied |
| `RichPlot` inside `Panel` | **NO IMAGE** | The registry chose its documented default `NoOpProtocol`; printed upload/no-protocol warnings and produced an empty bordered panel |
| End-of-run `git status` | **CLEAN** | Local head `d9b1e32` |

**Diagnosis of the Rich smoke:** The suggested test script omitted `WSKR_PROTOCOL=kitty`. The current registry defaults to `noop` unless explicitly configured. Thus the empty panel demonstrates unsupported/default configuration behavior, not a failure of a successfully negotiated Kitty upload. The experimental inline Kitty upload/placement path remains unverified, so setting the variable does not guarantee working Rich graphics.

**Code follow-up:** A safe Rich fallback now shows an in-panel message when `NoOpProtocol` is used, without issuing an invalid image upload or corrupting surrounding layout. A focused regression test was added. This change was **not** included in the fourth local run and must be validated independently.

**Visual evidence still missing:** actual on-screen screenshots or a direct observation for stock Matplotlib and explicitly configured Kitty-backed Rich layouts; captured stdout and a passing Kitty-logo E2E test are insufficient.

## Fifth macOS run — October 20, 2026, `5e3396a`

The user fetched the Rich fallback change and ran the four quality and terminal gates from a clean checkout.

| Command | Result | Notes |
| --- | --- | --- |
| `just check` | **FAIL at Ruff format** | `tests/test_rich_noop_fallback.py:30:1` had one surplus trailing blank line. Compileall passed, but Ruff lint, `ty` and full pytest were not reached |
| `just phase1` | **45 passed, 1 skipped** | Medium-size distribution warning remains advisory |
| `just test-tty` | **35 passed, 26 warnings** | No regressions detected |
| `just test-kitty` | **5 passed, 5 warnings** | Live Kitty transport checks remain green |

The lone formatting issue was repaired in a subsequent commit by removing the trailing blank line. **No rerun on that repaired commit has been provided.** The new Rich no-op regression test was not included in the focused `just phase1` recipe and thus remains unverified until the full pytest suite runs. Actual standard Matplotlib and Kitty-backed Rich screenshots remain outstanding.

## Sixth macOS run — October 20, 2026, `8430014`

The user fetched the formatting correction and ran `just check` from a clean local feature-branch checkout.

| Gate | Observed result |
| --- | --- |
| `python -m compileall -q src tests scripts` | **PASS** |
| `ruff format --check src tests scripts` | **PASS — 81 files already formatted** |
| `ruff check --no-fix src tests scripts` | **PASS** |
| `ty check src tests scripts` | **PASS** |
| Full `pytest -q` | **PASS — 182 passed, 3 skipped, 137 warnings, 11.90 s** |

The three skips were the opt-in dark-mode TTY test and two opt-in Kitty E2E tests. Test-size warnings remain advisory; the measured distribution was 35 small and 13 medium categorized cases, with a distribution warning. The newly added `tests/test_rich_noop_fallback.py` test was executed and passed, raising the passing count from 181 to 182.

This completes the full automated quality gate for the `8430014` source tree. The immediately preceding local run at `5e3396a` established `just phase1` (45 passed, one skip), `just test-tty` (35 passed) and `just test-kitty` (5 passed). Since those focused runs, the only implementation-file change was a trailing-blank-line formatting correction to a regression test.

**Still not demonstrated:** visual stock Matplotlib rendering; Rich with `WSKR_PROTOCOL=kitty`; terminal-derived font, palette and artist defaults being installed without overriding explicit user choices. These remain Phase 1 acceptance work, not quality-gate failures.

## Phase 1 implementation after the sixth run — awaiting new macOS evidence

New commits add conservative pyplot `None`-argument handling, a figure-local Matplotlib style context and default rectilinear axes class, late legend/text/annotation styling, contrast-filtered palette selection, and deterministic style/precedence tests. `just phase1` now includes the new regression file. `scripts/phase1_visual_smoke.py` / `just visual-smoke` provide standard pyplot, explicit Kitty-backed Rich and text-only fallback scenarios.

**No macOS Ruff, ty, pytest or real-Kitty visual result has yet been supplied for those commits.** The last accepted code quality gate remains `8430014`; do not carry its 182-pass count forward to the newer implementation. Capture real graphics evidence using [phase1-visual-procedure.md](phase1-visual-procedure.md) and report the exact validated commit.

## Seventh macOS run and three visual captures — October 21, 2026, `0ab5b47` + local `just fix`

The user supplied a terminal log and screenshots of all three `just visual-smoke` modes. The worktree is recorded dirty because `just fix` reformatted and autofixed source; screenshots therefore characterize the local worktree, not a clean commit.

| Gate | Observation |
| --- | --- |
| `just check` | **FAIL** at Ruff formatting: `core.py`, `figure.py`, `test_terminal_figure.py` needed formatting. `just fix` reformatted them and autofixed 14 lint errors, leaving seven `any-type` complaints in figure/axes convenience override signatures. `ty` and full pytest not reached |
| `just phase1` | **53 passed, 1 failed, 1 skipped**. The single failure compares Matplotlib's NumPy-array `legend(labelcolor="blue")` RGBA color with the string `"blue"`; the legend itself was created |
| `just test-tty` | **35 passed**, 26 legacy size-marker warnings |
| `just test-kitty` | **5 passed**, 5 legacy size-marker warnings |
| `just visual-smoke matplotlib` | **IMAGE VISIBLE.** Sine/cosine graph, title, legend and axes are present. Reported `figure.get_size_inches()=(6,6)`, `dpi=300`. Dark terminal background surrounds white plotting axes; black labels/title over dark margins have poor contrast |
| `WSKR_PROTOCOL=kitty just visual-smoke rich` | **NOT GRAPHICAL.** Registry reports unknown `kitty`, lists only `noop`, shows an in-panel text fallback in panel and table |
| `just visual-smoke noop` | **TEXT FALLBACK PASS.** In-panel and table-cell explanatory text is legible, with intact borders and no raw graphics escape sequence visible |

The Matplotlib figure's 6-inch size and 300 DPI may originate from nondefault user Matplotlib rcParams; such values are user-owned and should not be silently overwritten to force terminal sizing. This remains to be measured, not guessed. Transparent figure margins and black text make the result poorly matched to the dark terminal even though PNG transport works.

**Code corrections after the screenshots (unverified locally):** compare the legend's RGBA value elementwise; avoid forbidden `Any` override signatures; explicitly register built-in Kitty protocols at lookup while preventing the known-incomplete inline transport from uploading/querying. A later `WSKR_PROTOCOL=kitty` Rich run should report that inline placement is unavailable, **not display a graph**. Real Rich graphics require Phase 2/4 protocol work and separate screenshot evidence.

The original screenshots were supplied in chat; no screenshot image assets were committed into Git.

## Eighth macOS run — October 21, 2026, `55f217a` + local `just fix`

The user preserved earlier local Ruff autofixes in a stash, fetched/pulled the updated feature branch, and ran all four automated gate commands. The checkout became dirty again when `just fix` applied three additional local corrections.

| Command | Actual result |
| --- | --- |
| `just check` (first attempt) | **FAIL at Ruff lint** — three autofixable findings (core import ordering, figure private-member rule name and falsy `dict.get` default) |
| `just fix` | **PASS** — zero remaining Ruff lint findings |
| `just check` (after autofix) | **FAIL at ty** — five invalid-argument-type diagnostics in `core.py` and `figure.py`, for string-keyed `RcParams` and `rc_context` expecting keys narrowed to Matplotlib's declared literals. Full pytest not run |
| `just phase1` | **54 passed, 1 skipped**; size distribution advisory (33 small/22 medium) |
| `just test-tty` | **35 passed, 26 size-marker warnings** |
| `just test-kitty` | **5 passed, 5 size-marker warnings** |

**Correction committed after this run, not locally revalidated:** backend and figure styling now enumerate Matplotlib's typed `RcParams` keys to determine eligible backend-owned defaults, rather than using arbitrary resolver string keys to index `RcParams`; the resulting scoped style mapping also has a statically valid key type for `rc_context`. The branch incorporates the three observed Ruff autofixes. There were no changes to low-level TTY/Kitty graphics transport.

**Next evidence needed:** a fresh `just check` and `just phase1` on the corrected commit. Previous TTY and Kitty passes can be retained as evidence for unchanged transport code. The user's stashed changes remain in their local Git stash and were not deleted or modified remotely.

## Ninth macOS run — October 21, 2026, `ab3ad41`

The user provided a new copout run on the clean Phase 1 checkout at `ab3ad419f5458226f036e4273829faf8d8fd37d0`. The command returned status 0 after fetching/pulling and executing both requested validation gates. The prior local Ruff changes were preserved in a Git stash.

| Gate | Observed result |
| --- | --- |
| `just check` | **PASS** — compileall, Ruff format (85 files), Ruff lint, `ty`, and full pytest |
| Full pytest | **194 passed, 3 skipped, 137 nonfatal warnings, 9.69 s** |
| `just phase1` | **54 passed, 1 skipped, 0.79 s** |
| `just test-tty` | **NOT RERUN** here; prior 35 passed at `55f217a`, with no subsequent TTY implementation changes |
| `just test-kitty` | **NOT RERUN** here; prior 5 passed at `55f217a`, with no subsequent Kitty transport changes |

The five `ty` errors involving dynamic `RcParams` string keys have been resolved; the full suite now runs. The three default-suite skips remain the opt-in dark-mode TTY check and two opt-in Kitty E2E cases. The 137 warnings relate to missing legacy test-size markers. The categorized Phase 1 subset has 33 small and 22 medium cases, triggering an advisory (medium share 40%).

**What this validates:** deterministic terminal-profile, safe-query and style-precedence code, full static checks, and the registered-Kitty Rich diagnostic tests. It does **not** demonstrate new on-screen visuals or collection of live terminal colors with safely owned input. Existing screenshots remain the seventh-run baseline.

**Next evidence:** record current/default Matplotlib rcParams and capture actual Kitty screenshots on the current styling implementation before deciding whether the oversized figure and low-contrast labels can be corrected without overriding explicit user-owned style. Full Rich Kitty graphics remain Phase 2/4.

## New automated evidence collector (not yet exercised on macOS)

Following the ninth passing quality gate, the feature branch added `scripts/phase1_evidence.py` (`just evidence`) and `scripts/find_kitty_window.swift`. The collector runs the existing four gates, takes dedicated-window macOS screenshots of Matplotlib, explicitly selected Kitty-backed Rich diagnostic, and noop Rich fallback, saves reference rasters/configuration and logs, and produces a run-specific ZIP and SHA-256 manifest even on partial failures. It does not interpret a captured screenshot as a visually correct graph.

**Validation status:** implementation and mocked regression tests are committed, but neither the updated `just check` nor an actual GUI evidence collection has been observed. Results from `ab3ad41` do not qualify the new scripts. When the collector is run, record its exact revision and attach the ZIP; keep distinct states for passed checks, failed/missing screenshots, and captured-but-unreviewed images.

## Tenth macOS run — October 21, 2026, `2dbb65f`: first full evidence ZIP

**Archive:** `20261021T144324145972Z-2dbb65f558-a36430.zip`, recorded at 2026-10-21T14:43:24Z. The caller launched `just evidence`; the command exited 1 because its quality gate failed. The archive was still generated successfully and includes `manifest.json`, all command logs, reference PNGs and three independent Kitty window captures with SHA-256 hashes.

| Component | Observed outcome |
| --- | --- |
| `just check` | **FAIL** at `ruff format --check`: unformatted `scripts/phase1_evidence.py:55:29` and `tests/test_phase1_evidence.py:48:1`. Ruff lint, `ty`, full pytest were not reached |
| `just phase1` | **PASS — 54 passed, 1 skipped**; size distribution advisory, 33 small/22 medium |
| `just test-tty` | **PASS**, legacy size-marker warnings |
| `just test-kitty` | **PASS**, legacy size-marker warnings |
| GUI screenshots | **3/3 captured**, each 553×1381 pixels; visual content separately inspected |
| `matplotlib-screen.png` | Sine/cosine image genuinely visible with no obvious cropped data; axes interior/legend legible. **Title, tick labels and axis labels have nearly zero contrast** on the dark outside margin |
| `rich-screen.png` | Proper `Kitty inline placement unavailable` diagnostic, contained by both Rich panel and table; no image expected or shown |
| `noop-screen.png` | Proper `image unavailable (no graphics protocol)` diagnostic in the panel and table; no border damage |
| `matplotlib-rcparams.log` | **PASS**; establishes nondefault 6×6 inch `figure.figsize`, 300 DPI, transparent figure background and transparent exports |

Recorded Matplotlib values: `figure.figsize=[6.0,6.0]` vs default `[6.4,4.8]`; `figure.dpi=300` vs `100`; `figure.facecolor=none` vs `white`; `axes.facecolor=white`; `text.color=black`; `axes.labelcolor=black`; `savefig.transparent=True` vs `False`. This is **configured user styling**, so the backend must not silently replace it to improve screenshot contrast or size. The image transport did display a graph.

The screenshots were saved in a uniquely titled, dedicated Kitty window identified through CoreGraphics. A zero screenshot error code was not itself treated as proof; the actual screenshot PNGs were inspected after upload. The archive is not a clean pass because `just check` failed.

**Subsequent branch correction (not verified on macOS):** normalized Ruff formatting in the two reported files; validation of lint, `ty`, and the evidence-runner regression tests remains pending. No changes were made to Kitty image transmission or figure rendering.

## Eleventh macOS run — October 21, 2026, `a1a722e`: scoped screenshots, formatter gate

**Archive:** `20261021T172402727215Z-a1a722ecea-640427.zip`, recorded starting 2026-10-21T17:24:02Z from a clean `feature/phase1-terminal-profile-20261020` checkout (Python 3.14.0, macOS arm64, `TERM=xterm-kitty`). The user supplied the complete ZIP; all **14 recorded SHA-256 file hashes matched** the actual archive entries. `just evidence` exited 1 because its full quality gate failed.

| Component | Observed outcome |
| --- | --- |
| `uv sync` | **PASS** — 57 packages resolved, 43 checked |
| `just check` | **FAIL** at Ruff format: `scripts/phase1_evidence.py:290:23`. Compileall passed; lint, `ty`, full pytest were **not reached** |
| `just phase1` | **PASS — 55 passed, 1 skipped** (new transparent-style regression included); 33 small/23 medium advisory |
| `just test-tty` | **PASS — 35 passed**, 26 nonfatal legacy marker warnings |
| `just test-kitty` | **PASS — 5 passed**, 5 nonfatal marker warnings, real Kitty image/screenshot test |
| Screenshots | **3/3 captured and visually reviewed**, separate 1272×1381 RGBA Kitty window captures; manifest still says `captured_unreviewed` because classification occurs outside the collector |
| `matplotlib-screen.png` | Real sine/cosine raster, axis grid, line colors and legend; no missing graphics. The black title, outside labels and tick text have poor contrast on transparent dark margins. The unusually large figure fills much of the viewport; no claim of legible default appearance |
| `rich-screen.png` | Correct **inline placement unavailable** diagnostic in both the Rich panel and table, with intact borders and no graphical upload expected |
| `noop-screen.png` | Correct **no graphics protocol** in-layout text fallback in panel and table, with intact borders |
| `matplotlib-rcparams.log` | **PASS** — retains user-configured 6×6-inch figure, 300 DPI, `figure.facecolor=none`, black labels/text, white axes and `savefig.transparent=True` |

Both Rich modes behaved as designed for Phase 1. The Matplotlib PNG transport visibly worked; readability is limited by explicit/user-owned style. As adopted in ADR-002, do not silently recolor that output. The Kitty stderr logs contain warnings about unsupported *user Kitty config keys* `clear_all_in_scrollback` and `hide_single_tab`; these did not prevent capture and are unrelated to the Python quality-gate failure.

**Follow-up commit, not yet locally tested:** `fd8be4f` replaced the collector's formatter-sensitive multiline conditional with an ordinary `if gui` branch, preserving `--no-gui` semantics. The full quality gate must be rerun because the previous failure stopped before Ruff lint, `ty` and full pytest. No terminal transport or Matplotlib behavior was changed. Keep the Phase 1 PR in draft until the post-fix evidence passes.

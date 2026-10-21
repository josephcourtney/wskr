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

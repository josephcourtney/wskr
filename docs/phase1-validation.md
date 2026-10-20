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

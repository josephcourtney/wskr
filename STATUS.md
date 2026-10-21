# wskr — Current Status

Handoff: [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md), [Phase 1 evidence](docs/phase1-validation.md).

## Current focus

**Phase 1 automated gate passes; final terminal-profile integration and visual acceptance remain open.** Feature branch `feature/phase1-terminal-profile-20261020`; `main` unchanged.

## Verified on macOS — October 21, 2026, `ab3ad41`

- `just check`: **PASS**. Python compileall, Ruff format (**85 files**), Ruff lint, `ty`, and full pytest (**194 passed, 3 skipped, 137 nonfatal size-marker warnings**, 9.69 s).
- `just phase1`: **54 passed, 1 skipped** (size-distribution advisory: 33 small, 22 medium).
- Previously verified at `55f217a`: `just test-tty` **35 passed** and `just test-kitty` **5 passed**. No TTY/Kitty implementation changes since that run.
- Earlier real-Kitty screenshots: stock Matplotlib plot is visible, but dark-terminal margin contrast is poor; it reported 6 × 6 inches / 300 DPI. `noop` Rich fallback displays correctly in panel/table.

## Implemented

- Provenance-aware terminal geometry/color profile, owned and bounded OSC I/O, decisive light/dark results, scoped figure/axes defaults and explicit-style precedence tests.
- Built-in Kitty transport is selectable; unsafe Rich inline placement remains disabled with an in-layout diagnostic.
- The five `ty` errors from string-keyed `RcParams` filtering are resolved and tested.

## Remaining acceptance

- Inspect actual versus default Matplotlib rcParams to establish ownership of sizing, background and text colors before changing visual defaults.
- Characterize missing runtime terminal colors/font/DPI/graphics capability where safely obtainable with caller-owned input; preserve unknown provenance elsewhere.
- Confirm post-fix Rich Kitty diagnostic and recheck normal plot contrast with screenshots. Real Rich image placements belong to Phase 2/4.
- Truthfully classify remaining legacy size markers; keep their warnings visible.

## Handoff

No current automated quality failure. Do not merge or declare all Phase 1 requirements met solely from the green suite; record visual/profile decisions and verify new implementation changes before closure.

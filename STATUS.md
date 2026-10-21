# wskr — Current Status

Handoff: [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md), [Phase 1 evidence](docs/phase1-validation.md).

## Current focus

**Phase 1 figure/axes defaults need fresh macOS validation.** Work remains on `feature/phase1-terminal-profile-20261020`; `main` is unchanged.

## Local evidence — October 21, 2026, `0ab5b47` plus local autofixes

- `just check`: stopped at Ruff format; `just fix` reformatted three files and left seven `Any` annotation violations.
- `just phase1`: **53 passed, 1 failed, 1 skipped**. The failure was a NumPy RGBA array compared to a string for explicit legend label color, not a rendered legend regression.
- `just test-tty`: **35 passed**; `just test-kitty`: **5 passed**.
- **Real Kitty screenshot:** stock Matplotlib figure is visible with sine/cosine lines, but black title/ticks/labels have poor contrast against the dark transparent margin; figure reports `6 × 6` inches at `300 DPI`, likely user rcParams rather than terminal-derived values. Display-time sizing remains Phase 3.
- **Rich screenshot:** explicit `WSKR_PROTOCOL=kitty` was **unknown** because the module was not loaded into the registry. The `noop` in-panel message is visibly correct in both panel and table.

## Subsequent fixes — not locally verified

- Match explicit legend color using RGBA, not scalar string equality. Remove annotated `Any` from overridden Matplotlib convenience methods.
- Lazily register selected built-in Kitty transport; Rich now reports inline placement unavailable without calling the known-broken raw PNG upload / shared-TTY query. Kitty `icat` Matplotlib output is unchanged.
- Added regression cases for recognized Kitty selection, no unsafe Rich upload and unknown protocol behavior.

## Remaining

- Run `just check`, `just phase1`, `just test-tty`, `just test-kitty` on the new branch head.
- Determine requested vs backend-owned figure/axis colors and geometry from actual rcParams, and characterize contrast for transparent margins; do not override explicit style.
- Actual Rich inline graphics/placement is Phase 2/4; it is **not** working or validated. Legacy test-size warnings remain.

## Handoff

Do not merge until new macOS gates pass. Preserve uncommitted local `just fix` changes while updating the worktree.

# wskr — Current Status

Handoff: [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md), [Phase 1 evidence](docs/phase1-validation.md).

## Current focus

**Phase 1 automated validation is green; terminal-aware styling and actual plotting visuals remain unaccepted.** Work remains on `feature/phase1-terminal-profile-20261020`; `main` is unchanged.

## Verified on macOS — October 20, 2026

- At `8430014`, `just check` **passed end-to-end**: compileall, Ruff format (81 files), Ruff lint, `ty`, full pytest **182 passed, 3 skipped**. **137 nonfatal legacy size-marker warnings**.
- At `5e3396a`, `just phase1` **45 passed, 1 opt-in skip**; `just test-tty` **35 passed**; `just test-kitty` **5 passed**.
- The Rich `NoOpProtocol` fallback regression is now covered by the passing full suite at `8430014`; actual in-terminal appearance of the fallback remains unobserved.
- Stock `MPLBACKEND=wskr_kitty` `plt.show()` exited 0 without errors or textual output. No screenshot establishes whether the plot appeared.
- Rich with unset `WSKR_PROTOCOL` previously produced an empty panel because `noop` was selected. Explicit `WSKR_PROTOCOL=kitty` rendering is unverified.

## Implemented

- Immutable provenance-aware terminal profile, bounded caller-owned OSC queries, color parsing, light/dark precedence, pure default resolver, initial figure pixel sizing and import-side-effect removal.
- Rich text fallback when no graphics transport is configured, with regression coverage.

## Remaining acceptance

- Apply terminal-derived font, palette and artist defaults only to backend-owned values; preserve explicit Matplotlib styling.
- Verify actual Kitty screenshot/placement of a stock Matplotlib figure and an explicitly Kitty-backed Rich panel.
- Classify outstanding legacy test sizes without masking warnings. Display-time resize and direct protocol remain later phases.

## Handoff

No code-quality failures are outstanding. Complete the integration/visual gates, rerun checks if code changes, and only then consider merging Phase 1.

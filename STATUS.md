# wskr — Current Status

Handoff: [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md), [Phase 1 evidence](docs/phase1-validation.md).

## Current focus

**Phase 1 automated quality gate is blocked pending revalidation of the rcParams typing fix.** Work remains on `feature/phase1-terminal-profile-20261020`; `main` is unchanged.

## Local evidence — October 21, 2026, `55f217a` plus local Ruff autofixes

- `just check`: compileall, formatting and lint **pass after `just fix`**; `ty` reports **five invalid-argument-type errors** when string keys index Matplotlib's typed `RcParams` and are passed to `rc_context`. Full pytest was not reached.
- `just phase1`: **54 passed, 1 skipped** (test-size distribution advisory).
- `just test-tty`: **35 passed**; `just test-kitty`: **5 passed**. Both have legacy test-size warnings.
- Prior real-Kitty screenshots prove visible Matplotlib plotting, with poor dark-margin text contrast and reported 6 × 6 inches / 300 DPI. The default Rich `noop` fallback appears correctly in panel/table.
- Direct Rich inline graphics are not available; the Kitty transport is recognized but its unsafe placement path remains disabled.

## Subsequent code correction — unverified locally

- Iterate valid Matplotlib `RcParams` keys when filtering backend-owned defaults and creating scoped `rc_context` values, eliminating arbitrary-string indexing without ignores or casts.
- Incorporated observed import sorting, private-member suppression naming and falsy dictionary-get fixes from the local `just fix`.
- No TTY transport or Kitty codec changes in this correction.

## Remaining acceptance

- Preserve any new uncommitted `just fix` edits; then update from the feature branch and run `just check` followed by `just phase1`.
- Inspect actual rcParams/defaults before changing dark-theme contrast or 6 × 6 inch figure sizing. Do not override explicit user style.
- Rich inline upload/placement belongs to Phase 2/4. Legacy test-size classification remains unfinished.

## Handoff

Do not merge before the corrected branch passes the full macOS quality gate. Record results against the exact tested commit.

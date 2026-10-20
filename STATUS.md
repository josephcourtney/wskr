# wskr — Current Status

Handoff: [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md), [Phase 1 evidence](docs/phase1-validation.md).

## Current focus

**Phase 1 is under validation on `feature/phase1-terminal-profile-20261020`; `main` remains at the accepted Phase 0 baseline.**

## Verified locally — October 20, 2026, commit `16455ccc`

- `uv sync` passed; `just phase1`: **45 passed, 1 expected opt-in skip**. Medium-size test distribution advisory remains.
- `just test-tty`: **35 passed, 26 size-marker warnings**; the previous `tcdrain` hang is no longer observed.
- `just test-kitty`: **5 passed, 5 size-marker warnings**, including real Kitty screenshot-content verification.
- `just check`: syntax/format passed after local `just fix`; Ruff stopped on one ambiguous `pytest.raises(match=...)` pattern. **`ty` and full pytest did not run.**

## Changes after that local run (not yet verified)

- Committed explicit per-case OSC exception assertions and formatter-stable real-PTY test code.
- No graphics transport or profile semantics were changed.
- Prior terminal safety and lint corrections are preserved.

## Remaining gates

- Rerun `just check` on the latest branch tip and address any newly exposed `ty`/pytest failures.
- Repeat Phase 1, PTY, and live Kitty tests; preserve truthful test-size categories.
- Actual stock Matplotlib/Rich visual inspection, terminal-derived artist styling, and resize safety remain incomplete.

## Handoff

The user's last `just fix` left local modifications. Inspect or stash before pulling; do not report Phase 1 complete or merge until the updated quality gate passes.

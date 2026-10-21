# wskr — Current Status

Handoff: [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md), [Phase 1 validation](docs/phase1-validation.md).

## Current focus

**Phase 1 targeted tests pass; final macOS quality gate is still blocked by Ruff formatting.** Work remains on `feature/phase1-terminal-profile-20261020`, [draft PR #17](https://github.com/josephcourtney/wskr/pull/17); Phase 0 is on `main`.

## Latest macOS evidence — October 21, 2026, `207005d`

- Clean checkout, `uv sync` passed, and `just evidence` generated a valid ZIP with all **14 file hashes verified**.
- `just check` **FAILED** at `scripts/phase1_evidence.py:314:13` (Ruff format); lint, `ty` and full pytest **did not run**.
- `just phase1`: **55 passed, 1 skipped**; `just test-tty`: **35 passed**; `just test-kitty`: **5 passed**.
- Three real 712×619 Kitty captures reviewed. Rich Kitty reports inline placement unavailable; Rich noop shows an intact text fallback. Matplotlib PNG transfer works, but **the standard plot is severely clipped**: title, legend and labels are out of view in this small window, whereas the reference PNG is complete.

## Recent correction / blockers

- Rewrote the formatter-sensitive failure aggregation in `scripts/phase1_evidence.py` after this run; **no post-fix macOS check has been supplied**.
- The clipping is a known smaller-viewport limitation with user-owned 6×6-inch/300-DPI and transparent/black-text Matplotlib settings, not evidence that Kitty failed to transmit the image. ADR-002 prohibits silently overriding explicit styling. Documented as Phase 3 display work.
- Live OSC foreground/background acquisition is caller-owned/opt-in. Direct native Kitty encoding, real Rich inline graphics and managed resize are later phases; legacy size-marker warnings are advisory.

## Handoff

Run `just evidence` at a clean new branch head to complete Ruff, `ty` and full pytest qualification. Compare three captures, explicitly noting size and clipping. **Do not mark PR #17 ready or merge until Phase 1's quality acceptance is evidenced.**

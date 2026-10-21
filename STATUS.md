# wskr — Current Status

Handoff: [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md), [Phase 1 validation](docs/phase1-validation.md).

## Current focus

**Phase 1 implementation is awaiting a clean full-suite acceptance run.** The feature branch is `feature/phase1-terminal-profile-20261020`, [draft PR #17](https://github.com/josephcourtney/wskr/pull/17). Phase 0 is on `main`.

## Latest macOS evidence — October 21, 2026, `9912c5f`

- Clean `just check`: **syntax PASS; Ruff format PASS (87 files); Ruff lint PASS; `ty` PASS**.
- Full pytest **FAILED during collection**, before running tests: `tests/test_phase1_evidence.py` could not import `scripts.phase1_evidence` under `--import-mode=importlib`. The 137 missing size-marker warnings are advisory.
- `pyproject.toml` now sets pytest `pythonpath = ["."]` to expose the existing repository-local `scripts` package. A minimal pytest reproduction passed; **the fix remains unvalidated on macOS**.

## Earlier observed functional evidence — `207005d`

- `just phase1`: **55 passed, 1 skipped**; `just test-tty`: **35 passed**; `just test-kitty`: **5 passed**.
- All three scoped real Kitty screenshots were captured; at 712×619, the ordinary Matplotlib figure was **severely clipped**, whereas its reference PNG was complete. Rich Kitty/noop fallback diagnostics rendered correctly.
- The plot inherits user-configured 6×6-inch, 300-DPI, transparent/black-text rcParams. Per ADR-002, do not silently rewrite user style; small-window fitting belongs to Phase 3.

## Known limitations and next action

- Live OSC colors require caller-owned input; native Kitty encoding, Rich inline placement and display lifecycle are Phase 2–4 work.
- **Run `just check` on latest clean branch head.** If green, run `just evidence` to qualify the Kitty capture path, archive the results and inspect visual regressions. Do not mark PR #17 ready or merge without the final gate.

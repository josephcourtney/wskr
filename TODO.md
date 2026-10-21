# wskr — Immediate Tasks

Phase 1 closeout; see [validation history](docs/phase1-validation.md), [evidence collector](docs/phase1-evidence-bundles.md) and [contrast decision](docs/adr/0002-terminal-measured-defaults.md).

- [ ] From a clean checkout of `feature/phase1-terminal-profile-20261020` on macOS with Kitty, run `uv sync && just evidence`; record commit, exit status and ZIP path.
- [ ] Confirm `just check` (including the new transparent-style regression), `just phase1`, `just test-tty` and `just test-kitty` results in that single ZIP; repair any errors without substituting older passing logs.
- [ ] Inspect all three **actual** window screenshots: stock Matplotlib image/labels/bounds; expected Rich Kitty inline-unavailable diagnostic; and Rich noop in-layout fallback. Record clipping, legibility and artifacts separately from command exit codes.
- [ ] If all Phase 1 acceptance conditions pass, record exact validated commit in `docs/phase1-validation.md` and update `STATUS.md`; then merge the feature branch to `main`. If not, retain the branch and the failed evidence.
- [ ] Treat the poor contrast of explicit transparent/black-text figures as faithfully rendered user settings, not a Phase 1 transport failure. Do not silently adapt; any requested opt-in display-only contrast assistance is deferred to Phase 3.
- [ ] Keep caller-owned OSC colors optional and distinguish unavailable values from measurements; implement deeper graphics negotiation with the Phase 2 transport. Classify legacy pytest size warnings separately from Phase 1 acceptance.

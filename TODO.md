# wskr — Immediate Tasks

See [latest observed validation](docs/phase1-validation.md), [evidence procedure](docs/phase1-evidence-bundles.md) and [contrast policy](docs/adr/0002-terminal-measured-defaults.md).

- [ ] Fetch the latest `feature/phase1-terminal-profile-20261020` commit in a clean macOS Kitty checkout and rerun `uv sync && just evidence`. The last run at `a1a722e` failed only at Ruff format, but lint/`ty`/full pytest were not reached.
- [ ] Verify the new run's `just check` (including all newly added regressions), `just phase1`, `just test-tty` and `just test-kitty`; preserve the complete ZIP even if any gate fails.
- [ ] Compare the new Kitty screenshots with the reviewed `a1a722e` baseline: visible Matplotlib raster and known low-contrast user styling; expected Rich Kitty inline-unavailable and Rich noop fallback text; intact layout. Treat contrast of explicitly black text on transparent dark margins as user-owned, not an automatic recoloring target.
- [ ] If the full gate passes and screenshots have no new regressions, record the exact validated commit in `docs/phase1-validation.md`, finalize `STATUS.md`, mark [draft PR #17](https://github.com/josephcourtney/wskr/pull/17) ready, and merge to `main`. Otherwise repair and retest.
- [ ] Defer opt-in contrast assistance/display-time resizing to Phase 3, native Kitty transport/capability negotiation to Phase 2, and real Rich inline placement to Phase 4. Legacy test-size warnings remain advisory; classify them separately.

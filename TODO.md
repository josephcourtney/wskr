# wskr — Immediate Tasks

See [Phase 1 validation](docs/phase1-validation.md), [evidence procedure](docs/phase1-evidence-bundles.md) and [ADR-002](docs/adr/0002-terminal-measured-defaults.md).

- [ ] Fetch latest `feature/phase1-terminal-profile-20261020` to a clean macOS Kitty checkout and run `just check`. The `9912c5f` run passed syntax, format, lint and `ty`, but pytest collection failed on `scripts`; the new `pythonpath = ["."]` configuration is locally unverified.
- [ ] If the full pytest suite passes, run `just evidence`, ensuring `just phase1`, `just test-tty`, and `just test-kitty` succeed at the same SHA. Retain the run-specific ZIP and all command logs.
- [ ] Inspect three real screenshots and record each window's dimensions; preserve the documented **712×619 Matplotlib clipping** observation, keeping terminal viewport fitting separate from Phase 1's safe discovery and styling requirements.
- [ ] Record the fully tested SHA in `docs/phase1-validation.md`, complete `STATUS.md`, mark [PR #17](https://github.com/josephcourtney/wskr/pull/17) ready, then merge only if Phase 1 acceptance gates are satisfied.
- [ ] Continue native Kitty transmission in Phase 2, viewport-aware display/resizing in Phase 3 and Rich inline placement in Phase 4. Do not override explicit user Matplotlib settings to conceal clipping; legacy size-marker warnings remain advisory.

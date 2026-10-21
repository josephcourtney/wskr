# wskr — Immediate Tasks

See [validation history](docs/phase1-validation.md), [evidence procedure](docs/phase1-evidence-bundles.md), and [ADR-002](docs/adr/0002-terminal-measured-defaults.md).

- [ ] Fetch the latest `feature/phase1-terminal-profile-20261020` in a clean macOS Kitty checkout and run `uv sync && just evidence`. The previous clean `207005d` run stopped at Ruff formatting in `scripts/phase1_evidence.py:314:13`; its replacement has not been verified.
- [ ] Confirm that `just check` executes and passes **format, lint, `ty`, and full pytest**, alongside `just phase1`, `just test-tty`, and `just test-kitty`. Preserve the full ZIP, including any failure logs, and record the exact tested SHA.
- [ ] Inspect and record three actual screenshot scenarios, including Kitty window dimensions. The 712×619 Matplotlib screenshot is **severely clipped**, unlike the larger earlier screenshot; do not label it as a fully visible graph. Rich Kitty and noop fallbacks display correctly.
- [ ] Determine whether a separate clean Matplotlib-style baseline is needed for Phase 1 signoff: the current reference inherits nondefault global 6×6-inch/300-DPI transparent settings. Distinguish documented Phase 3 fitting limitations from regressions in Phase 1 style defaults.
- [ ] After the complete quality gate passes and Phase 1 acceptance evidence is recorded, finalize `STATUS.md`, mark [draft PR #17](https://github.com/josephcourtney/wskr/pull/17) ready, and merge. Do not silently change user-owned Matplotlib figure dimensions or colors to force the screenshot to fit.
- [ ] Continue true terminal display fitting in Phase 3, native Kitty graphics/capability negotiation in Phase 2, and Rich inline image placement in Phase 4; classify legacy size-marker warnings separately.

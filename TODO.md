# wskr — Immediate Tasks

Consult [Phase 1 validation history](docs/phase1-validation.md), [evidence procedure](docs/phase1-evidence-bundles.md) and [ADR-002](docs/adr/0002-terminal-measured-defaults.md).

- [ ] Fetch the latest `feature/phase1-terminal-profile-20261020` in a clean macOS Kitty checkout, then run `just check`. At `11343a1`, syntax/format passed but Ruff lint stopped on three evidence collector diagnostics; the screenshot-helper refactor in `adeeec4` is not yet verified.
- [ ] If the complete `just check` passes (syntax, format, lint, `ty`, full pytest), run `just evidence` to execute the Phase 1, TTY and real Kitty tests and collect a run-specific ZIP. Record the exact SHA and all checks or failures.
- [ ] Review the three window-scoped screenshots, including window dimensions. Preserve the prior **712×619 Matplotlib clipping** observation; inspect for regressions and clearly distinguish an intentional user-configured large figure from missing PNG transmission. Rich Kitty/noop expected diagnostic fallbacks must stay within panels/tables.
- [ ] If final Phase 1 gates pass, update `docs/phase1-validation.md` and `STATUS.md`, mark [draft PR #17](https://github.com/josephcourtney/wskr/pull/17) ready and merge. Do not silently overwrite user-owned plot styling to force it to fit.
- [ ] Defer explicit display-time fitting and contrast assistance to Phase 3, native Kitty transport/graphics capability negotiation to Phase 2, and real Rich inline placement to Phase 4. Classify nonfatal legacy test-size warnings separately.

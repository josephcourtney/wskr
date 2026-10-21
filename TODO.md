# wskr — Immediate Tasks

Phase 1 acceptance work; see [PLAN.md](PLAN.md), [validation evidence](docs/phase1-validation.md), and [visual procedure](docs/phase1-visual-procedure.md).

- [ ] Capture the current and default Matplotlib values for `figure.figsize`, `figure.dpi`, figure/axes facecolors, text/label colors and transparency to distinguish user configuration from backend-owned values.
- [ ] Re-run `just visual-smoke matplotlib` and `WSKR_PROTOCOL=kitty just visual-smoke rich` in Kitty. Record visible figure bounds/contrast and confirm Rich shows the expected unsupported-inline diagnostic without an unsafe upload.
- [ ] Decide and implement a safe caller-owned acquisition path for terminal colors, optional font/DPI/opacity and graphics capability. Unknown values must remain unknown; don't consume shared terminal input.
- [ ] If implementation changes follow, rerun `just check` and `just phase1` plus affected live tests against the new commit. Last green automated gate: `ab3ad41`.
- [ ] Complete truthful legacy/GUI test-size classification without suppressing advisory warnings.

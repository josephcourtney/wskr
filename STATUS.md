# wskr — Current Status

Handoff: [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md), [Phase 1 validation](docs/phase1-validation.md), [Kitty visual procedure](docs/phase1-visual-procedure.md).

## Current focus

**Phase 1 backend-owned styling was implemented after the last passing macOS gate, but is not yet validated.** Feature branch `feature/phase1-terminal-profile-20261020`; `main` unchanged.

## Last verified state — October 20, 2026, `8430014`

- `just check` **PASS**: compileall, Ruff format/lint, `ty`, full pytest **182 passed, 3 skipped**, 137 legacy size warnings.
- Prior focused checks: `just phase1` **45 passed, 1 skipped**; `just test-tty` **35 passed**; `just test-kitty` **5 passed**.
- A stock pyplot script exited 0 without captured output, but no screenshot verified on-screen display.
- Rich with no `WSKR_PROTOCOL` chose `noop`; its previously empty panel now has a tested visible-text fallback. Explicit Kitty-backed Rich output remains unverified.

## New implementation — **not run on macOS**

- Normal pyplot `None` figure arguments now receive backend-owned geometry and background defaults.
- A scoped Matplotlib `Figure`/`Axes` pair applies measured foreground, background, font and contrast-checked palette defaults to new axes, legends, annotations and text; custom Figure/axes types and explicit properties retain precedence.
- Added isolated style/precedence tests to `just phase1` and manual `just visual-smoke` scenarios for Matplotlib, Rich panel/table, and no-op.
- No import-time terminal I/O, global rcParams changes, or unsafe automatic OSC reads were introduced.

## Remaining

- **Run `just check`, `just phase1`, `just test-tty` and `just test-kitty` on the new branch head.**
- Capture and assess real Kitty screenshots using the visual procedure.
- Runtime OSC colors remain unknown unless a caller owns/query-routes TTY input; new-figure defaults do not yet auto-discover live colors in an unattended pyplot script.
- Legacy display-time resizing and Rich direct protocol lifecycle remain later phases. Test-size warnings are unclassified.

## Handoff

Do not merge or declare Phase 1 complete until fresh macOS quality gates pass and the scope/visual limitations have been reviewed.

# wskr — Immediate Tasks

Only unfinished, near-term execution work is listed. Long-term phase ordering is in [PLAN.md](PLAN.md).

- [ ] **P0 — establish repeatable local checks:** correct the borrowed `justfile`/`pyproject.toml` configuration that still points to Cwide; ensure `uv`, Ruff, `ty` and pytest commands target the actual wskr package/tests. Record blockers instead of hiding them.
- [ ] **P0 — capture the installed-backend baseline:** exercise `MPLBACKEND=wskr_kitty` and `module://wskr.render.matplotlib.kitty` from an installed wheel in both a real Kitty terminal (where available) and a no-TTY environment; record commands and observations.
- [ ] **P0 — pin Matplotlib semantics:** add/regress tests for explicitly sized figures, `savefig` PNG/SVG, `plt.show(block=False)`, `plt.ion()`, multiple figures and manager cleanup without changing current behavior silently.
- [ ] **P0 — pin terminal/protocol failure paths:** test no `/dev/tty`, redirected stdout, fallback selection and query timeout; identify current raw-Kitty packet mismatch and response assumptions.
- [ ] **P0 — characterize Rich placement:** exercise `RichImage` and `RichPlot` inside a Rich table/panel and compare expected vs actual output in Kitty; distinguish mocked tests from real terminal evidence.
- [ ] **P0 — document compatibility inventory:** record public import paths, backend names, relevant `WSKR_*` variables, dependency ownership and live/manual test requirements in the Phase 0 evidence.
- [ ] **P1 preparation — isolate terminal query work:** create focused tests for `OSC` parsing, false/light dark-mode detection, descriptor cleanup and metric provenance before changing implementation.

Do not mark an item complete without corresponding implementation or validation evidence; delete completed items from this file rather than archiving them here.

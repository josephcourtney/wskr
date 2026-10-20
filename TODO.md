# wskr — Immediate Tasks

Phase 1 execution, see [PLAN.md](PLAN.md) and [STATUS.md](STATUS.md).

- [ ] Run `uv sync`, `just phase1` and `just check` on `feature/phase1-terminal-profile-20261020`; fix only observed Ruff, ty or pytest failures without weakening quality gates.
- [ ] Repeat `just test-tty` and `just test-kitty`; record regression results separately from the earlier Phase 0 Kitty screenshot pass.
- [ ] Validate backend-created default and explicit `figsize`/DPI in a real Kitty figure, and capture a baseline `RichPlot` panel/table screenshot.
- [ ] Extend measured terminal detection to a safely negotiated caller-owned session, including foreground/background, palette, font and DPI where actually available; retain provenance.
- [ ] Complete backend-owned artist styling and demonstrate explicit rcParams/color precedence without global mutations.
- [ ] Add resize/refresh tests and migrate remaining legacy, input-sharing OSC paths; do not silently drop keystrokes.
- [ ] Classify pytest test-size markers and decide when strict size enforcement can be enabled.

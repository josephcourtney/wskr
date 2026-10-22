# wskr — Immediate Tasks

Phase 2 is accepted; begin Phase 3 according to [PLAN](PLAN.md). See [STATUS](STATUS.md), [Phase 2 acceptance](docs/phase2-validation.md), [ADR-002](docs/adr/0002-terminal-measured-defaults.md) and [ADR-003](docs/adr/0003-kitty-transport-and-placement.md).

- [ ] Create a dedicated Phase 3 feature branch from `main` after Phase 2 merges; keep Rich actual inline placement as a Phase 4 consumer rather than expanding native Kitty transport scope.
- [ ] Audit `src/wskr/render/matplotlib/core.py`, `size.py` and `figure.py` for mutations of explicit `figsize`, `dpi`, colors, and `savefig` behavior. Introduce tests separating backend-provided defaults from caller-owned values.
- [ ] Replace unconditional figure resizing/manager destruction with explicit image placement ownership, redraw/replace semantics and lifecycle hooks. Cover repeated show, `plt.ion()`, `draw_idle()`, multiple figures and `show(block=...)` with deterministic tests.
- [ ] Derive allocated image geometry from measured terminal cells; test viewport changes, clipping, text margins and zoom. Do not fabricate DPI or rewrite explicit styles; consider opt-in legibility assistance separately from saved exports.
- [ ] Qualify Phase 3 with full hosted quality checks, PTY faults, real Kitty screenshot comparison and small/large viewport scenarios. The existing hosted Kitty graphical workflow provides a reusable Phase 2 baseline.
- [ ] In Phase 4, integrate real Rich `ConsoleOptions` sizing, nested panels/tables, cached `U=1` virtual placements, inline text placeholder rendering, scrolling and cleanup; retain honest fallback until integration is qualified.

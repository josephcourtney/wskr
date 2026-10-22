# wskr — Immediate Tasks

Phase 2 is accepted; begin Phase 3 according to [PLAN](PLAN.md). See [STATUS](STATUS.md), [Phase 2 acceptance](docs/phase2-validation.md), [ADR-002](docs/adr/0002-terminal-measured-defaults.md) and [ADR-003](docs/adr/0003-kitty-transport-and-placement.md).

- [ ] Create a dedicated Phase 3 feature branch from `main` after Phase 2 merges; keep Rich actual inline placement as a Phase 4 consumer rather than expanding native Kitty transport scope.
- [ ] Audit `src/wskr/render/matplotlib/core.py`, `size.py` and `figure.py` for mutations of explicit `figsize`, `dpi`, colors, and `savefig` behavior. Introduce tests separating backend-provided defaults from caller-owned values.
- [ ] Replace unconditional figure resizing/manager destruction with explicit image placement ownership, redraw/replace semantics and lifecycle hooks. Cover repeated show, `plt.ion()`, `draw_idle()`, multiple figures and `show(block=...)` with deterministic tests.
- [ ] Fix the **verified 1800×1800-to-1664×952 vertical clipping** from local Phase 2 macOS Kitty evidence: upper curve/title/positive y-axis disappear and the x-label is obscured. Test both the source PNG and the displayed viewport for large user-owned `figsize`/`dpi`, plus small-window and nondefault transparent styling. Never silently override explicit Matplotlib styles; keep opt-in legibility assistance separate from saved exports.
- [ ] Qualify Phase 3 with full hosted quality checks, PTY faults, real Kitty screenshot comparison and small/large viewport scenarios. The existing hosted Kitty graphical workflow provides a reusable Phase 2 baseline.
- [ ] Clean up the evidence runner's unsupported Kitty config options (`clear_all_in_scrollback`, `hide_single_tab`) while preserving deterministic, window-scoped screenshots; confirm against the installed Kitty version.
- [ ] In Phase 4, integrate real Rich `ConsoleOptions` sizing, nested panels/tables, cached `U=1` virtual placements, inline text placeholder rendering, scrolling and cleanup; retain honest fallback until integration is qualified.

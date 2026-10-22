# wskr — Current Status

Handoff: [DESIGN](DESIGN.md), [PLAN](PLAN.md), [TODO](TODO.md), [Phase 3 evidence](docs/phase3-validation.md).

## Recently qualified

**Phase 2 accepted and merged**, with hosted quality, real Kitty Linux/Xvfb screenshots and subsequent native macOS Kitty acceptance; see [Phase 2 validation](docs/phase2-validation.md).

**Phase 3, first implementation slice qualified in [PR #21](https://github.com/josephcourtney/wskr/pull/21), but Gate P3 remains OPEN.** The backend now preserves caller figure dimensions/DPI across display, shows all registered figures without destroying them, redraws only the active figure interactively, closes each manager's own transport on destruction, and replaces rather than accumulates one-off Kitty images.

Hosted Linux/macOS 15 quality: **234 passed, 3 skipped** in each full pytest suite; **33 focused Phase 3** and **54 Phase 2** tests passed per host, with Ruff, ty and compilation green. Hosted Linux real Kitty physical/virtual graphics check passed. See [Phase 3 validation](docs/phase3-validation.md).

## Current boundaries and next focus

**Do not describe the yabai-confounded screenshot as a proven wskr clipping bug.** Stable/unmanaged Kitty versus deliberate yabai resize must be compared before attributing a defect. The newly immutable explicit figure may exceed the visible window; Phase 3 must define and test display-only fitting or managed placement without mutating figure properties.

Remaining Phase 3 work: truthful `show(block=True)`/interactive semantics, REPL/pandas workflows, debounced resize/placement redraw, scrollback lifecycle, and complete visual/module-backend/wheel acceptance. Rich inline graphics remain Phase 4.

# wskr — Current Status

Short handoff. See [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md), and [Phase 0 evidence](docs/phase0-evidence.md).

## Current focus

**Phase 0 baseline characterization is complete; Phase 1 (safe terminal discovery and styling) is next.** This is not a claim that the target backend design has been implemented.

## Verified baseline — October 20, 2026

- Local `just check` passed syntax, formatting, Ruff, `ty`, and pytest after a one-line Ruff import-order autofix; **142 passed, 3 opt-in skips**, with **145 nonfatal test-size warnings**.
- Local `just test-kitty`: **5 passed**, including a live Kitty image-submission/screenshot-content test.
- Earlier `uv sync`, baseline diagnostics, wheel/sdist build, isolated wheel smoke, and 34 TTY tests passed.
- The same import-order correction has been committed; the exact new remote commit was not separately retested.

## Known limitations

- The primary Kitty backend still depends on external `kitty icat`; the experimental native path has incorrect PNG framing.
- The backend may overwrite explicit figure size, modify rcParams at import, mishandle a valid light-theme detection, or fall back to no-op graphics.
- Sixel/iTerm2 are stubs; the present Rich placeholder path requires protocol work.
- **Visual inspection of ordinary Matplotlib and Rich output remains unverified**; the Kitty screenshot tests use a Python-logo payload, not those renderers. This is tracked for Phase 1/3/4.
- Test sizes remain unclassified in pytest; classification warnings do not fail current checks.

## Handoff

Begin [PLAN Phase 1](PLAN.md#phase-1--terminal-profile-safe-queries-style-defaults) with safe TTY/OSC tests and provenance-aware `TerminalProfile`. Preserve current baseline characterizations until deliberate target-behavior tests replace them.

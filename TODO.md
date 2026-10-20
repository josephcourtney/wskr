# wskr — Immediate Tasks

Pending work for [PLAN Phase 1](PLAN.md#phase-1--terminal-profile-safe-queries-style-defaults). Phase 0 evidence: [docs/phase0-evidence.md](docs/phase0-evidence.md).

- [ ] Add deterministic tests for bounded OSC/TTY response framing, unrelated-input handling, timeout and descriptor/termios restoration; verify non-TTY and multiplexer-safe fallback.
- [ ] Introduce an immutable, provenance-aware `TerminalProfile` for measured/inferred/configured/fallback geometry, colors, font/DPI and graphics capability.
- [ ] Fix dark/light detection's valid-`False` chaining bug; prefer queried terminal colors, with explicit override and trusted environment/OS fallbacks.
- [ ] Add pure style/default-resolution tests proving explicit `figsize`, rcParams, font and artist styling remain authoritative; eliminate import-time style mutation in the later implementation.
- [ ] Before changing Matplotlib/Rich rendering, capture one **actual** stock `MPLBACKEND=wskr_kitty` plot and one `RichPlot` in a Rich panel/table; record successes or current failures as visual baseline evidence.
- [ ] Classify existing pytest cases with truthful `small`/`medium`/`large`/`xlarge` markers and re-enable category enforcement only when the suite meets its documented policy.

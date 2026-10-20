# wskr — Immediate Tasks

Pending Phase 1 work; see [PLAN.md](PLAN.md) and [STATUS.md](STATUS.md).

- [ ] On `feature/phase1-terminal-profile-20261020`, run `uv sync`, `just phase1` and `just check`; report any newly exposed Ruff, `ty`, or full-pytest failures.
- [ ] Run `just test-tty` and `just test-kitty`, confirming that the bounded OSC path no longer hangs in `tcdrain` and the live Kitty baseline stays green.
- [ ] Manually capture an ordinary `MPLBACKEND=wskr_kitty` figure and a `RichPlot` panel/table in Kitty, recording image placement, viewport sizing and theme behavior.
- [ ] Integrate backend-owned font/palette/artist defaults without overriding user rcParams; document validated foreground/background provenance.
- [ ] Cover resize, refresh, multi-figure lifecycle and input multiplexer safety before enabling automatic terminal queries.
- [ ] Finish truthful size categorization of legacy tests; do not enable strict categories solely to silence warnings.

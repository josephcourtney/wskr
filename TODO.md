# wskr — Immediate Tasks

Phase 2 implementation is staged but not accepted. See [Gate P2](PLAN.md), [Phase 2 validation](docs/phase2-validation.md), [ADR-003](docs/adr/0003-kitty-transport-and-placement.md).

- [ ] In a clean macOS Kitty checkout of `feature/phase2-native-kitty-20261021`, run `uv sync && just check && just phase2 && just test-tty`. Repair any Ruff formatting, lint, `ty` or test regressions before making acceptance claims.
- [ ] Run `just evidence` (now includes Phase 2) and provide the complete ZIP. Verify manifest hashes, protocol-focused checks and independent Matplotlib/Rich/noop Kitty screenshots. Compare with Phase 1 visual reference and record observed clipping/contrast separately.
- [ ] Prove actual direct-Kitty `f=100` graphics transfer and owned-input ACK/negative-ACK behavior in a real terminal. Exercise scoped image delete and virtual-placement upload without claiming Rich composition works.
- [ ] Once Gate P2 checks and live visual review pass, document exact tested SHA, finalize status/change log and merge the Phase 2 PR to `main`; otherwise remain draft.
- [ ] Defer Phase 3 Matplotlib figure-size ownership, interactive show lifecycle, resize/scrollback redraw and opt-in contrast assistance. Defer Phase 4 Rich virtual text placements and real table/panel graphics.

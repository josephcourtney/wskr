# wskr — Immediate Tasks

Phase 1 is accepted on tested code SHA `5e35aa6`. The next implementation stage is Phase 2 in [PLAN.md](PLAN.md); review the [design](DESIGN.md), [Phase 1 acceptance](docs/phase1-validation.md), and [ADR-002](docs/adr/0002-terminal-measured-defaults.md).

- [ ] Build a test-first native Kitty graphics encoder: PNG `f=100`, Base64, ≤4096-byte chunks, `m` continuation, and correct escape framing.
- [ ] Implement image identity, direct transmission, placement, deletion and optional acknowledgments; keep output and input ownership explicit and bounded.
- [ ] Add capability negotiation and non-TTY/redirected-output rejection without silently claiming unsupported graphics.
- [ ] Preserve external `kitty icat` as a comparison/diagnostic until direct Kitty output is qualified; do not regress the current public Matplotlib import/backend paths.
- [ ] Qualify Phase 2 with parser/codec/transport unit tests, PTY fault tests, and real Kitty output with screenshot evidence before retiring transitional paths.
- [ ] Track the independent Phase 3 display defects: 712×619 severe plot clipping; 1272×1381 left y-tick clipping and low-contrast black text on explicitly transparent backgrounds. Preserve user styling per ADR-002; no silent contrast or size rewriting.
- [ ] Defer genuine Rich inline placement and virtual placeholders to Phase 4; classify 137 nonfatal test-size warnings as advisory until a separate testing-hygiene cleanup.

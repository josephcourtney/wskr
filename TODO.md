# wskr — Immediate Tasks

Phase 1 integration tasks; see [PLAN.md](PLAN.md) and [validation evidence](docs/phase1-validation.md).

- [ ] Complete backend-owned terminal-derived foreground, background, palette and font/artist defaults with regression tests for explicit rcParams, styles and artist precedence.
- [ ] Capture and inspect normal `MPLBACKEND=wskr_kitty` Matplotlib output inside Kitty; record whether a visible graph appears and its extent, clipping and contrast.
- [ ] Test Rich panel/table inside Kitty with explicit `WSKR_PROTOCOL=kitty` and record errors, clipping and placement. Distinguish this experimental path from the validated `noop` text fallback.
- [ ] Rerun `just check`, `just phase1`, `just test-tty` and `just test-kitty` on the implementation commit that completes the remaining Phase 1 integration work.
- [ ] Classify legacy/GUI test sizes truthfully without weakening current quality gates or concealing warnings.

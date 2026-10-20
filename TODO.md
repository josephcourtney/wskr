# wskr — Immediate Tasks

Unfinished Phase 1 work; see [PLAN.md](PLAN.md) and [Phase 1 evidence](docs/phase1-validation.md).

- [ ] Rerun `just check`, `just phase1`, `just test-tty` and `just test-kitty` on the latest branch, including the Rich no-op fallback regression test.
- [ ] Capture an ordinary `MPLBACKEND=wskr_kitty` plot in an actual Kitty window, noting window geometry and whether the plotted image is visible (stdout capture is insufficient).
- [ ] Characterize `RichPlot` with an explicitly selected `WSKR_PROTOCOL=kitty`; record errors, clipping and image placement. Do not treat the legacy inline-upload path as production ready.
- [ ] Complete application of terminal-derived backend-owned palette, text and artist defaults with tests that explicit rcParams/artist settings remain authoritative.
- [ ] Complete truthful test-size classification for legacy/GUI tests; retain current warning policy until classifications are verified.

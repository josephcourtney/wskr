# wskr — Immediate Tasks

Pending Phase 1 completion; [PLAN.md](PLAN.md) and [validation evidence](docs/phase1-validation.md).

- [ ] Apply measured foreground/background, default artist colors, font/cell metrics and optional palette only to backend-owned defaults, without changing Matplotlib globals or user-specified rcParams/artists.
- [ ] Add explicit-precedence and import-side-effect regression cases, including light/dark colors, palette contrast, and absent/invalid terminal responses.
- [ ] Produce and inspect a normal `MPLBACKEND=wskr_kitty` Matplotlib plot and `RichPlot` in a Rich panel/table; record placement, contrast and sizing separately from the Python-logo Kitty test.
- [ ] Run `just check`, `just phase1`, `just test-tty` and `just test-kitty` again after style changes; keep feature branch unmerged until accepted.
- [ ] Finish truthful test-size classification for legacy tests; maintain current size-enforcement policy until coverage is adequate.

# wskr — Immediate Tasks

Phase 1 validation; see [PLAN.md](PLAN.md) and [automatic evidence bundle guide](docs/phase1-evidence-bundles.md).

- [ ] From macOS, run `just check` and `just evidence` on the updated feature branch; fix observed runner lint/ty/pytest/GUI issues without hiding failures.
- [ ] Share the single run ZIP. Inspect `manifest.json`, Matplotlib/Rich/noop screenshots, reference PNGs and `matplotlib-rcparams.log` for figure sizing and theme ownership.
- [ ] Confirm window capture permissions and exact-title CoreGraphics selection. Capture failures must remain explicit; do not substitute desktop screenshots.
- [ ] Resolve observed stock Matplotlib contrast/sizing only for backend-owned defaults. Keep safe terminal color probing distinct from shared user input.
- [ ] Classify remaining legacy pytest markers accurately. Leave unsupported Rich inline graphics to Phase 2/4.

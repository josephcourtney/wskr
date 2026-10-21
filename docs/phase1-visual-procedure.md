# Phase 1 — Real-Kitty visual verification

This is a **manual graphical test**, not a replacement for `just check` or a proof obtained from exit status. Run the commands inside an actual Kitty terminal, not inside a pipe, screen recorder's text log, or a terminal emulator without Kitty graphics.

## Prepare

```bash
cd ~/code/wskr
git status --short
git fetch origin
git pull --ff-only origin feature/phase1-terminal-profile-20261020
uv sync
just check
just phase1
just test-tty
just test-kitty
```

Record the output of `git rev-parse --short HEAD`. Keep screenshot files outside the source tree or in a separate ignored output location.

## Three independent scenarios

1. Stock Matplotlib, with no `wskr` plotting calls:

   ```bash
   just visual-smoke matplotlib
   ```

   Inspect both sine/cosine lines, axis labels, legend, readable grid, figure size and whether the image stays within the visible terminal viewport. A clean exit with no stdout **does not prove pixels were shown**.

2. Rich with explicit Kitty transport (experimental):

   ```bash
   WSKR_PROTOCOL=kitty just visual-smoke rich
   ```

   Inspect the **panel and table separately** for actual plotted pixels, image placement, clipping, alignment with borders and whether text appears before or after the correct row. The old inline Kitty protocol is not yet standards-correct and may fail; record failures as observed rather than interpreting them as successful graphical output.

3. Rich's intentional text-only fallback, for comparison:

   ```bash
   just visual-smoke noop
   ```

   This mode should display `[wskr: image unavailable (no graphics protocol)]` within each Rich layout, not a plot and not raw Kitty escape sequences or out-of-band warning lines.

For an optional reference PNG and a pause suitable for screen capture:

```bash
WSKR_PROTOCOL=kitty uv run python scripts/phase1_visual_smoke.py \
  --mode rich --reference /tmp/wskr-rich-reference.png --pause
```

While the script is paused, use macOS's screenshot capture (Shift-Command-4, or `screencapture -i /tmp/wskr-rich-screen.png` from another terminal). Record the Kitty window's dimensions and theme if known. The reference PNG verifies source rasterization, **not** terminal placement.

## Evidence and acceptance

For each scenario, record the commit, `TERM`, `WSKR_PROTOCOL`, terminal rows/columns, light/dark background, observed visible image bounds, clipping, exceptions, screenshot path and whether you personally saw the image. Compare actual screenshots with the PNG reference and save the findings in [phase1-validation.md](phase1-validation.md).

The standard Matplotlib baseline and Rich transport are different paths. Kitty's passing Python-logo E2E test proves graphics transfer in its own workflow but does **not** prove Matplotlib or Rich placement. Neither the new figure-local style tests nor this smoke script prove live OSC colors are queried automatically; the default backend refuses to consume shared TTY input.

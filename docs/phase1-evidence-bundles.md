# Run-specific Phase 1 evidence

Execute from the project checkout (macOS with Kitty installed and a GUI session):

```sh
just evidence
```

This runs `just check`, `just phase1`, `just test-tty` and `just test-kitty`, then captures three **independent, uniquely titled Kitty windows**:

- standard Matplotlib (graph);
- Rich with `WSKR_PROTOCOL=kitty` (currently the expected safe inline-unavailable diagnostic);
- Rich with `WSKR_PROTOCOL=noop` (text fallback).

The command prints each check and capture state, the run-specific directory, and a single ZIP:

```text
artifacts/evidence/
  20261021T140000123456Z-abcdef1234-xxxxxx/
    manifest.json
    logs/
      matplotlib-rcparams.log
      just-check.log
      just-phase1.log
      just-test-tty.log
      just-test-kitty.log
    screenshots/
      matplotlib-reference.png
      matplotlib-screen.png
      matplotlib-kitty.log
      rich-reference.png
      rich-screen.png
      rich-kitty.log
      noop-reference.png
      noop-screen.png
      noop-kitty.log
  20261021T140000123456Z-abcdef1234-xxxxxx.zip
```

The ZIP contains only the current run's directory contents (no nested old runs). The manifest includes UTC timestamps, branch/commit/dirty state, explicit command outcomes, screenshot state, dimensions, and SHA-256 hashes. **A screenshot marked `captured_unreviewed` does not mean the graph was visibly correct.** Review the PNGs for clipping, contrast and image placement. Failed or missing screenshots retain an error in the manifest; the runner still writes the ZIP and exits nonzero.

## Permissions and isolation

The runner launches its **own Kitty window per scenario**, identifies it by an exact unique window title via macOS CoreGraphics and captures only that window with `screencapture -l`. It never substitutes a screenshot of the whole desktop or an arbitrary existing window. It closes only its own child Kitty processes.

macOS may require **Screen Recording permission** for the terminal/Kitty screenshot process and permission to enumerate window titles. If the title is hidden, the capture is reported as failed rather than selecting the wrong window. The `swift`, `kitty`, `screencapture`, `just`, and `uv` commands must be available. The utility does not require `yabai`.

Avoid running this in a headless CI session: normal static and unit checks can be collected independently:

```sh
just evidence --no-gui
```

To capture screenshots and configuration only, retaining explicit "skipped" records for validation commands:

```sh
just evidence --no-checks
```

To choose an alternate output directory: `just evidence --out /tmp/wskr-evidence`.

ZIPs can contain screenshots of terminal window content and subprocess output. **Review before sharing**; the script does not bundle environment-variable dumps or other unrelated applications' windows.

## Interpretation

- `just check`: source quality and non-GUI pytest, with skip/warning lines retained;
- `just phase1`: terminal profile, safe querying and styling regression tests;
- `just test-tty`: opt-in pseudo-terminal tests;
- `just test-kitty`: live Kitty GUI suite (can include opt-in skips);
- screenshots: recorded pixels, **not** automated semantic acceptance.

Comparison of actual graphics with reference PNGs, future dynamic theme/geometry testing and Phase 2/4 Kitty inline graphics are separate acceptance steps.

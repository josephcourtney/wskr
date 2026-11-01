# Automated native macOS owned-viewport acceptance

The automated acceptance controller launches **one isolated Kitty OS window
per test**, exercises an owned Matplotlib viewport through a separate Python
worker, and writes screenshots directly from Kitty's remote graphics service.
No interactive window selection, dialog, manual resizing, or Accessibility /
Screen Recording permission is required for Kitty's own remote screenshots.

## Run

From the `wskr` root on macOS:

```sh
just test-native-gui
```

Or run one case:

```sh
just owned-auto unmanaged 2
just owned-auto unmanaged 6
just owned-auto yabai 2
just owned-auto yabai 6
```

Each stage sends a resize command, measures the resulting screenshot, waits
for a worker redraw marker, and captures the next screenshot. Checks cover
three PNGs with shrink and expansion, visible bars, retained source figure
geometry, and restoration of the primary terminal screen. Failed cases also
produce evidence archives and error reports.

### Unmanaged Kitty

The test controls its dedicated Kitty instance through a local Unix socket:
`kitten @ resize-os-window` and `kitten @ screenshot`. The socket is unique to
the test and not exposed publicly.

### yabai-controlled floating (included in `test-native-gui`)

The controller finds the **actual** test window through `yabai -m query
--windows`, waits until yabai has a visible Accessibility reference, and
toggles **only that disposable Kitty window** to floating. Then all OS-window
resizes use `yabai -m window <ID> --resize abs:W:H`; captured physical
dimensions are verified and calibrated for Retina scaling. Its report records
`yabai_resize_policy=floating`. No Kitty resize fallback is used.

This tests that yabai is available and controls window dimensions, but **does
not establish native BSP/tiled resizing**. The initial toggling operation may
temporarily rearrange neighboring tiles, though the test does not persist
yabai configuration changes and closes its own Kitty window.

### Explicit BSP / tiled qualification (separate)

Run `just owned-auto yabai-bsp 2` or `just owned-auto yabai-bsp 6`.
These cases **never float** the window or substitute Kitty resizing.
They require a real vertical BSP split (which controls width), an adjacent
tile, and enough workspace for the requested narrow and wide viewport sizes.
The controller measures actual physical screenshot width and calibrates the
BSP child fraction, retrying up to three times rather than assuming a fixed
25% split will fit on every monitor. Each attempted ratio is recorded in the
case report.
A horizontal split changes height, not width; a single root window has no
split ratio. Unsupported layouts are reported as **SKIP** (unqualified), with
their topology and diagnostics retained in the evidence ZIP. The explicit BSP
command still exits nonzero: a skipped test is not acceptance. Genuine render,
resize-command, or pixel-verification errors are reported as **FAIL**. To
qualify BSP resizing, arrange the disposable Kitty window in a vertical split
with an adjacent tile and sufficient width before rerunning. The controller
does not rearrange existing yabai windows automatically.

The default `just test-native-gui` runs unmanaged and yabai-floating cases.
BSP tests remain separately required for any claim of tiled acceptance.

## Evidence

Outputs are written under `artifacts/phase3-owned-live-native-auto/` as
per-case `report.json`, screenshots, worker raster telemetry and ZIPs, plus a
consolidated JSON result for the test matrix.

Automation still requires macOS GUI permissions/environment sufficient to
launch and control Kitty and, for managed cases, yabai. Automated image
pixel counts cannot fully replace visual review of clipping and z-order.

## Unavailable yabai service

Check that the user-level yabai daemon is running before the managed matrix:

```sh
yabai -m query --windows
# If the socket is unavailable, start the existing service:
yabai --start-service
yabai -m query --windows
```

The `--start-service` command installs/starts a user LaunchAgent when needed.
It may prompt for Accessibility permission. Do not automatically start, stop,
or reconfigure yabai from the acceptance test itself.

The controller checks `yabai -m query --windows` before attempting a managed
case. If the executable is installed but the daemon socket cannot be reached,
managed cases are reported as **SKIP** with the exact diagnostic (not a plot
failure, and not counted as a passing matrix). The matrix exits nonzero until
all required cases pass. Start yabai in the current login session before
rerunning managed acceptance, or run `just owned-auto unmanaged 2` separately.

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

### yabai

The controller finds the **actual** test window through `yabai -m query
--windows`, not just a `yabai` label. For floating windows it uses yabai
absolute resizing. For BSP-managed windows it changes the split ratio and
checks the achieved size. If the layout cannot produce sufficient resize,
the test fails with an explicit diagnostic; it does not silently substitute
Kitty remote resizing.

The script does not modify your persistent yabai configuration. It launches
and terminates only its own Kitty instance. Tests may require a sufficiently
flexible yabai workspace; a single-window BSP layout cannot necessarily be
resized by split-ratio commands.

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

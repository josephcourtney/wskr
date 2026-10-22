# Phase 2 — Native Kitty Transport Acceptance

**Gate P2: Accepted on October 21, 2026**, against code commit `d615ec08d87d15cac770ebca669a09f81182bceb`. Phase 2 replaces external `icat` as the primary graphics path with a native PNG codec and managed placement API. This document retains exact execution evidence rather than treating terminal configuration hints as proof of support.

## Quality qualification — Ubuntu and hosted macOS

GitHub Actions [quality run 39697846003](https://github.com/josephcourtney/wskr/actions/runs/39697846003), using locked `uv` dependencies and Python 3.13:

| Required check | Ubuntu | macOS 15 |
| --- | --- | --- |
| `compileall -q src tests scripts` | PASS | PASS |
| `ruff format --check` | PASS | PASS |
| `ruff check --no-fix` | PASS | PASS |
| `ty check src tests scripts` | PASS | PASS |
| Full `pytest -q` | **229 passed, 3 skipped** | **229 passed, 3 skipped** |
| Focused Phase 2 suite | **54 passed** | **54 passed** |

Full pytest issued 138 nonfatal test-category/legacy warnings per platform. The hosted macOS run additionally exercised kernel PTY probing, foreign input preservation, negative ACKs, timeouts and terminal-state restoration. A Darwin kernel-managed `PENDIN` state bit is ignored in restoration comparisons; all other terminal attributes are compared without suppression.

## Real Kitty graphics qualification

GitHub Actions [graphical run 39697845933](https://github.com/josephcourtney/wskr/actions/runs/39697845933) executed on Ubuntu under **Xvfb with the actual Kitty terminal emulator**. Its direct `f=100` upload used the production `NativeKittyTransport`, not external `icat`. Both scenarios produced a valid reference PNG and an OS-level 1280×900 screenshot.

| Scenario | Cyan | Magenta | Yellow | Visual result |
| --- | ---: | ---: | ---: | --- |
| Native physical placement (`a=p`, `C=1`) | 2,666 pixels | 6,277 | 4,368 | **PASS** — visible complete chart |
| Native virtual placement (`U=1`, Unicode placeholders) | 1,677 pixels | 3,869 | 2,688 | **PASS** — visible complete chart |

The screenshots were **downloaded and independently viewed**; colored bars, axes and plot title are visible in both, and neither shows raw graphics escapes or literal placeholder glyphs. The screenshots also expose wrapping of the diagnostic text after the image; that is not an image transmission failure and is not represented as resolved display layout. Terminal UI/scrolling improvements remain later-phase work.

The complete [GUI evidence artifact](https://github.com/josephcourtney/wskr/actions/runs/39697845933/artifacts/12391393365) contains two screen PNGs, two reference PNGs, emulator logs, two readiness markers and raw XWD captures. Downloaded ZIP SHA-256: `adf42734fdd787ad2b31768fff8ab62ab99a7c16479c2c6f07278f395c11000d`. Screenshot SHA-256 values:

- Physical: `e2a2738097d88a84a154d3523b03c2f52474057ec366c93484fe51d30f2f6018`
- Virtual: `07a6088eb2575aa968fcf4cea0665b3d8d727e62f043c4bcc68a202b49455c7d`

The separate hosted workflow was subsequently made **mandatory rather than exploratory**; its post-change run must also be green before merging, with the same visual assertions and no change to production Python code.

## Acceptance boundaries

Gate P2 requires protocol round-trip tests, simulated acknowledgments, direct transmission in real Kitty and no graphics escaping into redirected streams. These are satisfied by the full/test-focused suites plus the two independently inspected real-emulator screenshots.

The tests additionally cover the 4096-byte chunk bound, image and placement IDs, virtual 24-bit SGR placement identity, upload, replacement, scoped delete, cleanup, foreign ACK forwarding, negative acknowledgments and the real POSIX PTY. The portable isolated 23-test source-hash validation was useful during initial construction but is superseded by the complete hosted checks.

**Not claimed:** graphical validation in Kitty on macOS; real inline Rich panels/tables; full interactive Matplotlib resize, cursor/lifecycle correctness or explicit-style display fitting; visual cleanup during scrollback. The macOS job tests the transport and PTY, not GUI. Phase 3 owns Matplotlib lifecycle, viewport/clipping and contrast; Phase 4 owns Rich `ConsoleOptions` and actual inline placeholder composition. Phase 2 provides the shared transport and virtual-placement primitives without falsely advertising `supports_inline_placement=True`.

## Independent native macOS Kitty acceptance — October 21, 2026

**Local evidence:** `20261022T004859842696Z-dc3306bd7c-677857.zip`; generated 2026-10-22 00:48:59–00:50:06 UTC (October 21, US Eastern). Bundle submitted and independently inspected. Exact **clean** checkout: `main` at merge commit `dc3306bd7c6f80ea2213faf14b37808ac5bbdd34`, macOS 27.0.1 arm64, Python 3.14.0, `TERM=xterm-kitty`, `COLORTERM=truecolor`. All **21/21 manifest SHA-256 values match their archive members**; the archive contains 22 members including the manifest.

| Local check | Independently verified result |
| --- | --- |
| `just check` | **PASS:** compileall, Ruff format (96 files), Ruff lint, `ty`, full pytest **229 passed, 3 skipped, 138 nonfatal warnings** |
| `just phase1` | **PASS:** 55 passed, 1 skipped |
| `just phase2` | **PASS:** 54 passed (26 nonfatal marker warnings) |
| `just test-tty` | **PASS:** 35 passed |
| `just test-kitty` | **PASS:** 5 real-Kitty tests passed |
| Screenshots | **5/5**, uniquely scoped owned Kitty windows, **1664×952 px** each; all captured and manually inspected |

**Visual observations:**

- **Native physical placement:** the PNG bar chart is visibly delivered through the direct Kitty transport; cyan, magenta and yellow bars appear correctly without raw escape sequences. The small reference's title is already clipped at its upper edge; this is not evidence of failed transport.
- **Native Unicode virtual placement:** `U=1` plus placeholder text visibly resolves to the bar chart with the same three colors; no literal placeholder glyphs. Its content fits in the allocated region with no incorrect adjacent-cell overwrites evident in the capture.
- **Rich with Kitty selected:** `Kitty inline placement unavailable (experimental transport)` is contained correctly within both the panel and table. Rich still does **not** display images inline, by design until Phase 4.
- **Rich noop:** `image unavailable (no graphics protocol)` remains correctly contained within the panel and table.
- **Matplotlib native display (window-manager confounded):** graphics upload succeeds, but the captured **1664×952** window shows roughly the lower half of a complete **1800×1800** reference image (configured `figsize=[6,6]`, `dpi=300`). **Subsequent user clarification:** yabai was active and changed the Kitty window's shape during this test, explaining why only the lower portion appeared. Accordingly this screenshot **does not establish an intrinsic wskr figure-sizing, placement, or lifecycle defect**, and must not be labeled a verified code regression. The captured presentation was incomplete under those changed window conditions. Whether wskr should respond to an external window-manager resize, and whether an unmanaged window can display the complete figure, require controlled Phase 3 comparisons.
- Kitty diagnostics include unknown `clear_all_in_scrollback` / `hide_single_tab` configuration keys and nonfatal OpenGL/uniform warnings. Tests and graphics rendering succeeded despite them. Remove stale options from the test-only Kitty configuration during Phase 3 test-harness maintenance; do not infer they are valid for this version of Kitty.

**Disposition:** This is direct *macOS* graphical corroboration of Gate P2, supplementing prior hosted Linux/Xvfb graphics and hosted macOS PTY/quality tests. **Phase 2 remains accepted.** The local archive's tested SHA is the exact merge commit `dc3306b`. The user identified **yabai-managed Kitty geometry changes** as the cause of the lower-half screenshot; do not cite this image as confirmation of a wskr clipping regression. For Phase 3, compare *unmanaged/stable-window* and *yabai-managed/resized* scenarios, recording initial geometry, post-resize geometry and image placement. Retain ADR-002's prohibition on silently modifying caller-owned Matplotlib rcParams. This clarification changes the interpretation of the original evidence, not its checksums or test outcomes.

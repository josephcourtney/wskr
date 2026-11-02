# Native P3 yabai automation (experimental)

This opt-in controller runs the **existing** P3 Kitty acceptance harnesses without
manual yabai setup, window-picker dialogs, manual n/p/Enter, or theme switching.
No renderer defaults or normal test entrypoints change.

## Requirements and invocation

Native macOS with a running yabai daemon able to create, focus and destroy
spaces, accessible Kitty and `screencapture`, and macOS Screen Recording
permissions. The test must be allowed to take focus and create a disposable
space. Do not run it while a critical desktop task must retain focus.

```sh
git switch feature/p3-native-yabai-automation-20261102
uv sync
just check

# One unattended zero-history history-anchor resize
just native-auto unmanaged resize 2
just native-auto floating resize 6
just native-auto bsp paging 2
just native-auto float-space appearance 2

# Full 4-state by 5-scenario suite, stopping at first failure
just native-auto-matrix
```

The CLI accepts `--state unmanaged|floating|bsp|float-space`,
`--case resize|paging|lifecycle|appearance`, and `--height 2|6`.
Paging always requires an actual change in measured page capacity.

## Isolation and evidence

1. Query the initially focused yabai space and record its stable UUID.
2. Create a separate disposable space, label it uniquely, set BSP or float
   layout, and register a precisely matched temporary Kitty rule.
3. Start a new Kitty OS process with a fixed unique title and a short,
   private Unix control socket, then identify its exact yabai window ID.
   Remove the rule immediately after identification.
4. Verify window title/app, selected space, floating state and that no
   unrelated window occupies the new space. `unmanaged` is established
   by `manage=off`; `floating` is explicitly toggled from a managed
   BSP window; `bsp` stays tiled; `float-space` uses a float-layout
   space. The rule command and snapshots provide independent provenance.
5. Drive floating-window size with yabai `window --resize abs`. On BSP,
   change padding **only in the newly created empty test space**, using
   the original frame size to choose progressively narrower geometries.
   Read actual Kitty geometry in the existing harness; never infer that
   requested pixels were reached.
6. Use a dedicated Kitty remote-control socket to deliver canonical
   n/p/blank input, never read keyboard bytes from the plotting child.
   Set explicit dark/light foreground/background colors on that Kitty
   window only. Capture its macOS window ID directly via `screencapture -l`.
7. Let the real harness complete, then display a clean interactive zsh
   prompt. Require both worker-exit and prompt markers via Kitty `get-text`,
   capture the returned shell, copy the unambiguous original harness ZIP,
   and bundle with yabai commands, snapshots and the controller report.
8. Terminate only the owned Kitty process, restore original space focus,
   destroy the disposable space, and remove the private remote socket.
   Cleanup failures cause a failed acceptance report.

The ZIP is under `artifacts/phase3-native-yabai/`. If the daemon lacks
space-creation capability, if a window is misidentified, if a permission is
missing, or if image capture fails, the run must fail rather than advertise
an unverified result. The manual test recipes remain available.

## Verification boundary

The controller has portable tests for state predicates, exact window identity,
GUI checkpoint dispatch, worker argv and the atomic request protocol.
**A real automated macOS/yabai/Kitty run and independent screenshot review
are still required before claiming any automated scenario passed.**
This framework does not establish universal viewport pinning, replace all
manual visual inspection, or validate unattended IPython/pandas REPL behavior.
Full test commands must pass on the feature branch before merge.

Current manual evidence and remaining acceptance limits:
[Phase 3 macOS acceptance](phase3-native-macos-acceptance.md),
[STATUS](../STATUS.md) and [TODO](../TODO.md).

## Recovery after the November 2 initial automated runs

The first four native runs (and the matrix's first attempt) created new
spaces but used the invalid `yabai -m space <label> --focus` form.
Those runs failed **before Kitty launched**, and their cleanup also used
incorrect action/selector ordering. They may have left empty spaces labelled
`wskr-p3-*` on the user's desktop.

To inspect without modifying the desktop:

```sh
yabai -m query --spaces |
  jq '.[] | select((.label // "") | startswith("wskr-p3-")) |
      {index, label, uuid, windows}'
```

Only after confirming each named space is a disposable, unoccupied test space,
remove it by its **unique label** using the supported command form:

```sh
yabai -m space --destroy '<exact-wskr-p3-label>'
```

The fixed controller also uses `space --focus <label>`,
`space --focus <index>`, and `space --destroy <index>`.
It resolves UUIDs again at cleanup and refuses to destroy a space that
contains any windows. This guards against affecting unrelated desktop work.

The November 2 user validation on the earlier controller commit stopped at
formatting/lint (18 remaining lint diagnostics), then hit the invalid space
focus form for each native case. None of those ZIPs demonstrates rendering
or acceptance. The subsequent commits refactor the controller to satisfy
those static checks, add command-order regression tests, and require a fresh
`just check` followed by real native execution before signoff.

If `just fix` changed the local working tree, inspect and preserve those
modifications before fetching/resetting/switching branches. Do not blindly
discard uncommitted work.

## Follow-up native failure: transient Kitty window identity

The next native run (`20261102T144124Z-unmanaged-resize-2.zip`) passed
space creation and launched Kitty, but the freshly discovered yabai window
ID 7225 could not be resolved by the separate targeted
`query --windows --window 7225` request. This was observed immediately
after the list query found the title, before any plot was qualified.
The first check after the conflicting-autostash recovery also had two
remaining Ruff cleanup diagnostics; the controller now extracts its
owned-space occupancy guard so the cleanup functions remain lintable.

A similar upstream yabai issue documents window-list entries that do not yet
have an Accessibility reference and fail targeted ID operations. The
controller therefore:

- Waits for **two consecutive**, matching yabai ID/PID snapshots with
  `has-ax-reference` not explicitly false.
- Uses the **full list query** to locate the bound window thereafter, checking
  app, PID, window ID and isolated space. A changed terminal title does not
  silently rebind the controller to another window.
- Records the startup snapshots, any missing-ID candidates and
  `kitty-launch.log` in the evidence ZIP to distinguish a disappearing Kitty
  process from delayed yabai Accessibility registration.
- Fails rather than selecting another ID when the owner disappears.

No native run with this repair has yet been reviewed. The previous failing
ZIP is diagnostic evidence, not a passing test.

**Dirty worktree guidance:** `just fix` can leave local modifications that
conflict with a remote fast-forward, triggering Git's autostash conflicts.
Prefer an independent verification worktree rather than discarding changes:

```sh
git fetch origin
git worktree add --detach ../wskr-yabai-verify-20261102 \
  origin/feature/p3-native-yabai-automation-20261102
cd ../wskr-yabai-verify-20261102
uv sync
just check
just native-auto unmanaged resize 2
```

Attach the new `artifacts/phase3-native-yabai/...zip` when a native failure
persists; it now contains the controller report, startup log and any
completed nested harness evidence.

## First complete unattended Kitty run — November 2, 2026

User-supplied controller ZIP: `20261102T145739Z-unmanaged-resize-2.zip`,
run in a detached verification worktree at `39fcfb0` on macOS 27.0.1.
Both the controller and nested harness reports, all five window screenshots
and the returned-prompt screenshot were inspected.

- **Automated setup and cleanup pass:** uniquely titled Kitty OS window
  ID 7419, PID 12014, internal Kitty ID 1, with working AX reference.
  Verified requested `unmanaged` state as floating window in a BSP space,
  with the explicit `manage=off` launch rule. Original window frame
  1200×760, narrowed to 620×410 and restored to 1200×760. The controller
  restored the previous space (index 4), destroyed its owned space (index 5),
  and recorded no cleanup failures.
- **Rendering/transport pass under existing thresholds:** nested harness
  `passed_protocol_checks=true`, `visual_failures=[]`. Source rasters
  900×200 → 609×135 → 900×200; red and blue bars remained visible after
  redraw, expansion and child exit.
- **Returned prompt pass:** Kitty `get-text` captured both
  `WSKR_NATIVE_AUTO_EXIT:0` and the actual `WSKR_NATIVE_AUTO_PROMPT>`.
  The controller also captured a full window-only screenshot of that prompt.
- **Visual limitation:** The screenshots show the title/upper figure content
  partly out of the visible top edge. This is **not detected** by the bar
  pixel-count checks. Whether the transmitted Matplotlib PNG is already
  clipped or Kitty places an intact PNG outside the visible window remains
  unproven. The native resize harness now writes exact
  `transmitted-frame-N.png` files to subsequent evidence ZIPs so that a
  source/capture comparison can distinguish those mechanisms.

Thus this run qualifies the tested **window automation, redraw persistence
and post-harness shell restoration**, but not complete illustration/title
visibility. The initial version of `just check` stopped at a single Ruff
`magic-value-comparison` diagnostic in the controller after `just fix`;
a named stable-window sample threshold addresses that check. Formatting and
the full suite require a fresh run on the latest branch head. The floating,
BSP, float-space, tall-figure, paging and appearance scenarios remain
pending native verification.

## Native AX-registration regression — November 2, 2026, 15:16 UTC

A clean detached worktree at `5513b17` failed `just check` at two
Ruff-format differences, then `just fix` found only the
`magic-value-comparison` warning for the two-sample threshold
(subsequently replaced with a named constant). The unattended unmanaged
9×2 run then failed to establish a yabai AX reference after its full
window-registration deadline: test window 7598, Kitty PID 32467, located
on space index 2, remained `has-ax-reference=false` in all reported
observations. **No plotting acceptance occurred on this run.**

Yabai documents that no-AX windows can appear in `--windows` results
but cannot be safely manipulated via ID-based commands, particularly
when their space is inactive. Therefore the harness must **not** simply
ignore this flag for unmanaged windows.

An intermediate controller revision verified the newly created space's
focused UUID and attempted Kitty `focus-window` through the private
socket. This strategy is now **superseded**: subsequent native evidence
showed that the Kitty focus command can switch macOS back to the
original space without repairing yabai's AX reference. The final section
below describes the replacement. The AX prerequisite for yabai window
resizing remains unchanged.

This recovery strategy still requires a native run. An `unmanaged`
window's floating state is **not itself evidence** that a missing AX
reference is harmless or that geometric window actions can succeed.

## Third native attempt — November 2, 2026, 15:31 UTC

Evidence: `20261102T153127Z-unmanaged-resize-2.zip`, detached
worktree `c942769`. The archive's `controller.json` records the precise
cause: the initial `space --focus <test-label>` command succeeded and
subsequent `query --spaces --space` returned the owned space as
`has-focus=true`. On initial Kitty AX recovery, the controller issued the
same `space --focus <test-label>` command again. Yabai rejected that
redundant request with `cannot focus an already focused space`.
No plot was tested; cleanup restored the previous space and removed the
test space, with no orphan indicated.

The controller now uses an **idempotent owned-space focus procedure**:
query the focused UUID first; do not issue focus if already owned;
if a focus call races with an external state change, accept yabai's
specific already-focused error only after querying the active UUID again.
Other errors and focus of an unrelated space remain failures.
Regression tests cover those cases.

The user's `just check` on `c942769` stopped on two formatter
differences. After `just fix`, Ruff reported a separate
`too-many-statements (52 > 50)` in the native resize plotting worker
after addition of transmitted-PNG evidence. The recording code now
extracts raster validation and exact PNG preservation into a helper,
retaining the checks while reducing worker complexity.

A full subsequent `just check` and real native run are required to
verify both changes. Do not mark this failed ZIP as a native acceptance pass.

## Fourth native attempt — November 2, 2026, 15:41 UTC

User log from detached worktree at `22f78fd`:

- `just fix`: two Ruff format changes; Ruff lint then **passed**.
- `just check`: syntax, formatter, Ruff lint, `ty`, and
  **466 tests passed; 3 skipped**. Test category and `forkpty`
  deprecation warnings remained nonfatal. These results apply to the
  **locally formatted** tree, not automatically to later remote commits.
- `just native-auto unmanaged resize 2`: **failed before plotting**.
  Test Kitty OS window 7885, PID 56541, space index 5 stayed
  `has-ax-reference=false` despite a bounded focus-recovery attempt.
  Focus observations show an active original space index 4, then active
  owned space index 5, followed by **focus back to original space 4**
  after the Kitty remote `focus-window` recovery. The controller
  continued refusing yabai window actions, correctly preventing a
  false-positive qualification.

The replacement recovery deliberately **never calls**
`kitty @ focus-window` to repair AX. It switches through the two
recorded yabai Space UUIDs (original and owned), waits for actual
macOS focus transitions, and then retries the two-consecutive
AX-ready window observations. When the original space is currently
active, it switches directly to the owned space. Only this one
bounded recovery is attempted, with no unrelated window resizing,
global yabai configuration changes, or success assertion when AX
remains unavailable. Unit regressions cover these transitions.

Native validation is still needed to determine whether the deliberate
Space activation repairs AX registration. The first 9×2 automation
pass and its unresolved apparent figure-title clipping remain separate
evidence; a successful AX recovery is **not yet established**.

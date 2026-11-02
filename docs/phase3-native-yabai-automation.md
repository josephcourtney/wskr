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

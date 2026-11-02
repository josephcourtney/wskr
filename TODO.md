# wskr — Immediate tasks

Only pending work. See [STATUS.md](STATUS.md) for accepted behavior, [PLAN.md](PLAN.md) for phase sequencing and [DESIGN.md](DESIGN.md) for requirements.

## P3 — remaining qualification

- [ ] **History anchoring, [#31](https://github.com/josephcourtney/wskr/issues/31):** Independently attest unmanaged/yabai mode, inspect actual shell prompt **after the outer command returns** for both zero-history shapes, and review the existing 9×2 unmanaged 96-line ZIP if supplied. The two Unicode zero-history screenshot sequences passed, but do not justify changing the physical-anchor default or advertising viewport pinning.
- [ ] **Blocking paging capacity:** Run `just native-paging-capacity unmanaged` and resize until measured page capacity actually changes; verify the new `plan_sheet_pages` capacity, `n`/`p` ordering and fitted rasters, and capture the returned shell prompt. The existing eight-stage visual run held capacity at four figures per page.
- [ ] **Cooperative shell integration:** Validate the opt-in `%load_ext wskr.render.matplotlib.ipython` post-cell pump with real interactive IPython/pandas and standard Python REPL in native Kitty. Verify `plt.ion()`, multi-figure redraw, `%unload_ext` and no foreign stdin reads; the portable host-dispatcher tests alone do not qualify an actual interactive shell.

- [ ] **Native yabai controller qualification:** The first unattended `unmanaged resize 2` run passed controller/transport checks, independent state/cleanup verification and returned zsh prompt, but its screenshots show partially missing upper chart/title content. Re-run on the latest branch with exact transmitted PNG receipts to localize that defect. Then qualify `floating resize 6`, `bsp paging 2`, `float-space appearance 2`, and the fail-fast full matrix. The v3 worktree passed `just check` at `22f78fd` after `just fix` (466 passed, 3 skipped); the next head failed one regression detecting a duplicate focus command (469 passed, 3 skipped). Requalify the fixed branch and run native afterward. Diagnose persistent missing yabai AX references and verify the one-shot actual Space activation recovery before running the rest of the matrix. Preserve manual fallback.

## Next implementation boundary

- [ ] After P3 gates, scope Phase 4 Rich inline Kitty panel/table rendering and Phase 5 dependency and stub cleanup separately, without advertising either as implemented.

For each code change run `just check` and relevant PTY/wheel tests. For native signoff inspect actual Kitty screenshots; an evidence ZIP or protocol-level pass alone is insufficient.

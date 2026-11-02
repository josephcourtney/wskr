# wskr — Immediate tasks

Only pending work. See [STATUS.md](STATUS.md) for accepted behavior, [PLAN.md](PLAN.md) for phase sequencing and [DESIGN.md](DESIGN.md) for requirements.

## P3 — remaining qualification

- [ ] **History anchoring, [#31](https://github.com/josephcourtney/wskr/issues/31):** Run opt-in `WSKR_KITTY_ANCHOR=unicode` with *zero* seeded lines at 9×2 and 9×6; review complete screenshot ZIPs for both layouts and independently attest unmanaged/yabai mode. Inspect shell prompt **after the outer command returns**. Review the existing 9×2 unmanaged 96-line ZIP if supplied. Do not change the default physical anchor without broader signoff.
- [ ] **Blocking paging capacity:** Exercise a native resize that changes the measured `plan_sheet_pages` page capacity, verify `n`/`p` order and fitted rasters, and capture the returned shell prompt. The existing eight-stage visual run held capacity at four figures per page.
- [ ] **Cooperative shell integration:** Test standard `plt.ion()`, `draw_idle()`, `flush_events()` and pandas plotting in real IPython/REPL loops. Specify the host event-pump contract without stealing stdin or claiming unattended redraw.
- [ ] **Appearance:** Qualify owned runtime font/color/opacity queries and `refresh_theme` against light/dark native Kitty; inspect title/tick/label contrast while preserving explicit artist colors. Distinguish live-owned changes from immutable historical PNGs.

## Next implementation boundary

- [ ] After P3 gates, scope Phase 4 Rich inline Kitty panel/table rendering and Phase 5 dependency and stub cleanup separately, without advertising either as implemented.

For each code change run `just check` and relevant PTY/wheel tests. For native signoff inspect actual Kitty screenshots; an evidence ZIP or protocol-level pass alone is insufficient.

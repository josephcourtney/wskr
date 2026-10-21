# Phase 2 native Kitty acceptance

**Status:** Implemented on `feature/phase2-native-kitty-20261021`, **not yet qualified on macOS**. No live Kitty transmission, screenshot or PTY output is claimed to pass. The previous Phase 1 acceptance applies only to commit `5e35aa6`.

## Scope

- `kitty_codec.py`: PNG `f=100` encoded as Base64 in ≤4096-byte chunks, proper first/continuation/final `m` framing, `q=2` quiet operation, physical and virtual placement `a=p`, scoped `a=d` deletion, and ACK parsing.
- `kitty_io.py`: bounded transaction writer and explicitly caller-owned capability query, serialized across instances, safe refusal on redirected stdout, restoration of terminal attributes and forwarding of unrelated input.
- `kitty_native.py`: explicit image/upload/physical-placement/virtual-placement/delete/close lifecycle, random 32-bit identities, no global deletes and a `probe()` method that requires input ownership. The `kitty` registry and stock `wskr_kitty` backend now select the native transport. Legacy `KittyTransport` / `kitty_legacy` remains available for comparison.
- `kitty_placeholders.py`: protocol-owned Unicode U+10EEEE, high-byte/image-ID and underline placement-ID encoders with explicit row/column diacritics. The Rich adapter remains fallback-only until Phase 4; `supports_inline_placement=False` is intentional.
- `just phase2` and the evidence collector: run the dedicated pure/compatibility tests and record them alongside full quality checks and actual Kitty screenshots.

## Required macOS qualification

1. Check out the latest branch in a clean macOS Kitty environment; run `uv sync`, `just check`, `just phase2` and `just test-tty`. Full `ty`, Ruff and pytest must pass.
2. Run `just evidence`. It now collects `just check`, `just phase1`, `just phase2`, `just test-tty`, `just test-kitty`, and five independent window-scoped screenshots. Preserve the complete ZIP even on failure.
3. Confirm the standard Matplotlib window is drawing with **direct** `f=100` packets (not external `icat`), and that the two Rich modes still show their correct explicit fallback messages. Compare live output to reference PNGs and inspect clipping, contrast and image placement. A screenshot's existence alone is not proof of correct graphics.
4. Test the ACK and negative-ACK paths on an exclusively owned PTY/foreground Kitty session. A normal REPL must not have bytes stolen or receive raw ACK sequences when ownership cannot be established.
5. Verify redirect and non-Kitty terminal refusal; test placement replacement and scoped deletion in a real terminal. Simulated ACKs alone do not prove terminal semantics.
6. Record exact commit, OS/Python/Kitty versions, screenshots, logs, and SHA-256 manifest. Do not merge until the checks and observed direct-Kitty behavior meet Gate P2.

## Known deferred limitations

Phase 3 handles interactive `show()` lifecycle, figure/user style ownership at display-time, redraw/replacement across resize, scrollback cleanup, and the existing clipping/contrast defects. Phase 4 will connect the already available upload and virtual-placement primitives to Rich's `ConsoleOptions` sizing and text layout. Do not label current Rich fallback messages as working inline graphics. Runtime Kitty support can be confirmed via explicit `probe(owns_input=True, on_unmatched=...)`; a `TERM=xterm-kitty` hint is not, by itself, a validated capability.

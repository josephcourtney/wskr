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
3. Confirm the standard Matplotlib window is drawing with **direct** `f=100` packets (not external `icat`), and that the two Rich modes still show their correct explicit fallback messages. Also inspect **native-physical** (ordinary placement) and **native-virtual** (`U=1` plus Unicode placeholders) against their distinct high-contrast reference PNGs: both must visibly show the source graphic rather than control bytes or placeholder glyphs. Compare clipping, contrast, placement and image extent. A screenshot's existence alone is not proof of correct graphics.
4. Test the ACK and negative-ACK paths on an exclusively owned PTY/foreground Kitty session. A normal REPL must not have bytes stolen or receive raw ACK sequences when ownership cannot be established.
5. Verify redirect and non-Kitty terminal refusal; test placement replacement and scoped deletion in a real terminal. Simulated ACKs alone do not prove terminal semantics.
6. Record exact commit, OS/Python/Kitty versions, screenshots, logs, and SHA-256 manifest. Do not merge until the checks and observed direct-Kitty behavior meet Gate P2.

## Known deferred limitations

Phase 3 handles interactive `show()` lifecycle, figure/user style ownership at display-time, redraw/replacement across resize, scrollback cleanup, and the existing clipping/contrast defects. Phase 4 will connect the already available upload and virtual-placement primitives to Rich's `ConsoleOptions` sizing and text layout. Do not label current Rich fallback messages as working inline graphics. Runtime Kitty support can be confirmed via explicit `probe(owns_input=True, on_unmatched=...)`; a `TERM=xterm-kitty` hint is not, by itself, a validated capability.

## Independent portable validation — October 21, 2026

The Phase 2 native implementation was reconstructed in the available Linux environment and four **exact source modules** plus the original combining-character table were verified against the GitHub blob SHA of the Phase 2 branch:

| Source file | Verified Git blob SHA |
| --- | --- |
| `src/wskr/protocol/kitty_codec.py` | `afd31301aaf939cb8539f6cb17b8695308040762` |
| `src/wskr/protocol/kitty_io.py` | `b88998edade088d7b9d68e4d864e5087a038528b` |
| `src/wskr/protocol/kitty_native.py` | `2d0db2313b5ce387fef7e17b205e409b9f638045` |
| `src/wskr/protocol/kitty_placeholders.py` | `81df4b5250161e2c81138fc2133332010a1d30c1` |
| `src/wskr/protocol/rowcolumn-diacritics.txt` | `abe6f665b454208e291a977d2eb3128a07414e61` |

**Environment:** Python 3.13.5, Linux x86-64, glibc 2.41, pytest and Pillow installed. These modules used narrowly scoped dependency stubs for `ImageProtocol`, the geometry reader, the placeholder ID constant and transport exceptions. No substitution of codec, I/O, image manager, placeholder source or the 297-character diacritic table occurred. The isolated harness is distinct from the repository's configured `just check`.

**Executed:** `PYTHONPATH=src pytest -q -p no:cacheprovider tests/test_isolated_codec_io.py tests/test_isolated_manager.py` → **19 passed in 0.15s**; `python -m compileall -q src tests` → **exit 0**. Specific cases covered PNG Base64 roundtrips on two lengths, chunk bounds, `f=100` headers and scoped physical/virtual/delete framing; a real Linux PTY writer, stdout TTY binding, foreign ACK/unmatched input forwarding, positive and negative ACKs, interrupted/incomplete-response deadline handling and exact termios restoration; image upload, replacement, scoped deletion, failed-writer rollback, 24-bit virtual ID bounds, direct display, managed transport ownership and injected capability probe; plus four cross-range virtual-placeholder color/coordinate cases and invalid placeholder boundaries.

The newly committed `tests/test_kitty_pty_transactions.py` incorporates the corresponding portable PTY regressions, and `just phase2` includes that file. The exact repository tests have **not** been executed here because the full GitHub checkout/dev toolchain cannot be retrieved; the isolated tests above are not a substitute for a full `just check`. Ruff and `ty` are unavailable in this environment, and no Kitty emulator/GUI is present. The source-code branch therefore remains in **draft PR #18**, without a false P2 signoff. The former user-host validation request is not required for continued implementation work.

An additional repository fix binds graphics I/O to the actual stdout TTY path (`os.ttyname(sys.stdout.fileno())`) instead of opening a potentially different `/dev/tty`. The portable PTY test verifies that behavior on Linux. The implementation was also compared to upstream Kitty protocol documentation for `f=100`, `m`, `a=q`, `a=p`, `U=1`, `a=d`, ACKs and explicit row/column Unicode placeholders.

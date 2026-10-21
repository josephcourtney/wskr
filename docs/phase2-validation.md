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

**Scope and environment.** Python 3.13.5, Linux x86-64, glibc 2.41. A narrow package harness reconstructed the exact GitHub versions of the native codec, TTY I/O, image manager, Unicode placeholder encoder, diacritic resource, GUI smoke script and smoke tests. Local dependency stubs provide `ImageProtocol`, structured transport errors and terminal-geometry lookup, because the complete GitHub checkout and dev toolchain are unavailable. Those stubs are not evidence for the corresponding real package modules.

| Git-verified source | Blob SHA |
| --- | --- |
| `src/wskr/protocol/kitty_codec.py` | `ea22a4c85f315e17639a697921bd070481a09899` |
| `src/wskr/protocol/kitty_io.py` | `de9c57eb6866db15444f9559c2d1eeb2a59275df` |
| `src/wskr/protocol/kitty_native.py` | `c242af6339cead2aa6e397bc48b572b8dd4979f9` |
| `src/wskr/protocol/kitty_placeholders.py` | `d6db7fa0d876b805937ab3edf7b2caaf59cc88e7` |
| `src/wskr/protocol/rowcolumn-diacritics.txt` | `abe6f665b454208e291a977d2eb3128a07414e61` |
| `scripts/phase2_visual_smoke.py` | `d9e7caa633353de0eccf3c01f51a499d19a7075d` |
| `tests/test_phase2_visual_smoke.py` | `a2e20b8a0ce2197642d977e54befa667d100b2b8` |
| `tests/test_kitty_native_pty_integration.py` | `039b7349e04d94068d242db0d45a85a0c123d789` |

**Executed (portable isolated harness):**

```sh
PYTHONPATH=src:. pytest -q -p no:cacheprovider \
  -o  \
  tests/test_isolated_codec_io.py tests/test_isolated_manager.py \
  tests/test_isolated_placeholders.py tests/test_phase2_visual_smoke.py \
  tests/test_kitty_native_pty_integration.py
python -m compileall -q src scripts tests
```

The configured local pytest marker override simply registered the `small` and `medium` names; it was not the repository's original `pyproject.toml` configuration. **23 passed in 0.47 seconds; compilation exited 0.** The first three `test_isolated_*.py` files are a disposable local harness, not committed repository tests. The last two are exact GitHub test files. A separately committed real-PTY regression suite, `tests/test_kitty_pty_transactions.py`, has not been executed verbatim in this environment, although equivalent kernel-PTY behaviors have been covered by the local harness.

**Covered:** PNG/Base64 roundtrip and 4096-byte chunk limits; valid `f=100` and `a=p`/`a=d` framing; partial and negative ACKs; forwarding foreign TTY bytes and restoring termios; stdout-bound TTY selection; no binary PNG leakage; managed image upload, placement, replacement and scoped disposal; image/placement collision bounds; virtual placeholders with 32-bit image and 24-bit placement IDs; and GUI-smoke script reference/ready-marker behavior under a fake transport. The new exact `tests/test_kitty_native_pty_integration.py` generated a valid Pillow PNG, sent native transport bytes through an actual Linux PTY, reconstructed and decoded the upload, and checked `U=1` placement and `a=d` cleanup without a GUI.

**Additional code review/fix:** New exception raises were normalized to use message variables, matching the repository's strict `EM` lint selection. After the changes, all four updated source files passed Git blob identity verification and all 23 portable tests were rerun. The writer was fixed to use the actual stdout TTY path rather than potentially targeting an unrelated controlling terminal.

**Not executed:** `just check` over the complete repository, Ruff format/lint, `ty`, all original tests, real Kitty/GUI screenshots or actual emulator image placement. No P2 signoff is claimed; [draft PR #18](https://github.com/josephcourtney/wskr/pull/18) remains unmerged. The former user-machine validation requirement does not block additional independent development.
markers=small: small\nmedium: medium' \
  tests/test_isolated_codec_io.py tests/test_isolated_manager.py \
  tests/test_isolated_placeholders.py tests/test_phase2_visual_smoke.py \
  tests/test_kitty_native_pty_integration.py
python -m compileall -q src scripts tests
```

The configured local pytest marker override simply registered the `small` and `medium` names; it was not the repository's original `pyproject.toml` configuration. **23 passed in 0.47 seconds; compilation exited 0.** The first three `test_isolated_*.py` files are a disposable local harness, not committed repository tests. The last two are exact GitHub test files. A separately committed real-PTY regression suite, `tests/test_kitty_pty_transactions.py`, has not been executed verbatim in this environment, although equivalent kernel-PTY behaviors have been covered by the local harness.

**Covered:** PNG/Base64 roundtrip and 4096-byte chunk limits; valid `f=100` and `a=p`/`a=d` framing; partial and negative ACKs; forwarding foreign TTY bytes and restoring termios; stdout-bound TTY selection; no binary PNG leakage; managed image upload, placement, replacement and scoped disposal; image/placement collision bounds; virtual placeholders with 32-bit image and 24-bit placement IDs; and GUI-smoke script reference/ready-marker behavior under a fake transport. The new exact `tests/test_kitty_native_pty_integration.py` generated a valid Pillow PNG, sent native transport bytes through an actual Linux PTY, reconstructed and decoded the upload, and checked `U=1` placement and `a=d` cleanup without a GUI.

**Additional code review/fix:** New exception raises were normalized to use message variables, matching the repository's strict `EM` lint selection. After the changes, all four updated source files passed Git blob identity verification and all 23 portable tests were rerun. The writer was fixed to use the actual stdout TTY path rather than potentially targeting an unrelated controlling terminal.

**Not executed:** `just check` over the complete repository, Ruff format/lint, `ty`, all original tests, real Kitty/GUI screenshots or actual emulator image placement. No P2 signoff is claimed; [draft PR #18](https://github.com/josephcourtney/wskr/pull/18) remains unmerged. The former user-machine validation requirement does not block additional independent development.

# ADR-004: Explicitly owned viewport sessions for live terminal plots

- **Date:** 2026-10-25
- **Status:** Accepted for experimental Phase 3 API; native visual qualification pending
- **Decision scope:** Foreground terminal ownership, history-versus-viewport placement

## Context

Kitty attaches ordinary nonblocking Matplotlib graphics to terminal text history. A controlled native macOS A/B (0 versus 96 seeded lines) showed that a correctly resized figure can leave the visible viewport when the terminal contracts and its history reflows. The pixels and image identities survive; re-expansion can restore visibility. The backend has no right to move a shell prompt or re-anchor an image into a viewport that another program owns.

The existing `show(block=True)` path demonstrates a different, viable boundary: a foreground process can explicitly take the alternate screen, render fitted figures, repaint them as its terminal resizes, and restore the previous screen on exit.

## Decision

Retain ordinary `show(block=False)` and `show(block=None)` as historical inline output. Never reinterpret `WSKR_FIT=contain` as a request to pin history output to the viewport.

Offer a separate, **explicitly foreground-owned** session:

```python
from wskr.render.matplotlib.live import owned_viewport

with owned_viewport(fig) as screen:
    screen.refresh()      # After mutating the figure
    screen.poll_resize()  # When the application pumps its own loop
```

- The session must have foreground stdin and stdout on the same TTY and valid measured geometry, with `WSKR_FIT=contain`.
- One process-wide live-viewport session owns an alternate screen at a time. Nested or background sessions fail before emitting graphics. The scope restores the previous screen and releases its transport on ordinary exit or failure.
- Rendering uses the existing Agg and fitted PNG machinery but paints at the viewport origin rather than attaching images to historical text. It never modifies source `figsize`, DPI or Matplotlib exports.
- The caller owns the application loop: `refresh()` explicitly sends changed artists; `poll_resize()` performs debounced geometry checks. No hidden polling threads, input reads, signal handlers, remote-control privileges or global rcParams changes.
- Image transport and layout are scoped; the final figure does **not** persist in history when an owned session ends.
- The initial implementation targets **one Figure in a real Kitty terminal**. Additional figures, prompt handling, event integration and mouse/keyboard input ownership require independent designs.

The experimental API is in a distinct module, not retrofitted into `plt.show(block=False)`. It is not evidence that arbitrarily calling pyplot APIs while another REPL owns stdout is safe.

## Alternatives

- Re-anchor historical output by moving the cursor to the visible viewport: rejected as a potentially destructive operation on foreign output and shell prompts.
- Make `WSKR_FIT=contain` implicitly enter an alternate screen: rejected as surprising and incompatible with persistent nonblocking output.
- Use Kitty remote control/window orchestration or yabai: unnecessary privileges, unrelated to the backend's ownership rules.
- Require a complete terminal UI library before supporting owned sessions: postpones a small independently testable first-party mode.

## Consequences and qualification

Positive: distinct contracts with no hidden shell interference, bounded lifecycle and testable viewport repaint. Negative: the caller must opt in, provide a foreground TTY and drive updates; alternate-screen contents are discarded when the scope ends.

Portable tests verify ownership, input isolation, failure cleanup and debounced resizing. Hosted real Kitty/Xvfb screenshots confirm initial display, shrink, expansion and alternate-screen restoration. Independent **native macOS and yabai** graphical qualification remains outstanding, so the API remains experimental.

# ADR-003: Direct Kitty image transport with managed placements

- **Date:** 2026-10-19
- **Status:** Accepted
- **Decision scope:** Protocol correctness, image identities, Rich composition

## Context

wskr currently uses the external `kitty +kitten icat` executable for primary display, and its experimental direct transfer path does not encode PNG consistently with the Kitty specification. Rich rendering needs images to move with text rather than requiring all placement to be controlled by cursor escape sequences. Interactive redraw should not accumulate images in terminal scrollback.

## Decision

Implement Kitty's graphics protocol directly in Python with correct pixel-format declarations, Base64 framing/chunking and safe response handling. Separate image transmission from image/placement identity, reuse managed placements for redraw, and support Unicode-placeholder **virtual** placements for Rich. Both Matplotlib and Rich use the same image manager. Keep `kitty icat` only as optional diagnostic/comparison tooling.

## Alternatives considered

- Keep `icat` as a required subprocess: simpler and currently working in some environments, but slower and difficult to integrate with placement management.
- Have Matplotlib and Rich each implement their own Kitty framing: duplicated protocol code and divergent lifecycles.
- Require Kitty remote control (`kitty @`) or platform window automation: unnecessary privileges and host dependencies.
- Adopt a general multi-terminal UI framework immediately: unnecessary complexity before a second functional protocol.

## Consequences

Positive: less runtime tooling, reusable placements, better Rich composition and explicit cleanup. Negative: correct implementation requires capability negotiation, ID ownership and failure handling; real Kitty validation is essential. Other protocols remain future additions and cannot be called supported while stubbed.

**Design references:** [DESIGN ``3, 7–8](../../DESIGN.md), `INV-07`, `INV-08`, `INV-09`, `INV-11`.

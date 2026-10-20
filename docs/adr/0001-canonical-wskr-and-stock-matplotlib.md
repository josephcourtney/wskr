# ADR-001: Canonical wskr, standard Matplotlib public API

- **Date:** 2026-10-19
- **Status:** Accepted
- **Decision scope:** Project identity and public plotting interface

## Context

Earlier work explored a standalone `mplkitty` backend, the existing modular `wskr` package, the minimal `matplotlib-backend-kitty`, and `jkit` plotting utilities. The desired user experience is to render in Kitty with ordinary Matplotlib code, while keeping optional Rich rendering and room for additional terminal transports.

## Decision

Use **wskr** as the canonical implementation. Preserve the Matplotlib backend model and existing backend selection: `MPLBACKEND=wskr_kitty`, module backend selection, normal `Figure`/`Axes`/`pyplot`/`savefig`. Keep a separate terminal-protocol layer and optional Rich renderables. Do not introduce new `wskr.plot` / `wskr.subplots` / `wskr.show` as required plotting APIs. Keep semantic plotting utilities like `jkit` separate.

## Alternatives considered

- Continue `mplkitty` as a new standalone project: smaller initial implementation, but duplicates wskr's established transport/Rich abstractions and testing investments.
- Adopt jktr's minimal backend verbatim: a clear Matplotlib integration but external `icat` dependency and limited terminal appearance/placement control.
- Integrate all plotting helpers into one high-level library: more convenience APIs but weaker separation of concerns.

## Consequences

Positive: less duplicated work, stock Matplotlib interoperability and shared backend/Rich graphics transport. Negative: wskr requires cleanup of experimental layers, heavy dependencies and backend lifecycle semantics; compatibility paths need testing. The canonical project retains its existing GPL-3.0-only licensing position.

**Design references:** [DESIGN ``1–4](../../DESIGN.md), `INV-01`, `INV-05`, `INV-11`.

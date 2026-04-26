# Round 2 — State-event matrices

One file per stateful entity. Filename pattern: `<entity-id>-state-machine.json` (e.g. `E.RESERVATION-state-machine.json`).

A "stateful entity" is one whose Round 1 catalog entry has `kind: stateful` in `round-1/entities.json`. Value-typed entities (e.g. `kind: value`) don't have state machines.

Each file declares:
- `entity` — the entity ID this matrix is for
- `states` — the lifecycle states (mutually exclusive; every instance is always in exactly one)
- `events` — every external trigger, internal completion, failure, timeout, or actor-initiated operation that can affect this entity
- `cells` — one record per (state, event) pair. `kind` is one of:
  - `transition` — state changes; specify `next_state`, optional `guard`, `actions`, `output_events`
  - `noop` — event acknowledged but state unchanged; specify `rationale`
  - `impossible` — combination cannot occur; **must specify `justification_ref`** pointing to the invariant or mechanism that enforces impossibility

## Schema

`../.ci/schemas/state-machine.schema.json`

## Closure condition

- Every stateful entity has a `<entity-id>-state-machine.json` file.
- Every (state × event) cell is filled in every matrix — `python spec/.ci/checks/check_round2_completeness.py` exits 0.
- Every `impossible` cell has a `justification_ref` resolving to a real invariant or other artifact.

## Bootstrapping

This directory is empty until Round 1 has at least one stateful entity. Once it does, the LLM driver (per [`AGENTS.md`](../AGENTS.md)) walks [`agents/round-2-state-event.md`](../agents/round-2-state-event.md) for each stateful entity. `spec/scripts/new-entity.sh` can scaffold both the round-1 stub and the round-2 matrix file. From project root:

```bash
bash spec/scripts/new-entity.sh E.YOUR_ENTITY YourEntityName "STATE_A STATE_B STATE_C"
```

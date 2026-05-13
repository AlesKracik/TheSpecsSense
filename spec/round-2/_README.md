# Round 2 — State machines

Two files per stateful entity:

- `<entity-id>.qnt` — the formal state machine (states, events, actions). This is the **authoritative artefact** and is consumed unchanged by Round 5 via `import`.
- `<entity-id>-notes.json` — the companion holding per-cell `_note`, `_rationale`, `source_evidence`, `uncertainty`, and `justification_ref` (for `impossible` cells). The fields Quint cannot enforce live here.

A "stateful entity" is one whose Round 1 catalog entry has `kind: stateful` in `round-1/entities.json`. Value-typed entities (e.g. `kind: value`) don't have state machines.

## The `.qnt` module

A single `module <EntityName>` containing:

- `type State = STATE_A | STATE_B | ...` — one literal per declared lifecycle state.
- `var s: State` (or `var instances: Set[{ id: int, state: State }]` for collections — pick the shape matching the entity's cardinality).
- `action init` — sets every `var` to its declared initial value.
- One `action handle_<event_name>` per declared event, body composed of guarded branches (one per applicable `(state, event)` cell).
- `action step = any { handle_<event_1>, handle_<event_2>, ... }` — the dispatch the model checker walks.

Round 5 `imports` this module and adds `val` invariants over its state. **Round 5 never edits the module.** State changes are owned by Round 2.

## The `-notes.json` companion

Each file declares:
- `entity` — the entity ID this matrix is for
- `states` — the lifecycle states (mirrors `type State` in the `.qnt`)
- `events` — every external trigger, internal completion, failure, timeout, or actor-initiated operation that can affect this entity (mirrors `handle_<event_name>` action names without the `handle_` prefix)
- `cells` — one record per (state, event) pair. `kind` is one of:
  - `transition` — state changes; corresponding `.qnt` branch is `all { s == STATE, <guard>, s' = NEXT, ... }`
  - `noop` — event acknowledged but state unchanged; corresponding branch is `all { s == STATE, s' = s }`
  - `impossible` — combination cannot occur; corresponding branch is `all { s == STATE, false }`. **Must specify `justification_ref`** pointing to the invariant or mechanism that enforces impossibility.

The notes file is what reviewers diff. The `.qnt` is what the typechecker and model checker consume.

## Schema (notes)

`../.ci/schemas/state-machine.schema.json`

> **Note:** during the migration to `.qnt`-authoritative state machines, the schema still contains `next_state`, `guard`, `actions`, and `output_events` fields. These will be removed in a follow-up PR — their authoritative form is now the Quint branch. Until then, agents may include them in notes records as redundant prose, but the Quint is the source of truth.

## Closure condition

- Every stateful entity has BOTH `<entity-id>.qnt` AND `<entity-id>-notes.json`.
- `quint typecheck spec/round-2/<entity-id>.qnt` exits 0 for every file.
- Every (state × event) cell is filled in every notes file — `python spec/.ci/checks/check_round2_completeness.py` exits 0.
- Cross-file consistency: every `handle_<event>` branch in the `.qnt` has a matching cell record in the notes; every cell record names an event the `.qnt` handles. (CI check TBD; verify manually until then.)
- Every `impossible` cell has a `justification_ref` resolving to a real invariant or other artifact.

## Bootstrapping

This directory is empty until Round 1 has at least one stateful entity. Once it does, the LLM driver (per [`AGENTS.md`](../AGENTS.md)) walks [`agents/round-2-state-event.md`](../agents/round-2-state-event.md) for each stateful entity. `spec/scripts/new-entity.sh` can scaffold the Round 1 stub, the `.qnt` module, and the notes file. From project root:

```bash
bash spec/scripts/new-entity.sh E.YOUR_ENTITY YourEntityName "STATE_A STATE_B STATE_C"
```

> **Note:** `new-entity.sh` predates the `.qnt` split and currently scaffolds only the JSON. Until it's updated, you'll need to hand-create the `.qnt` module after running it; see the procedure in [`agents/round-2-state-event.md`](../agents/round-2-state-event.md).

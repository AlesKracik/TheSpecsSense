# Agent: Round 2 — State machine + state-event matrix cell(s)

## Task

Author or extend the state machine for ONE entity. The state machine is the formal authoritative artefact for this entity's lifecycle and is consumed unchanged by Round 5. For each (state, event) pair, produce:

1. A Quint `action` (or guarded branch within one) in the entity's `.qnt` module — the formal substrate.
2. A matching cell record in the entity's notes companion — the prose `_note`, evidence, rationale, and uncertainty.

If invoked to fill ONE cell, only the action and note for that cell are added; the rest of the module remains untouched.

## You are working on

- **Entity:** `{{ENTITY_ID}}`
- **Target Quint file:** `spec/round-2/{{ENTITY_ID}}.qnt`
- **Target notes file:** `spec/round-2/{{ENTITY_ID}}-notes.json`
- **Schema (notes):** `spec/.ci/schemas/state-machine.schema.json` (see Migration note at end of file)
- **Empty cells to fill:** `{{LIST_OF_(STATE,EVENT)_PAIRS}}`

## Layer rule — Round 2 owns the state machine

Round 2 is the **sole author** of state declarations, events, and actions. Round 5 only `import`s your module and adds `val` predicates over it. If Round 5 needs new state to express an invariant, the R5 agent files a Round 2 PR first; it does not edit `.qnt` state directly. This boundary is enforced at PR review and (when implemented) by a CI check that asserts no `var`/`action`/`init` diffs land in PRs labelled `spec/round-5`.

## Context provided

- The full current `{{ENTITY_ID}}.qnt`
- The full current `{{ENTITY_ID}}-notes.json`
- The entity's record from `spec/round-1/entities.json`
- All verbs in `spec/round-1/verbs.json` whose object is this entity
- `spec/round-5/invariants.qnt` and `invariant-rationale.json` (so impossible-by-construction claims can cite a real invariant)

## Mode

Runs **greenfield** OR **brownfield** per invocation (never both at once); for project `Mode: mixed` the orchestrator dispatches both variants in parallel and reconciles at PR review. The output schema and procedure are identical; only the source of cell content differs.

### Greenfield input
- Stakeholder draft of the entity's intended lifecycle. The notes record's `rationale` records the WHY.

### Brownfield input
*Orchestrator: ensure this agent has the [`fetch-evidence`](../skills/fetch-evidence.md) skill loaded and `spec/scope.md § Evidence sources` in its initial context. The agent invokes the skill as needed during reasoning, using the bullet list below as the slice request.*

- The implementation file(s) realizing this entity (paths provided by the orchestrator).
- Transition functions, event handlers, switch/match statements, state-mutation code paths.
- Each cell from brownfield evidence MUST include a `source_evidence` field citing file:line **in the notes record**. Quint comments are not enforceable; the JSON companion carries auditable metadata.
- For `kind: impossible`, also cite the code guard or assertion enforcing it (in addition to `justification_ref`).
- If code's behavior under (state, event) is undefined (no handler, default fallthrough), propose `kind: noop` with `uncertainty: high` and flag for stakeholder triage.

## Procedure

### When seeding a fresh entity (no `.qnt` file yet)

1. Create `spec/round-2/{{ENTITY_ID}}.qnt` with a single `module {{EntityName}}` containing:
   - `type State = STATE_A | STATE_B | ...` — one literal per declared lifecycle state.
   - `var s: State` — the entity's current state. (For collections of instances use `Set[{ id: int, state: State }]`; pick the shape that matches the entity's cardinality.)
   - `action init = all { s' = STATE_A }` (or the declared initial state).
   - One `action handle_<event_name> = ...` stub per declared event, with body `all { false }` (placeholder; will be filled cell-by-cell).
   - `action step = any { handle_<event_1>, handle_<event_2>, ... }`.
2. Create `spec/round-2/{{ENTITY_ID}}-notes.json` with `entity`, `states`, `events`, and `cells: []`.

### When filling cells in an existing entity

For each empty cell `(STATE, event)`:

1. Decide its `kind`:
   - **transition** — a state change occurs. In `handle_<event>`, add a guarded branch:
     ```
     all { s == STATE, <guard>, s' = NEXT_STATE, <action_effects> }
     ```
   - **noop** — event acknowledged, state unchanged. Branch is `all { s == STATE, s' = s }`.
   - **impossible** — combination cannot occur. Branch is `all { s == STATE, false }`; the notes record MUST carry `justification_ref` pointing to the invariant or mechanism that enforces impossibility.

2. For **transition** branches:
   - `NEXT_STATE` must be one of the declared `State` literals — extending `type State` is allowed but must be reflected in both the `.qnt` and the notes file's `states` list.
   - Side effects on entity attributes are encoded as additional `next` assignments (e.g. `attempts' = attempts + 1`).
   - Output events to other entities are written as comments in the `.qnt` and listed in the notes record's `output_events`. Cross-entity emission becomes a joint action in Round 4.

3. For **impossible** branches:
   - `justification_ref` in the notes record must resolve to a real invariant ID. Check `spec/round-5/invariant-rationale.json`.
   - If no suitable invariant exists, set `kind: noop` instead and flag `uncertainty: high`.

4. Add a notes record per cell with a 40-300 char `_note` covering state, event, kind, next_state (if any), and actions (if any). The note must faithfully render the Quint branch — readers of the JSON diff should be able to predict the Quint without reading it.

## Output format

```json
{
  "uncertainty": "low | medium | high",
  "qnt_patch": "Unified diff against round-2/<entity>.qnt",
  "json_patch": [
    {"op": "add", "path": "/cells/-", "value": { ... cell record per schema ... }}
  ],
  "rationale_for_pr_body": "Brief summary of which cells were filled and any judgment calls. Cite invariants for impossible cells. Note any new states or events introduced."
}
```

## Hard rules

- The `.qnt` module and the notes file MUST stay in sync. Every `handle_<event>` branch has a matching cell record; every cell record names a Quint identifier the typechecker can resolve.
- Do not modify cells or `handle_` branches that already exist; only ADD missing ones. To revise an existing cell, file a separate PR.
- Every cell has a unique `id` of the form `C2.<STATE>.<event_name>` (unchanged from the previous JSON-only design).
- New states or events ADD to `type State` / the `step` dispatch — never rename or delete existing ones.
- An impossible cell with no real `justification_ref` is a hard failure — do not fabricate an invariant ID.
- Quint comments are not auditable; `_note`, `source_evidence`, `rationale`, `uncertainty`, and `justification_ref` all live in the notes JSON, never in `.qnt` comments.

## Migration note

Until the schema/CI rewrite lands:
- The notes file uses the existing `state-machine.schema.json` shape (with `entity`, `states`, `events`, `cells`), but is now a companion to the `.qnt` rather than the sole artefact.
- The `check_round2_completeness.py` check still reads the notes file's `cells` array — keep it valid.
- A follow-up PR will (a) slim the schema to drop fields now expressed in Quint (`next_state`, `guard`, `actions`, `output_events`), (b) add a `quint typecheck` step for `round-2/*.qnt`, (c) add a cross-file consistency check that every Quint branch has a notes record and vice versa.

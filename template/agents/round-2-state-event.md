# Agent: Round 2 — State-event matrix cell(s)

## Task

Fill one or more empty cells in the state-event matrix for a single entity. Each cell is the answer to: "What happens if this event occurs while the entity is in this state?"

## You are working on

- **Entity:** `{{ENTITY_ID}}`
- **Target file:** `spec/round-2/{{ENTITY_ID}}-state-machine.json`
- **Schema:** `spec/.ci/schemas/state-machine.schema.json`
- **Empty cells to fill:** `{{LIST_OF_(STATE,EVENT)_PAIRS}}`

## Context provided

- The full state-machine.json for this entity
- The entity's record from `spec/round-1/entities.json`
- All verbs in `spec/round-1/verbs.json` whose object is this entity
- `spec/round-5/invariants.qnt` and `invariant-rationale.json` (so impossible-by-construction claims can cite a real invariant)

## Mode

Runs **greenfield** OR **brownfield** per invocation (never both at once); for project `Mode: mixed` the orchestrator dispatches both variants in parallel and reconciles at PR review. The output schema and procedure are identical; only the source of cell content differs.

### Greenfield input
- Stakeholder draft of the entity's intended lifecycle. The `rationale` records the WHY.

### Brownfield input
*Orchestrator: ensure this agent has the [`fetch-evidence`](../skills/fetch-evidence.md) skill loaded and `spec/scope.md § Evidence sources` in its initial context. The agent invokes the skill as needed during reasoning, using the bullet list below as the slice request.*

- The implementation file(s) realizing this entity (paths provided by the orchestrator).
- Transition functions, event handlers, switch/match statements, state-mutation code paths.
- Each cell from brownfield evidence MUST include a `source_evidence` field citing file:line.
- For `kind: impossible`, also cite the code guard or assertion enforcing it (in addition to `justification_ref`).
- If code's behavior under (state, event) is undefined (no handler, default fallthrough), propose `kind: noop` with `uncertainty: high` and flag for stakeholder triage.

## Procedure

For each empty cell:

1. Decide its `kind`:
   - **transition** — a state change occurs. Specify `next_state`, optional `guard`, `actions`, `output_events`.
   - **noop** — event is acknowledged but state is unchanged. Specify rationale (often "ignore; log").
   - **impossible** — this combination cannot occur given enforcement elsewhere. MUST specify `justification_ref` pointing to the invariant or mechanism that enforces impossibility.

2. For **transition** cells:
   - `next_state` must be one of the entity's declared `states`.
   - `actions` are imperative phrases naming a side effect.
   - `output_events` are events emitted to other entities (must be lowercase snake_case).

3. For **impossible** cells:
   - `justification_ref` must resolve to a real invariant ID. Check `spec/round-5/invariant-rationale.json`.
   - If no suitable invariant exists, set `kind: noop` instead and flag `uncertainty: high`.

4. Write a 40-300 char `_note` that covers state, event, kind, next_state (if any), and actions (if any).

## Output format

```json
{
  "uncertainty": "low | medium | high",
  "patch": [
    {"op": "add", "path": "/cells/-", "value": { ... cell record per schema ... }}
  ],
  "rationale_for_pr_body": "Brief summary of which cells were filled and any judgment calls. Cite invariants for impossible cells."
}
```

## Hard rules

- Do not invent states or events. Only use values from `states` and `events` declared in the file.
- Do not modify cells that already exist; only ADD missing ones.
- Every cell has a unique `id` of the form `C2.<STATE>.<event_name>`.
- An impossible cell with no real `justification_ref` is a hard failure — do not fabricate an invariant ID.

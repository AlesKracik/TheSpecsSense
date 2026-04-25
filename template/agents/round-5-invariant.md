# Agent: Round 5 — Formal invariant in Quint

## Task

Add or strengthen ONE invariant in `spec/round-5/invariants.qnt` and add the matching rationale entry in `spec/round-5/invariant-rationale.json`. Output BOTH a patch to the `.qnt` file AND a JSON Patch to the rationale file.

## You are working on

- **Invariant ID:** `{{INV_ID}}` (e.g. `INV.NO_OVERSUBSCRIPTION`)
- **Kind:** `{{safety | liveness | fairness}}`
- **Target Quint file:** `spec/round-5/invariants.qnt`
- **Target rationale file:** `spec/round-5/invariant-rationale.json`

## Context provided

- The full current `invariants.qnt`
- The full current `invariant-rationale.json`
- All Round 1 entities and verbs
- All Round 2 state machines
- A statement of the property to express in natural language: `{{PROPERTY_STATEMENT}}`

## Mode

Runs **greenfield** OR **brownfield** per invocation (never both at once); for project `Mode: mixed` the orchestrator dispatches both variants in parallel and reconciles at PR review. Brownfield is a **strong source** for Round 5 — production telemetry reveals invariants that actually held (or failed to hold).

### Greenfield input
- Stakeholder-stated safety / liveness / fairness property.
- Mechanically-derived invariants from rounds 1-4 (e.g. "every state must be reachable").

### Brownfield input
*Orchestrator: ensure this agent has the [`fetch-evidence`](../skills/fetch-evidence.md) skill loaded and `spec/scope.md § Evidence sources` in its initial context. The agent invokes the skill as needed during reasoning, using the bullet list below as the slice request.*

- Dynamic invariant traces from production runs (Daikon-style: properties that held empirically across N executions).
- Existing assertions and `invariant()` calls in code.
- Postmortems where a property was *believed* to hold but was violated — these are the highest-value candidates because they come with a known counterexample to test against.
- Each invariant from brownfield evidence MUST include `source_evidence` (file:line, trace ID, or postmortem ID) in the rationale entry.
- For invariants extracted from traces, record the observation window in `rationale` (e.g. "held across N=12M observed transitions over 90 days").

## Procedure

1. Translate the property statement into a Quint predicate (`val` returning bool) over the existing module's state variables.
2. If the property requires state not yet in the Quint module, ADD that state to the module's `var` declarations and update `init` accordingly. Do not delete or rename existing state.
3. Add a line to `allInvariants` ANDing your new predicate.
4. Identify which actions (cells, interactions, verbs) could violate the invariant. List their IDs in the rationale entry's `actions_that_could_violate`.
5. Write the rationale entry's 40-300 char `_note` covering what the invariant says and which actions must preserve it.

## Output format

```json
{
  "uncertainty": "low | medium | high",
  "qnt_patch": "Unified diff against round-5/invariants.qnt",
  "json_patch": [
    {"op": "add", "path": "/invariants/-", "value": { ... rationale record per invariant-rationale.schema.json ... }}
  ],
  "rationale_for_pr_body": "What the invariant captures, why it matters, what actions are at risk."
}
```

## Hard rules

- The Quint identifier in `qnt_name` must exactly match the `val` name you add.
- Run `quint typecheck` mentally; if your patch wouldn't compile, fix it before submitting.
- Do NOT weaken existing invariants; if you believe one is over-strong, file a separate PR with that single weakening change.
- Every action in `actions_that_could_violate` must resolve to a real ID (cell, interaction, or verb) — referential integrity will check this.

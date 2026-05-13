# Agent: Round 5 — Formal invariant in Quint

## Task

Add or strengthen ONE invariant in `spec/round-5/invariants.qnt` and add the matching rationale entry in `spec/round-5/invariant-rationale.json`. Output BOTH a patch to the `.qnt` file AND a JSON Patch to the rationale file.

## Layer rule — Round 5 owns invariants only

Round 2 is the authoritative source of state declarations, events, and entity-local actions. `invariants.qnt` `import`s the Round 2 modules and declares `val` predicates over the imported state.

Permitted edits in this round's PRs:
- Adding `import Round2Entity.*` lines (or aliased imports).
- Adding `val <name> = ...` predicates.
- Adding a clause to `allInvariants`.
- Editing `init` and `step` **only** to compose imported Round 2 actions (e.g. `init = all { Foo::init, Bar::init }`, `step = any { Foo::step, Bar::step }`). These are compositional glue, not new behavior.
- Comments.

Forbidden in this round's PRs (must be a Round 2 PR instead):
- New `var` declarations.
- New `type` declarations.
- New `action` declarations beyond the compositional `init`/`step`.
- Renaming or deleting any existing `var`/`type`/`action`.

If you discover the property requires state that Round 2 has not declared, STOP and file a Round 2 PR first; resume this invariant only after that PR is merged. This boundary is enforced at PR review and by `spec/.ci/checks/check_round5_layer_boundary.py`, which fails any diff that adds disallowed declarations in `round-5/*.qnt`.

## You are working on

- **Invariant ID:** `{{INV_ID}}` (e.g. `INV.NO_OVERSUBSCRIPTION`)
- **Kind:** `{{safety | liveness | fairness}}`
- **Target Quint file:** `spec/round-5/invariants.qnt` (imports `spec/round-2/<entity>.qnt` modules)
- **Target rationale file:** `spec/round-5/invariant-rationale.json`

## Context provided

- The full current `invariants.qnt`
- The full current `invariant-rationale.json`
- All Round 1 entities and verbs
- All Round 2 Quint modules (`spec/round-2/*.qnt`) — the state vocabulary your predicates may reference
- All Round 2 notes companions (`spec/round-2/*-notes.json`) — for action IDs to cite in `actions_that_could_violate`
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

1. Translate the property statement into a Quint predicate (`val` returning bool) over the state variables already declared in the imported Round 2 modules.
2. If the property requires state that does not exist in any Round 2 module, STOP. Open a Round 2 PR that adds the needed state (the [Round 2 agent](round-2-state-event.md) owns this work). Do NOT add `var`, `type`, `action`, or `init` declarations in this PR; doing so violates the layer rule and will be rejected at review.
3. Add a line to `allInvariants` ANDing your new predicate.
4. Identify which actions (cells, interactions, verbs) could violate the invariant. List their IDs in the rationale entry's `actions_that_could_violate`. Action IDs come from the Round 2 notes files and Round 4 interactions — they resolve via the cross-file referential-integrity check.
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
- Layer rule (see top of file): only `val`, `import`, `allInvariants`, comments, and compositional edits to `init`/`step` are permitted. Adding new `var`/`type`/`action` declarations is rejected — file a Round 2 PR for state changes first.

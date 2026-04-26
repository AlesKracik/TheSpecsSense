# Agent: Round 3 — Input partitioning for one dimension

## Task

Produce a complete partition for one input dimension: a finite set of mutually-exclusive, collectively-exhaustive equivalence classes, each with specified behavior and representative values.

## You are working on

- **Dimension ID:** `{{DIMENSION_ID}}` (e.g. `D.SEAT_COUNT`)
- **Source:** `{{VERB_OR_ENTITY_ATTRIBUTE_PATH}}` (a verb parameter or entity attribute, e.g. `<verb-id>.<param-name>`)
- **Value type:** `{{integer | string | decimal | enum | datetime}}`
- **Target file:** `spec/round-3/{{DIMENSION_ID}}-partition.json`
- **Schema:** `spec/.ci/schemas/partition.schema.json`

## Context provided

- The verb or entity definition this dimension comes from
- Any existing partition file at the target path (treat its classes as committed; you are extending or proposing alternatives, not overwriting)
- Relevant scope.md excerpts about bounds and limits

## Mode

Runs **greenfield** OR **brownfield** per invocation (never both at once); for project `Mode: mixed` the orchestrator dispatches both variants in parallel and reconciles at PR review. Round 3 has **weak code signal** — branches do not reliably correspond to *intended* equivalence classes — so brownfield-mode output should always be flagged for stakeholder triage.

### Greenfield input
- Stakeholder-stated bounds and behavior per range; type and business limits from `scope.md`.

### Brownfield input
*Orchestrator: ensure this agent has the [`fetch-evidence`](../skills/fetch-evidence.md) skill loaded and `spec/scope.md § Evidence sources` in its initial context. The agent invokes the skill as needed during reasoning, using the bullet list below as the slice request.*

- Validator functions, input-sanitization code, conditional branches keyed on the dimension's value.
- Test fixtures and parameterized inputs that exercise the dimension.
- Each class from brownfield evidence MUST include `source_evidence` (file:line) and carry `uncertainty: medium` minimum.
- Weak-signal caveat: `if (x > 100)` does not prove `100` is the *intended* boundary — it may be a stale magic number. Propose stakeholder confirmation as a follow-up on every brownfield-extracted class.

## Procedure

1. Identify natural boundaries: type limits, physical limits, business limits, performance regime changes, error modes. Examples for an integer:
   - Below valid range (often `< 1` or `< 0`)
   - Each business-meaningful band (Tiny / Small / Medium / Large / Huge per scope)
   - Above valid range
2. Partition the value space into named classes. Classes must be **mutually exclusive** and **collectively exhaustive**.
3. For each boundary value (e.g. exactly `1`, exactly `10`), assign it to exactly one class. Record the choice in that class's `boundary_assigned_here`. Do NOT leave a boundary value implicit.
4. For each class, specify `behavior` (`accept | reject | alternative | warn | escalate`) and a concrete `behavior_detail`.
5. For each class, choose three representative values for test derivation: the minimum of the class, a typical interior value, and the maximum of the class.

## Output format

```json
{
  "uncertainty": "low | medium | high",
  "patch": [
    {"op": "replace", "path": "", "value": { ... full partition file per schema ... }}
  ],
  "rationale_for_pr_body": "Summary of class choices, why these boundaries, and any judgment calls about boundary assignment."
}
```

## Hard rules

- Coverage must be complete: every value of the dimension's type maps to exactly one class.
- Every boundary value is assigned to exactly one class, named in `boundary_assigned_here`.
- Each class has all three representatives.
- Every class has a 40-300 char `_note` covering range, behavior, and boundary assignment.
- If the dimension already has a partition file and you cannot improve it, output `patch: []` and explain why in the rationale.

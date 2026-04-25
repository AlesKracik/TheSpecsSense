# Agent: Round 8 — Assumption excavation for one category

## Task

Excavate implicit assumptions in ONE category. For each assumption: state it, score risk if violated, and propose a mitigation (accept / transfer / reduce / convert_to_requirement).

## You are working on

- **Category:** `{{environmental | data | human | organizational | technological}}`
- **Target file:** `spec/round-8/assumptions.json` (append entries)
- **Schema:** `spec/.ci/schemas/assumption.schema.json`

## Context provided

- The full current `assumptions.json`
- All Round 1, 2, 3, 4, 6, 7 artifacts
- For brownfield: postmortems, runbooks, ADRs, deployment scripts (paths provided)

## Mode

Runs **greenfield** OR **brownfield** per invocation (never both at once); for project `Mode: mixed` the orchestrator dispatches both variants in parallel and reconciles at PR review. Brownfield is the **richest source** for Round 8 — postmortems, runbooks, ADRs, and deployment scripts each document an assumption that was once implicit, then bit someone, then got written down.

### Greenfield input
- Probing questions (below) walked against rounds 1-7 artifacts.
- Stakeholder elicitation: "what must be true about the world for this requirement to work?"

### Brownfield input
*Orchestrator: ensure this agent has the [`fetch-evidence`](../skills/fetch-evidence.md) skill loaded and `spec/scope.md § Evidence sources` in its initial context. The agent invokes the skill as needed during reasoning, using the bullet list below as the slice request.*

- **Postmortems** — every "we assumed X but it turned out Y" is a Round 8 entry.
- **Runbooks** — every "if X happens, do Y" implies an assumption that X is rare or recoverable.
- **ADRs** — every "we chose X because Y" implies Y is true.
- **Deployment scripts and CI configs** — every hard-coded value is an assumption (region, capacity, third-party endpoint).
- **Code comments** containing "TODO", "HACK", "FIXME", or "assumes" — each names an implicit assumption.
- Each assumption from brownfield evidence MUST include `source_evidence` citing the postmortem ID, runbook section, ADR number, or file:line.
- An assumption surfaced via postmortem is severity HIGH minimum — it already has known prior cost.

## Probing questions per category

- **environmental** — what must be true about network, time, hardware, third-party services?
- **data** — what assumptions about format, encoding, size, language, validity?
- **human** — what assumptions about operator competence, availability, training?
- **organizational** — what assumptions about legal authority, policy stability, personnel retention?
- **technological** — what assumptions about platform longevity, API stability, algorithm soundness?

## Procedure

For each assumption:

1. State it as a positive assertion ("X is true at all times").
2. Identify which existing artifacts depend on it. Populate `referenced_by` with their IDs.
3. Score `risk_if_violated` (concrete consequence) and `severity`.
4. Choose a `mitigation`:
   - **accept** — risk is small enough, no action.
   - **transfer** — covered by contract / SLA / insurance with named other party.
   - **reduce** — add detection or fallback to lower probability or impact.
   - **convert_to_requirement** — promote to an explicit requirement that must be implemented and tested.
5. For `convert_to_requirement`, the new requirement should be filed via the appropriate round agent in a follow-up PR; cite the new requirement ID in `mitigation_detail`.

## Output format

```json
{
  "uncertainty": "low | medium | high",
  "patch": [
    {"op": "add", "path": "/assumptions/-", "value": { ... assumption record per schema ... }}
  ],
  "rationale_for_pr_body": "Per assumption, the source (which artifact relies on it), risk reasoning, and mitigation choice."
}
```

## Hard rules

- IDs follow `A8.<CATEGORY_UPPER>.<slug>` (e.g. `A8.ENV.ntp_sync`).
- `referenced_by` must be non-empty. An assumption with zero references is suspect — either find references or argue why it matters anyway in the rationale.
- Every assumption has a 40-300 char `_note` covering statement, mitigation, and the IDs it is referenced by.

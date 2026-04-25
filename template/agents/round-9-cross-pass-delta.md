# Agent: Round 9 — Cross-pass delta discovery for one round

## Task

Given the spec at the previous iteration tag and the current HEAD, identify NEW gaps in ONE round's artifacts that the delta exposes. New entries in any round often imply missing entries in others.

## You are working on

- **Round to scan:** `{{1 | 2 | 3 | 4 | 5 | 6 | 7 | 8}}`
- **Previous tag:** `{{ITERATION_TAG_N-1}}`
- **Current HEAD:** `{{COMMIT_SHA_OR_TAG}}`
- **Target files:** files under `spec/round-{{N}}/`

## Context provided

- `git diff {{ITERATION_TAG_N-1}}..HEAD -- spec/` (the full delta)
- All artifact files at HEAD
- The artifact files at the previous tag (for comparison)

## Procedure

1. Inspect the diff. List every NEW ID added since the previous tag (entities, verbs, actors, cells, classes, interactions, invariants, qualities, scenarios, assumptions).
2. For each new ID, ask: "what does Round {{N}} owe this entity / verb / etc.?"
   - **Round 1** — does the new entity have all attributes? Are verbs/actors fully linked?
   - **Round 2** — does each new stateful entity have a state-machine.json? Do new events appear in existing matrices?
   - **Round 3** — does each new verb parameter have a partition?
   - **Round 4** — does each new entity have its cross-product pairs analyzed?
   - **Round 5** — do new entities appear in the Quint module's state? Do new operations preserve all invariants?
   - **Round 6** — do new operations or assets surface new quality concerns?
   - **Round 7** — do new entities or interactions create new attack surface?
   - **Round 8** — do new requirements rest on previously-implicit assumptions?
3. For each gap, dispatch (i.e. propose in the PR body) a follow-up agent task: name the agent prompt template and the inputs it would need.

## Output format

```json
{
  "uncertainty": "low | medium | high",
  "gaps_found": [
    {
      "round_owing": {{N}},
      "trigger_id": "<the new ID that caused this gap>",
      "gap_description": "What is missing.",
      "follow_up_agent": "round-X-<name>",
      "follow_up_inputs": { ... key inputs the orchestrator would need to pass ... }
    }
  ],
  "rationale_for_pr_body": "Summary of pass-over-pass delta and the gap pattern."
}
```

## Hard rules

- Output a structured gap list, NOT patches. Round 9 dispatches to other rounds; it does not edit artifacts directly.
- If the delta produced zero new IDs in any round, output `gaps_found: []` and recommend tagging this iteration as the fixed point.
- Never fabricate a gap to look productive; an empty list is a meaningful signal.

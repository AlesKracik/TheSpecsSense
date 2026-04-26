# Agent: Round 9 — Cross-pass / cross-round gap discovery

## Task

Find gaps where one round owes a record to IDs introduced by another round. Two operational shapes depending on which pass you're in:

- **Pass 1 (full cross-round audit).** The previous pass tag (`pass-0`) has empty catalogs; there's no meaningful delta to scan. Walk every round's artifacts and look for cross-round inconsistencies that emerged during pass 1 — IDs referenced by one round but not produced by the round that owns them, completeness gaps where a round didn't anticipate what later rounds would need from it.
- **Pass 2+ (delta scan).** The previous pass tag has real content. Walk the `git diff` between that tag and HEAD; the new IDs are the trigger surface, and the question is whether the rounds owing those IDs have caught up.

The output is the same shape in both cases: a list of gaps, each naming the trigger ID and which round owes a record.

## You are working on

- **Round to scan:** `{{1 | 2 | 3 | 4 | 5 | 6 | 7 | 8}}`
- **Pass mode:** `pass_1_full_audit | pass_n_delta`
- **Previous pass tag** (only meaningful in `pass_n_delta`): `{{PASS_TAG_N-1}}` (e.g. `pass-2`)
- **Current HEAD:** `{{COMMIT_SHA_OR_TAG}}`
- **Target files:** files under `spec/round-{{N}}/`

## Context provided

For both modes:

- All artifact files at HEAD across `spec/round-1/` through `spec/round-8/`
- `spec/round-1/{entities,verbs,actors}.json` (the universe — every legal ID lives here)

For `pass_n_delta` only:

- `git diff {{PASS_TAG_N-1}}..HEAD -- spec/` (the delta to focus on)
- The artifact files at `{{PASS_TAG_N-1}}` (for comparison)

## Procedure

### `pass_1_full_audit` mode

1. **Build a global ID set** by reading every round's artifacts at HEAD. Note where each ID is *defined* (e.g., `E.RESERVATION` is defined in `round-1/entities.json`).
2. **Build a global reference set** — every ID *referenced* by a record (verb subject/object, cell justification_ref, interaction entity_a/b, invariant actions_that_could_violate, assumption referenced_by, contract traces_to, etc.).
3. **For each ID referenced but not defined**, that's a hard gap — but the referential-integrity CI check (`spec/.ci/checks/check_referential_integrity.py`) catches those at commit time. If you find one here, something slipped through CI; flag it.
4. **For each ID defined but not fully covered**, that's the soft cross-round gap Round 9 specializes in. Walk Round {{N}}'s perspective:
   - **Round 1** — does each entity have attributes (no `attributes: []`)? Does every verb have subject + object that resolve? Does every actor have at least one `permitted_verbs` entry?
   - **Round 2** — does every stateful entity in `entities.json` (kind=stateful) have a corresponding `<entity-id>-state-machine.json`? Within each matrix, does every (state, event) cell have an entry (transition / noop / impossible)?
   - **Round 3** — does every verb parameter and every entity attribute that's a value type have a `<dimension>-partition.json`?
   - **Round 4** — has every entity pair that could meaningfully interact been examined? Pairs explicitly marked `family: independent` count as covered.
   - **Round 5** — does every entity in `entities.json` appear in the Quint module's state declarations? Does every stateful action have an invariant constraining it?
   - **Round 6** — does every standard quality dimension (security, performance, scalability, ...) have at least one entry, either with targets or `applicable: false` + rationale?
   - **Round 7** — does every STRIDE category have at least one scenario, either with mitigation or `accepted_risk` + signoff? Are new entities reflected in the attack surface?
   - **Round 8** — does each round's records reference assumptions where load-bearing (e.g., a Round 6 SLO target that depends on an `A8.HUMAN.*` assumption being met)?
5. **Emit gaps.** Each gap names the trigger ID and which round owes the missing record.

### `pass_n_delta` mode

1. Inspect the diff. List every NEW ID added since `{{PASS_TAG_N-1}}` (entities, verbs, actors, cells, classes, interactions, invariants, qualities, scenarios, assumptions).
2. For each new ID, ask: "what does Round {{N}} owe this entity / verb / etc.?" — same per-round rules as pass-1 mode above, but applied only to the delta.
3. Emit gaps. Each gap names the trigger ID and which round owes a record.

## Output format

Same shape regardless of mode:

```json
{
  "mode": "pass_1_full_audit" | "pass_n_delta",
  "uncertainty": "low | medium | high",
  "gaps_found": [
    {
      "round_owing": {{N}},
      "trigger_id": "<the ID that surfaced this gap>",
      "gap_description": "What is missing — e.g. 'E.AUDIT_LOG referenced by Round 7 mitigation ADV7.STRIDE_S.session_hijack but not in entities.json' or 'no state-machine.json for stateful entity E.SESSION'.",
      "follow_up_agent": "round-X-<name>",
      "follow_up_inputs": { ... key inputs the driver would need to pass ... }
    }
  ],
  "rationale_for_pr_body": "Summary of the gap pattern and which rounds need follow-up."
}
```

## Hard rules

- Output a structured gap list, NOT patches. Round 9 dispatches to other rounds; it does not edit artifacts directly.
- If `pass_1_full_audit` finds zero gaps, the spec passed cross-round consistency on its first iteration — this is unusual but valid; recommend tagging `pass-1` and proceeding to closure-condition verification.
- If `pass_n_delta` finds zero gaps, the marginal additions since `{{PASS_TAG_N-1}}` didn't expose new cross-round consistency issues; recommend tagging `pass-{{N}}` (the next pass tag).
- Never fabricate a gap to look productive; an empty list is a meaningful signal — it means the spec is internally consistent at this iteration boundary.
- Soft cross-round gaps are distinct from hard referential-integrity failures. Don't duplicate work the CI check already did; focus on completeness across rounds, not just dangling references.

# Agent: Round 4 — Cross-product interaction for one entity pair

## Task

Specify behavior for one ordered or unordered entity pair (A, B) (sometimes triple). Either declare a meaningful interaction with specified joint behavior, OR mark the pair as `independent` with rationale.

## You are working on

- **Pair:** `{{ENTITY_A_ID}}` × `{{ENTITY_B_ID}}` (optionally `× {{ENTITY_C_ID}}`)
- **Target file:** `spec/round-4/interactions.json` (append entries)
- **Schema:** `spec/.ci/schemas/interaction.schema.json`

## Context provided

- The entity records for A, B (and C if 3-way)
- The state-machine.json for each entity (so you can reason about lifecycle overlap)
- The verb catalog (subset operating on A or B)
- Existing entries in `interactions.json` involving A or B

## Mode

Runs **greenfield** OR **brownfield** per invocation (never both at once); for project `Mode: mixed` the orchestrator dispatches both variants in parallel and reconciles at PR review. Round 4 has **weak code signal** — call graphs do not reliably reflect *intentional* interactions — so brownfield-mode output should always be flagged for stakeholder triage.

### Greenfield input
- Spec'd entities and their state machines; stakeholder reasoning about which pairs interact and which are independent.

### Brownfield input
*Orchestrator: ensure this agent has the [`fetch-evidence`](../skills/fetch-evidence.md) skill loaded and `spec/scope.md § Evidence sources` in its initial context. The agent invokes the skill as needed during reasoning, using the bullet list below as the slice request.*

- Cross-module call graphs between code realizing entity A and entity B.
- Shared DB tables, queue topics, or in-memory state both entities read or write.
- Lock files, transaction boundaries, retry handlers across the pair.
- Each interaction from brownfield evidence MUST include `source_evidence` (file:line) and carry `uncertainty: medium` minimum.
- Weak-signal caveat: a call from A to B does not prove a *behaviorally meaningful* interaction — it may be a logging dependency or shared utility. Stakeholder confirmation is required.

## Procedure

1. Walk the four interaction families and decide which (if any) apply:
   - **concurrency** — two operations on the same entity instance from different actors at the same time.
   - **lifecycle_overlap** — A depends on B while B is being deleted, retired, or migrated.
   - **resource_contention** — A and B compete for shared, finite resources (capacity, locks, quotas).
   - **temporal_ordering** — events from A and B can arrive out of expected order.

2. For each applicable family, draft an interaction record:
   - `situation` — concrete one-sentence description of the joint state that triggers the rule.
   - `specified_behavior` — what happens. Name precedence (which side wins), serialization choice (lock / queue / retry), or rejection.
   - `precedence` — short label like "first-write-wins by transaction commit order" or "B's lifecycle takes priority".

3. If after walking all four families no meaningful interaction exists, produce ONE record with `family: "independent"`, `specified_behavior: "no_interaction"`, and a rationale stating WHY independence is genuine (shared state is read-only, lifecycle is bracketed by maintenance, etc.).

## Output format

```json
{
  "uncertainty": "low | medium | high",
  "patch": [
    {"op": "add", "path": "/interactions/-", "value": { ... interaction record per schema ... }}
  ],
  "rationale_for_pr_body": "Which families were considered, which apply, and why."
}
```

## Hard rules

- Pruning a pair as `independent` is a real claim, not a pass. If you cannot defend it, raise `uncertainty: high`.
- Every interaction record has a 40-300 char `_note` covering family, situation, and behavior.
- IDs follow `X4.<A_short>_x_<B_short>.<situation_slug>`.

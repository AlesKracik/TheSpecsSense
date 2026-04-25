# Agent: Hoare contract assembly for one operation

## Task

Build a complete Hoare contract for ONE operation by reassembling clauses from rounds 1, 2, 3, 4, 5, 6, 7, 8. Every clause must trace back to a specific upstream artifact ID.

## You are working on

- **Operation:** `{{VERB_ID}}` (a verb ID from `spec/round-1/verbs.json`)
- **Target file:** `spec/contracts/{{VERB_ID}}.json`
- **Schema:** `spec/.ci/schemas/contract.schema.json`

## Context provided

- The verb record from `spec/round-1/verbs.json`
- The actor record(s) permitted to perform this verb
- The state-machine cells whose `event` matches this verb (or its emitted events)
- The partition file(s) for this verb's parameters
- The interaction(s) involving the verb's object entity
- All invariants and their `actions_that_could_violate` lists (filtered to entries that name this verb or one of its cells)
- Quality attributes whose target involves this operation
- Adversarial scenarios whose mitigation_requirement covers this operation
- Assumptions whose `referenced_by` includes any of the above

## Procedure

For each clause in the contract, walk the upstream artifacts and pull what belongs:

### `requires` (preconditions)

- From the **actor catalog**: clause that the caller holds the right role/permission. `traces_to`: actor ID.
- From **partitions** of each parameter: clause that the parameter is in an `accept` class. `traces_to`: partition class IDs.
- From **state-machine cells**: clause that the entity is in a state from which this event is permitted. `traces_to`: cell IDs.
- From **interactions**: clause for any joint precondition (e.g. "showing is not in past"). `traces_to`: interaction IDs.
- From **assumptions**: clause for any environmental precondition (e.g. clock skew bound). `traces_to`: assumption IDs.

### `ensures` (postconditions)

- From **state-machine cells**: clause that the entity transitions to the named state on success. `traces_to`: cell IDs.
- From **side effects** in the verb record: each side effect becomes an `ensures` clause.
- From **quality attributes**: latency / availability / observability obligations. `traces_to`: quality IDs.
- From **adversarial mitigations**: audit-log and tamper-evidence obligations. `traces_to`: scenario IDs.

### `preserves` (invariants)

- Every invariant whose `actions_that_could_violate` includes this verb or one of its cells. `traces_to`: invariant ID.

## Output format

```json
{
  "uncertainty": "low | medium | high",
  "patch": [
    {"op": "replace", "path": "", "value": { ... full contract per schema ... }}
  ],
  "rationale_for_pr_body": "Source-by-source summary of which artifacts contributed which clauses."
}
```

## Hard rules

- Every clause has a non-empty `traces_to`. A clause without a source is a hard failure.
- Do NOT add clauses that lack an upstream source. If you believe a clause is needed but has no source, file a follow-up PR adding it to the appropriate round, then re-run contract assembly.
- The contract's `_note` (40-300 chars) summarizes the operation, key requires, key ensures, and the invariants preserved.
- Run referential integrity mentally before submission — every `traces_to` ID must already exist.

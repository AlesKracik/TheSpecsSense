# Round 3 — Input partitioning

One file per input dimension. Filename pattern: `<dim-id>-partition.json` (e.g. `D.SEAT_COUNT-partition.json`).

Input dimensions come from:
- **Verb parameters** — every parameter named in `round-1/verbs.json` is a candidate dimension
- **Entity attributes that are value types** — every attribute in `round-1/entities.json` whose `type` is integer / decimal / string / enum / datetime
- **Externally-supplied values** — environment variables, config inputs, third-party API responses

Each file declares:
- `dimension` — the dimension ID
- `source_ref` — back-reference to the verb param or entity attribute this dimension models
- `value_type` — `integer | string | decimal | enum | datetime`
- `classes` — equivalence classes that are mutually exclusive AND collectively exhaustive. Each class has:
  - `range` — the value subset
  - `behavior` — `accept | reject | alternative | warn | escalate`
  - `boundary_assigned_here` — every boundary value (e.g. `0`, `1`, `10`, `11`) explicitly assigned to exactly one class
  - `representatives` — `min | typical | max` for test-case generation

## Schema

`../.ci/schemas/partition.schema.json`

## Closure condition

- Every dimension identified during Round 1 (verb params, entity attributes that are value types) has a partition file.
- Every boundary value is assigned to exactly one class (`boundary_assigned_here` non-empty for every relevant class).
- Every class has all three representatives (`min`, `typical`, `max`).

## Bootstrapping

This directory is empty until Round 1 has verbs with parameters or entities with value-typed attributes. Once it does, the LLM driver (per [`AGENTS.md`](../AGENTS.md)) walks [`agents/round-3-partition.md`](../agents/round-3-partition.md) for each dimension.

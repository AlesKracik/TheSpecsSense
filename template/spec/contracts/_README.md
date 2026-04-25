# Hoare contracts (consolidation)

One file per operation in the verb catalog. Filename pattern: `<verb-id>.json`.

Contracts are **derived**, not authored. Every clause traces back to:
- a Round 1 entity attribute or actor permission, or
- a Round 2 state-event cell, or
- a Round 3 partition class, or
- a Round 4 cross-product interaction, or
- a Round 5 invariant, or
- a Round 6 quality acceptance criterion, or
- a Round 7 mitigation requirement, or
- a Round 8 assumption.

The referential-integrity check (`../.ci/checks/check_referential_integrity.py`) verifies every `traces_to` ID resolves.

## Schema

`../.ci/schemas/contract.schema.json`

## Closure condition

- Every verb in `round-1/verbs.json` has a contract file.
- Every clause in every contract has a non-empty `traces_to`.

## Bootstrapping

This directory is empty until rounds 1-8 have produced enough material to assemble contracts from. The contract-assembly agent (`agents/contract-assembly.md`) creates one file per verb on dispatch.

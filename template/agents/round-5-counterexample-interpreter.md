# Agent: Round 5 — Counterexample interpreter

## Task

Read a Quint counterexample trace and propose ONE of two outcomes as a follow-up PR:

A. **Spec gap.** The trace exposes a missing requirement; propose adding a Round 2 cell, Round 4 interaction, or Round 8 assumption that closes it.

B. **Over-strong invariant.** The invariant rules out a behavior that is actually permitted; propose weakening the predicate (or splitting it).

## You are working on

- **Trace file:** `spec/round-5/traces/{{TRACE_FILENAME}}`
- **Invariant violated:** `{{INV_ID}}`

## Context provided

- The trace file (full)
- `spec/round-5/invariants.qnt` and `invariant-rationale.json` for the violated invariant
- The Round 2 state-machine.json for any entity referenced in the trace
- The Round 4 interactions involving entities in the trace
- The Round 8 assumptions referencing the violated invariant

## Procedure

1. Walk the trace step by step. Identify the action (cell, interaction, or verb) at each transition.
2. Decide A or B:
   - If a stakeholder reading the trace would say "yes, the spec really should forbid this — it's a real bug" → A.
   - If they would say "actually that behavior is fine, the invariant was too tight" → B.
   - If you can't decide, raise `uncertainty: high` and propose A by default (false positive on the spec is cheaper than a real silent gap).
3. Build the patch:
   - **A** — propose a JSON Patch against the appropriate Round 2/4/8 file adding the missing record.
   - **B** — propose a unified diff against `invariants.qnt` weakening the predicate, plus a JSON Patch to `invariant-rationale.json` updating the rationale entry's `_note` and `rationale`.

## Output format

```json
{
  "decision": "A_spec_gap | B_overstrong_invariant",
  "uncertainty": "low | medium | high",
  "json_patch_targets": ["spec/<file>"],
  "json_patches": [ ... ],
  "qnt_patch": "Unified diff or empty string",
  "rationale_for_pr_body": "Walk through the trace, name the violating action, justify A vs B, summarize the proposed fix."
}
```

## Hard rules

- Quote the relevant trace lines verbatim in `rationale_for_pr_body`.
- For decision B, keep the trace file in `round-5/traces/` for audit; do not delete it.
- Do not modify both spec content AND the invariant in the same PR; pick one direction. Mixed changes obscure responsibility.

# The `_note` convention

Every structured record at meaningful granularity carries a required `_note` field — a faithful, agent-authored prose rendering of the record in 1-3 short sentences (40-300 chars).

## Rules (CI-enforced where possible, reviewer-enforced where not)

1. **Render, do not add.** The note restates what the record's fields say. It must not introduce facts absent from the JSON, and must not omit facts that materially change the meaning. Mismatch between note and data is a bug.
2. **Cover the whole record.** Selective omission is a bug.
3. **Plain, concrete language.** Reference field values by their meaning, not internal field names.
4. **Include cited IDs.** When the record references other artifacts, the note should mention the IDs it cites so the referential-integrity checker can validate them in context.
5. **40-300 characters.** Mechanically enforced by the schema. If a record is too complex to render in 300 chars, the record itself is probably too complex and should be split.

## What `_note` is NOT

- It is not the **rationale**. `rationale` (a separate, optional field) carries the *why*. `_note` carries the *what the record says*.
- It is not a **summary** of intent. It is a translation of data.
- It is not free-form documentation. Long docs go in markdown files (e.g. `scope.md`, `glossary.md`).

## Why this matters

The reviewer reading a PR diff sees the sentence and can understand the decision without parsing JSON. If the sentence and the data appear to disagree, the reviewer drills into the JSON to resolve the doubt. This makes diff review viable for stakeholders who don't read JSON fluently and faster for those who do.

## Example

```json
{
  "id": "C2.VERIFYING.verify_complete_mismatch",
  "state": "VERIFYING",
  "event": "verify_complete_mismatch",
  "kind": "transition",
  "next_state": "AWAITING_REVIEW",
  "actions": ["retain_chunk_diff", "alert_security"],
  "rationale": "Mismatch may be transient; auto-failure destroys recoverable backup and forensic evidence.",
  "_note": "When verification finds a full mismatch during VERIFYING, the job moves to AWAITING_REVIEW, retaining the chunk diff and alerting security."
}
```

The note covers state, event, next_state, and both actions. The rationale (separate field) explains why this was chosen over alternatives.

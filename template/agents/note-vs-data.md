# Agent: `_note`-vs-data semantic check

## Task

Read ONE record (any kind), compare its `_note` field against the rest of the record's data, and decide whether they agree. Output a structured verdict with reasoning.

This is the **semantic** half of the `_note` convention. The mechanical half (presence, length) is enforced by `spec/.ci/checks/check_notes.py`. This agent runs in CI as an advisory check on changed records, and is gated only as a hard fail on CRITICAL changes.

## You are working on

- **Record:** the JSON value provided inline below
- **Record type:** `{{entity | verb | actor | cell | partition_class | interaction | invariant | quality | scenario | assumption | contract | test_metadata | diff_context}}`

## Procedure

1. Parse the record. Identify the material data fields (everything except `_note` and free-form `rationale`).
2. Parse the `_note`. List the facts it asserts.
3. Compare:
   - **Added facts** — the note says something the data does not.
   - **Omitted material facts** — the data has something the note does not, and that omission would mislead a reviewer.
   - **Contradiction** — the note and the data say different things.
4. Decide verdict:
   - **match** — note faithfully renders the record.
   - **drift** — minor omission or addition; flag for author attention but not a hard fail.
   - **mismatch** — material disagreement; hard fail.

## Output format

```json
{
  "verdict": "match | drift | mismatch",
  "added_facts": [],
  "omitted_material_facts": [],
  "contradictions": [],
  "suggested_note": "If verdict != match, propose a corrected _note (40-300 chars) that would render the data faithfully."
}
```

## Hard rules

- Be strict. A note that says "actions = retain_chunk_diff and alert_security" when the data says `actions: ["retain_chunk_diff"]` is a `mismatch`, not `drift`.
- Be lenient about word order, synonyms, and noun choice. "User cancels" and "the user issues a cancel" are equivalent.
- The `rationale` field is NOT part of `_note`'s scope. Do not flag the note for omitting rationale content.

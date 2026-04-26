# Agent: Round 1 — Universe construction

## Task

Propose new entries (entities, verbs, or actors — pick exactly one per invocation) for the Round 1 catalog given the inputs below. Output a JSON Patch against the named target file.

## You are working on

- **Catalog kind:** `{{ENTITY|VERB|ACTOR}}`
- **Target file:** `spec/round-1/{{entities|verbs|actors}}.json`
- **Schema:** `spec/.ci/schemas/{{entity|verb|actor}}.schema.json`

## Context provided

- `spec/scope.md` (full)
- `spec/glossary.md` (full)
- The current contents of the target catalog file
- The other two Round 1 catalogs (so you can cross-reference verbs to actors, etc.)
- `{{INFORMAL_REQUIREMENT_TEXT}}` (greenfield) OR `{{CODE_SLICE}}` (brownfield)

## Procedure

Runs **greenfield** OR **brownfield** per invocation (never both at once); for project `Mode: mixed` the orchestrator dispatches both variants in parallel and reconciles at PR review. Pick the section matching the variant the orchestrator gave you.

### GREENFIELD INPUT

1. Extract candidate {{entities|verbs|actors}} from the informal requirement text.
2. For each candidate, check the existing catalog. Skip duplicates and synonyms (consult glossary).
3. For each genuinely new candidate, build a record per the schema.
4. Mark `uncertainty` per candidate when:
   - Multiple plausible categorizations exist (entity vs value, verb vs side-effect of another verb).
   - The candidate may be already implied by an existing entry under a different name.

### BROWNFIELD INPUT

*Orchestrator: ensure this agent has the [`fetch-evidence`](../skills/fetch-evidence.md) skill loaded and `spec/scope.md § Evidence sources` in its initial context. The agent invokes the skill as needed during reasoning, using the bullet list below as the slice request.*

1. Extract candidates from the code slice. Sources by catalog kind:
   - **entities** — class/struct/type definitions, DB tables, API resource paths.
   - **verbs** — public methods, route handlers, CLI commands, pub/sub topics.
   - **actors** — auth roles, IAM principals, service-account names, distinct external callers.
2. Same dedup, schema, and uncertainty rules as greenfield.
3. Add a `source_evidence` field on each record citing the file:line that motivated it.

## Output format

A single JSON object:

```json
{
  "uncertainty": "low | medium | high",
  "patch": [
    {"op": "add", "path": "/{{entities|verbs|actors}}/-", "value": { ... record per schema ... }}
  ],
  "rationale_for_pr_body": "Free-form summary for the PR description, naming the source(s) and any judgment calls."
}
```

## Hard rules

- Every new record has `_note` of 40-300 characters that faithfully renders the record.
- Every reference (verb subject/object, actor permitted_verbs) names an ID that already exists in the provided catalogs OR is also being added in this PR.
- Do NOT modify scope.md, glossary.md, or any artifact outside the target file.
- Do NOT propose more than 10 records per invocation; if you have more, return the top 10 by importance and flag the rest in `rationale_for_pr_body`.

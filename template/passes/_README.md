# Pass progress checklists

This directory tracks the **procedural state** of each algorithm pass — what's been done, what's open, where each round stands. Think of it as the running mental model the LLM driver maintains across sessions and across humans.

## Files

| File | Role |
|---|---|
| `pass-template.md` | Frozen template. Never edit. Copied to `pass-N.md` at the start of each pass. |
| `pass-1.md`, `pass-2.md`, ... | Per-pass checklist. The most recent (un-tagged) one is **active** — the LLM driver edits it as work progresses. Earlier ones are **frozen historical record** — never modified after the corresponding `pass-N` git tag is created. |

## Lifecycle

1. **Init.** `scripts/init-spec.sh` copies `pass-template.md` → `pass-1.md` and stamps the start date + scope.md commit SHA.
2. **As work progresses.** The LLM driver (per [`AGENTS.md`](../AGENTS.md)) updates the active pass file:
   - Ticks off completed checklist items
   - Updates aggregate counters ("Matrices created: 3 / 5")
   - Appends PR URLs under the relevant round
   - Records blockers waiting on humans
   - Notes session-level observations
3. **At end of pass.** When all closure conditions hold and the human tags `pass-N`, the file is frozen. The driver creates `pass-(N+1).md` from the template — stamping the new pass's start date and the previous tag as the scope baseline.

## Why this exists

Git tags + open/closed PRs + file content are the source of truth for spec content, but they don't tell you "are we still in Round 4 or moved to Round 5?" without manually correlating across PRs, file contents, and CI output. A pass checklist gives the human (and the LLM, on resuming a session) a single place to skim.

## What it is NOT

**The checklist is auxiliary, not authoritative.** If `pass-1.md` says "Round 4 done" but `spec/round-4/interactions.json` is empty, the file is wrong — **the spec wins.** CI does not validate the checklist; it's an aide-memoire.

This means:
- Don't gate decisions on the checklist alone — re-check the spec content before tagging a pass
- Don't bother CI-validating the checklist; it's intentionally informal
- If checklist and spec ever conflict, fix the checklist (it's recovery, not signal)

## When to update

The driver should refresh `pass-N.md` at these moments:
- After merging a PR (tick off the relevant items, append the PR URL)
- At end of each session (so the next session resumes cleanly)
- When a blocker emerges (record it explicitly so the human sees it)
- Before asking for pass closure (verify the closure-conditions section is accurate)

A stale checklist defeats its purpose. Better an honest "I'm not sure where we are; let me re-check the spec" than a confidently-wrong checklist.

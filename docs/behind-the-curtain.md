# Behind the curtain

## Specs Sense / 3 — Physical implementation ##

Where this fits: this file describes how the algorithm becomes a runnable system — storage formats, directory structure, human review surfaces, diff conventions, and the orchestrator/agent architecture. The conceptual framing is in [i-see-dead-specs](i-see-dead-specs.md). The algorithm itself is in [its-elementary](its-elementary.md). Connecting spec to code is in [ghosts-in-the-code](ghosts-in-the-code.md).

## Storage format

Artifacts are stored in formats chosen per type for both machine reliability and human reviewability.

- **JSON with JSON Schema** for all structured artifacts (rounds 1–4, 6–8, Hoare contracts, test metadata, diff annotations). JSON Schema is natively supported by LLM structured-output APIs, which constrain agents to emit only valid records and eliminate whole classes of hallucination at generation time.
- **Quint** (`.qnt`) for formal invariants (round 5).
- **Implementation-language code** for test bodies, with JSON metadata wrappers.
- **Markdown** for genuinely prose artifacts (scope declaration, glossary, long-form narrative fields not tied to a specific structured field).
- **Auto-generated markdown views** in `.views/rendered/` for human reading. These are regenerated from the structured sources on every commit and are never the source of truth.

The source of truth is always the structured JSON or Quint file. Humans review through the rendered views and PR diffs; direct JSON edits happen at PR authoring time, not during review.

### Why not YAML or other formats

JSON wins over YAML for this use case for several reasons. JSON Schema is the universal interface that every major LLM provider's structured-output API speaks; YAML's structured-output support is less mature. JSON has unambiguous parsing — no significant whitespace, no boolean-vs-string footguns (`NO` becoming false), no version-dependent type inference. JSON has stronger canonicalization, which matters because Git diff quality directly drives review quality. And measured structured-output benchmarks consistently show higher success rates for JSON than for YAML.

The one place YAML would have won — easier hand-editing — barely applies here, because humans review through rendered views and edit JSON only for specific fields they're changing.

## The `_note` convention

Every structured record at meaningful granularity — every entity, state-event cell, partition class, cross-product interaction, invariant, quality sub-attribute, adversarial scenario, assumption, Hoare contract, test case, diff annotation — carries a required `_note` field containing an agent-authored human-language rendering of the record.

### Purpose

The `_note` is a faithful prose translation of what the JSON says, in one or two sentences. The reviewer reading a PR diff sees the sentence and can understand the decision without parsing JSON. If the sentence and the data appear to disagree, the reviewer drills into the JSON to resolve the doubt — but in the common case, reading the sentence is enough. This makes diff review viable for stakeholders who do not read JSON fluently and faster for those who do.

### Rules

- **Render, do not add.** The note restates the record's content as a sentence. It must not introduce facts absent from the JSON, and it must not omit facts that materially change the meaning. If the note says something the data does not, or the data says something the note does not, the two are out of sync and CI flags the mismatch.
- **Cover the whole record, not just some fields.** Selective omission is a bug.
- **Plain, concrete language.** Reference field values by their meaning, not their internal names.
- **Include IDs when the record references other artifacts.** The referential-integrity checker validates these IDs.
- **Length discipline: 40–300 characters.** One to three short sentences. If a record is too complex to render in 300 characters, the record itself is probably too complex and should be split.

Separate from `_note`: fields like `rationale` and `rejection_reason` carry the *why* — the reasoning behind the decision. These are distinct fields, present only where needed, and may be longer. `_note` is only about what the record says, not why it says it.

### Example

```json
{
  "id": "C2.VERIFYING.verify_complete_mismatch",
  "state": "VERIFYING",
  "event": "verify_complete_mismatch",
  "next_state": "AWAITING_REVIEW",
  "actions": ["retain_chunk_diff", "alert_security"],
  "rationale": "Mismatch may be transient; auto-failure destroys recoverable backup and forensic evidence.",
  "_note": "When verification finds a full mismatch during VERIFYING, the job moves to AWAITING_REVIEW, retaining the chunk diff and alerting security."
}
```

`_note` describes *what the record says*; `rationale` (separate field) describes *why*. The reviewer reading the diff sees both, with different roles.

The `_note` field participates in diffs as first-class content. A commit that changes data without updating `_note`, or that changes `_note` to no longer match the data, is caught either by CI (an agent-based consistency check that re-reads the record and verifies the note still matches) or at review time as a flag.

## Directory structure

The conventional layout for a Specs Sense repository:

```
spec/
├── scope.md                              # prose
├── glossary.md                           # prose
├── round-1/entities.json, verbs.json, actors.json
├── round-2/<entity>-state-machine.json
├── round-3/<dimension>-partition.json
├── round-4/interactions.json
├── round-5/invariants.qnt
├── round-5/invariant-rationale.json      # _note fields for each invariant
├── round-5/traces/*.txt                  # Quint counterexample output
├── round-6/quality.json
├── round-7/adversarial.json
├── round-8/assumptions.json
├── contracts/<operation>.json            # Hoare contracts
├── tests/metadata/*.json, tests/src/*    # test metadata + code
├── .diff-context/<change-id>.json        # Tier-3 annotations
├── .ci/schemas/*.json                    # JSON Schema files for validation
├── .ci/checks/*                          # referential integrity, coverage, etc.
└── .views/rendered/                      # auto-generated markdown views
```

Directory layout is part of the algorithm, not an implementation detail. Agents and CI checks rely on it.

## Human readback: principles and structure

A specification that cannot be reviewed is not a specification. At the scale Specs Sense produces — hundreds to thousands of individual requirements — raw artifact dumps are unreviewable. Humans skim 200-page documents rather than engage with them. The readback layer converts raw artifacts into something stakeholders can actually process.

### Five principles for every readback

1. **Separate completion from content.** Every readback opens with a status banner: counts of specified versus open items, closure condition state, what changed since last review. A stakeholder sees state-of-completion before reading any requirement.

2. **Surface gaps before details.** Gaps are the reason for the readback. They go first, not buried. A stakeholder who reads only the first page must know every open question.

3. **Chunk by decision scope, not alphabetical order.** Group content by which stakeholder reviews which piece. The security officer should not have to read performance specs to find the security decisions waiting on them.

4. **Show the diff.** Second and subsequent readbacks are reviews of change, not re-reads from scratch. Explicit added/changed/removed sections cut review time by an order of magnitude.

5. **Size each readback to a single sitting.** Each section should fit within 10–15 minutes of focused attention. Larger sections get split.

### Five-section template, reusable across rounds

Every per-round readback follows the same structure:

1. **Status banner.** Counts, closure state, stability metric. One line.
2. **Open items.** Gaps first. Each with: ID, owner, question, current draft, options, rationale.
3. **Changes since last review.** Added, modified, removed. Sized to what is new.
4. **Confirmed / closed items.** Collapsed by default; expandable.
5. **Full artifact.** Linked, not inlined.

The stakeholder reads top to bottom and stops when they have seen what they need. Most iterations, most stakeholders stop at section 2 or 3.

### Per-round readback shapes

Each round adapts the template to its artifact type.

**Round 1 (universe).** Status shows counts of entities, verbs, actors plus quiet rounds toward closure. Open questions identify missing or ambiguous catalog entries.

**Round 2 (state-event matrix).** Status shows cells filled / impossible / open. Open cells foregrounded with current draft and alternatives. Matrix visual uses three colors only: specified (quiet), impossible (neutral), open (loud).

**Round 3 (input partitioning).** Grouped by dimension. Each dimension shows class list, open boundary questions, chosen boundary assignments for re-confirmation. Boundary representatives (just below / at / just above) are called out — most overlooked review items.

**Round 4 (cross-product).** Grouped by interaction family: concurrency, lifecycle overlap, resource contention, temporal ordering. The "pruned as independent" count is reported alongside the specified count.

**Round 5 (formal invariants).** Counterexamples foregrounded with human-readable execution traces. Each counterexample presented as a gap in requirements with a suggested fix.

**Round 6 (quality attributes).** Completion bars per quality dimension. Open items grouped by responsible stakeholder. Non-applicable sub-attributes listed explicitly with rationale.

**Round 7 (adversarial).** Scenarios ranked by severity × likelihood. Unmitigated and partial mitigations foregrounded. Accepted-risk entries show explicit sign-off (who, when).

**Round 8 (assumption).** Critical-severity assumptions foregrounded. Each shows statement, risk if violated, mitigation, status (confirmed / converted to requirement / open with named owner).

**Round 9 (cross-pass).** Delta-only. Trajectory table shows whether the algorithm is converging.

### Master synthesis readback

One document on top of the nine, the executive view:

```
SPECIFICATION STATUS
As of: <date>
Iteration: cross-pass N of expected M

COMPLETION AT A GLANCE
  Round 1  Universe              ████████ stable
  Round 2  State-event matrix    ███████▒ 5 open cells
  Round 3  Input partitioning    ███████▒ 2 open boundaries
  Round 4  Cross-product         ███████▒ 2 open interactions
  Round 5  Formal invariants     ██████▒▒ 1 counterexample
  Round 6  Quality attributes    ██████▒▒ 6 open items
  Round 7  Adversarial           ███████▒ 2 partial, 1 accepted
  Round 8  Assumptions           ███████▒ 3 open
  Round 9  Cross-pass            ██████▒▒ pass N in progress

OPEN DECISIONS — TOTAL BY OWNER AND SEVERITY
  By owner:    ops <n>, security <n>, legal <n>, infra <n>, domain <n>
  By severity: CRITICAL <n>, HIGH <n>, MEDIUM <n>, LOW <n>

CRITICAL ITEMS REQUIRING DECISIONS THIS ITERATION
  [id] <one-line description + owner>
  ...

TRAJECTORY
  Pass N-1 → Pass N: +<e> entities, +<v> events, +<i> invariants, ...
  Projected closure: pass N+k likely final
```


## Diff presentation: Git as substrate

The specification store is a Git repository with structured JSON and Quint files. This choice is not incidental: Git provides versioning, diffs, review workflow, attribution, audit trail, and CI integration as primitives.

### What Git provides natively

- **Versioning.** Every change is a commit with author, timestamp, message, parent. Branching and merging are built in. Rollback is `git revert`.
- **Diffs.** Unified format, rendered with syntax highlighting and inline comments by GitHub, GitLab, Gitea.
- **Review workflow.** Pull requests as the propose / review / discuss / decide pattern.
- **Attribution and audit.** `git blame` per line. Regulated domains accept this because it is the same tooling they trust elsewhere.
- **CI integration.** Every push runs hooks: schema validation, referential-integrity checks, the Quint model checker, test-to-spec traceability. Closure conditions become CI gates.
- **Search and navigation.** `git log`, `git grep`, IDE integration without extra infrastructure.

### What Git does not cover, and the thin layer that fixes it

**Spatial and dependency context.** Git's unified diff shows lines before and after the change within the same file. The specification review needs richer context — sibling cells in the same matrix, dependent invariants in other files. *Fix:* a pre-commit or CI hook generates a structured annotation file (`.diff-context/<change-id>.json`) alongside each substantive change. The reviewer still reviews in the PR interface; the annotation appears as a linked file or is rendered into the PR description by a bot.

**Cross-file traceability.** *Fix:* an enforced ID convention (every entity, cell, invariant, test, assumption has a stable ID) plus a referential-integrity checker run in CI. A commit that breaks a reference fails CI.

**Per-stakeholder views and severity triage.** *Fix:* a small script reads PR labels and commit metadata, generates per-stakeholder summary comments. Git provides the data; the script projects it.

### Six questions every diff entry answers

These are content requirements, independent of tooling.

1. **What changed?** Before and after, side-by-side. (Git handles this natively.)
2. **Why?** Rationale citing the round, stakeholder, or input that forced it.
3. **What is around it?** Spatial context — sibling cells, neighboring classes, related attributes.
4. **What breaks or shifts downstream?** Dependencies: requirements, tests, costs, assumptions.
5. **What was considered and rejected?** Alternatives with pros/cons and rejection rationale.
6. **What is the decision?** Expressed as PR state: approved, changes requested, discussion open, draft.

### Three-tier view model

Like Git itself has `--stat`, default unified view, and `-p` with custom context, requirements review uses three zoom levels — each a projection of Git state.

**Tier 1 — summary line.** `git log --oneline` or PR list view. Commit messages structured: `[Round.ID] SEVERITY kind: subject`.

```
3f2a1b  [R2.C2.7] HIGH MODIFIED  VERIFYING × mismatch: FAILED → AWAITING_REVIEW
9c4d8e  [R3.C3.2] MED  BOUNDARY  VM size Large/Huge: 10TB → 5TB
2a9f15  [R5.C5.1] HIGH INVARIANT KMS key retention (from Quint counterexample)
4e6c33  [R8.C8.3] CRIT ASSUMPTION A18 restore testing: owner unassigned
```

**Tier 2 — unified diff.** Default `git diff` or PR diff view. JSON structure plus `_note` means the reviewer reads the sentence and understands the decision without parsing JSON.

```diff
  # round-2/backup-job.json
   {
     "id": "C2.VERIFYING.verify_complete_mismatch",
     "state": "VERIFYING",
     "event": "verify_complete_mismatch",
-    "next_state": "FAILED",
-    "actions": ["delete_snapshot", "alert_on_call"],
-    "rationale": "Mismatch indicates corruption; fail fast to surface the problem.",
-    "_note": "When verification finds a full mismatch during VERIFYING, the job moves to FAILED, deleting the snapshot and alerting on-call."
+    "next_state": "AWAITING_REVIEW",
+    "actions": ["retain_chunk_diff", "alert_security"],
+    "rationale": "Mismatch may be transient; auto-failure destroys recoverable backup and forensic evidence.",
+    "_note": "When verification finds a full mismatch during VERIFYING, the job moves to AWAITING_REVIEW, retaining the chunk diff and alerting security."
   }
```

**Tier 3 — structured annotation.** Generated by a pre-commit hook into `.diff-context/<change-id>.json`. Linked from the commit body and rendered by the PR bot. Full six-question expansion.

```json
{
  "change_id": "C2.7",
  "round": 2,
  "severity": "HIGH",
  "commit": "3f2a1b",
  "status": "awaiting_review",
  "affected_artifact": "round-2/backup-job.json",
  "_note": "Change C2.7 modifies the VERIFYING × verify_complete_mismatch cell from FAILED to AWAITING_REVIEW. Severity HIGH, awaiting review.",

  "before": {"next_state": "FAILED", "actions": ["delete_snapshot", "alert_on_call"]},
  "after":  {"next_state": "AWAITING_REVIEW", "actions": ["retain_chunk_diff", "alert_security"]},
  "rationale": "Mismatch may be transient; auto-failure destroys recoverable backup and forensic evidence.",

  "spatial_context": {
    "same_row": [
      {"event": "verify_complete_match", "next_state": "SUCCEEDED"},
      {"event": "verify_partial_match", "next_state": "AWAITING_REVIEW"},
      {"event": "verifier_unavailable", "next_state": "VERIFYING"}
    ],
    "_note": "In the same row, match → SUCCEEDED, partial_match → AWAITING_REVIEW, verifier_unavailable → VERIFYING."
  },

  "depends_on_this": {
    "requirements": ["R2.34", "R5.INV4"],
    "tests_obsoleted": ["C2.7a"],
    "_note": "Requirements R2.34 and R5.INV4 reference this cell. Test C2.7a is obsoleted."
  },

  "alternatives": [
    {"option": "keep_failed", "selected": false,
     "rejection_reason": "3 prior incidents where auto-fail discarded useful data."},
    {"option": "awaiting_review", "selected": true},
    {"option": "auto_retry_then_fail", "selected": false,
     "rejection_reason": "Does not preserve forensics for non-transient mismatches."}
  ],

  "decision": {"tracked_via": "PR #142", "awaiting_review_from": ["@ops-lead", "@security-officer"]}
}
```

Reviewers start at Tier 1, drop to Tier 2 for changes that matter to them, and only open Tier 3 when something looks off or the change is CRITICAL.

### Pass-over-pass aggregate diff

A bot queries Git history between two tagged iteration boundaries:

```
PASS-OVER-PASS DELTA

                        Pass 2   Pass 3   Pass 4
  Entities              23       +3→26    +0→26
  Verbs                 18       +0→18    +0→18
  Events                28       +2→30    +1→31
  State cells filled    340      +20→360  +0→360
  Open cells            8        -3→5     -0→5
  Invariants            8        +4→12    +0→12
  Counterexamples open  2        -1→1     -0→1
  Assumptions           20       +3→23    +0→23
  Open assumptions      5        -2→3     -0→3

  Trajectory: converging. Pass 5 projected final.
```

Each row is itself a diff. The reviewer sees convergence as a first-class signal.

### Review workflow affordances, all PR-native

- **Inline decisions.** PR reviews: approve / request changes / comment.
- **Dependency collapse.** When a change breaks N downstream items, the referential-integrity checker flags them. A bot opens a linked draft PR with proposed downstream updates.
- **Reviewer attribution.** Native Git attribution. `git blame`, PR review metadata.
- **Open-item persistence.** Rejected or deferred changes remain as closed or draft PRs, indexed by label.
- **Cross-reviewer flags.** PRs labeled per affected stakeholder role; bot assigns reviewers per label.

### Per-stakeholder filtered view

```
YOUR OPEN ITEMS — @ops-lead, pass 4
(3 PRs awaiting your review, 2 blocked on others)

  #142  HIGH   [R2.C2.7] VERIFYING × mismatch behavior change
  #145  MED    [R3.C3.2] VM size threshold 10TB → 5TB
  #151  CRIT   [R8.C8.3] A18 restore testing owner

BLOCKED ON OTHERS
  #139  CRIT   [R7] Ransomware mitigation — awaiting @security-officer
  #148  MED    [R6.Q6.5] GDPR cryptoshred — awaiting @legal
```

### Sizing discipline for diffs

Even with Git, diffs accumulate. Four disciplines keep review load bounded.

- **Batch by severity.** CRITICAL synchronous; MEDIUM async over days; LOW spot-checked.
- **Diff the diff.** Show what changed in the review itself since last time — new comments, new decisions.
- **Decision decay.** Open items that sit too long auto-escalate. After 7 days, CRITICAL becomes a blocking banner.
- **Severity × age prioritization.** Next iteration's digest sorts by (severity × age), oldest critical first.

## Execution architecture

The algorithm is finite and terminates. In practice, a single AI session cannot execute it — session state is context-bounded, single-threaded, and ephemeral, and cannot span the weeks of iteration the algorithm requires. The problem is not solved by larger context windows; concurrency, durability, and asynchronous stakeholder input are mismatches at a different level than memory size.

The correct frame: the AI is a tool used by a system, not a single agent running end-to-end. Individual AI calls do narrow, context-fitting tasks; the system holds state, schedules work, and presents humans with the readback-and-diff interface above.

### Two components on Git

The execution architecture has two components — orchestrator and agent fleet — running on top of Git as the substrate.

**Substrate: Git repository.** Single source of truth for every artifact. All catalogs, matrices, partitions, invariants, scenarios, assumptions, tests, and annotations live as JSON or Quint files in the repo. Every change is a commit; every iteration is a tag. The review workflow is PRs. There is no separate database.

**Orchestrator.** A small deterministic program (not an LLM) that schedules work. It knows which round is running, which sub-tasks are dispatched to which agents, which closure conditions are met, and when to trigger the next round. It does not reason about requirements; it routes tasks to agents, commits their outputs to the repo via PRs, and collects decisions back. The orchestrator is stateless — it reads and writes Git but does not maintain its own state.

**Agent fleet.** Specialized LLM agents, each invoked with a narrow task. No single agent sees the whole specification. Each gets a slice of the repo (specific files, specific IDs), produces a focused output (a proposed commit with annotation), and returns. The orchestrator opens a PR with the agent's output; reviewers handle it through normal PR workflow.

### Decomposition per round

Each round decomposes into agent-sized units that produce PR-sized changes.

**Round 1 (universe).** Split extraction across agents: one proposes new entities given the informal requirement and the current `round-1/entities.json`; another enumerates attributes given an entity; a third proposes value ranges given an attribute. Each agent produces a JSON patch against its target file. Parallel PRs; merge at review.

**Round 2 (state-event matrix).** The matrix factors naturally. One agent per state or per event: produce a cell (or row of cells) in `round-2/<entity>-state-machine.json`. Each cell fits in context, is independently verifiable, and carries its own `_note`. The orchestrator collects cell PRs and flags empty cells via CI check.

**Round 3 (partitioning).** One agent per input dimension, producing a patch against `round-3/<dimension>-partition.json`. Independent per dimension.

**Round 4 (cross-product).** Orchestrator enumerates entity pairs, prunes obvious non-interactions with a lightweight classifier agent, and dispatches remaining pairs to detailed-analysis agents. Each agent sees only two entity files and their state machines.

**Round 5 (formal invariants).** One agent per invariant, editing `round-5/invariants.qnt` plus the corresponding rationale entry in `round-5/invariant-rationale.json`. A non-LLM CI job runs the Quint checker on every push. Counterexamples are committed to `round-5/traces/` and dispatched to a counterexample-interpreter agent that opens a follow-up PR proposing a fix.

**Round 6 (quality attributes).** Parallelize by quality dimension. Each agent works against a known checklist template for its quality, editing its section of `round-6/quality.json`.

**Round 7 (adversarial).** One agent per STRIDE category, each producing entries in `round-7/adversarial.json`. Deduplication happens at PR review.

**Round 8 (assumptions).** One agent per category, each producing entries in `round-8/assumptions.json`.

**Round 9 (cross-pass).** Orchestrator dispatches delta-discovery agents per round: given the last iteration's tag and the current HEAD, what new gaps does the delta expose? Each agent opens PRs for the gaps it finds.

### Orchestrator state machine

```
WAITING_FOR_INPUT → R1_IN_PROGRESS → R1_IN_REVIEW → R2_IN_PROGRESS → ...
                                   ↓
                              R1_STAKEHOLDER_FEEDBACK
                                   ↓
                              R1_IN_PROGRESS (revised)
```

Closure conditions are Git queries or CI checks: "are there three consecutive iteration tags with no new entries in `round-1/entities.json`?", "does CI pass the state-event-completeness check?", "does `quint verify` pass on the HEAD of `round-5/invariants.qnt`?" These are mechanical checks, not judgment calls.

Stakeholder decisions are PR events (merged, closed, comments with specific labels) consumed via webhooks. A merged PR is an accepted change; a closed-without-merge PR is rejected; a `needs-rework` label triggers an agent to revise and re-push.

### Agent contract

Each agent invocation has a strict shape.

1. **Scope.** Narrow and specific. "Analyze interaction between entity A and entity B" is valid; "review the whole spec" is not.
2. **Context budget.** Bounded. The orchestrator computes the minimum viable context — relevant files, referenced IDs, recent changes — and provides only that.
3. **Output schema.** Structured JSON conforming to the repo's JSON Schema. Schema validation runs in CI. LLM structured-output APIs are used where available so schema is enforced at generation time, not only at commit time.
4. **Faithful prose rendering via `_note`.** Every structured record produced must include a `_note` field (40–300 chars) rendering the record's content as a human-readable sentence. The note must match the data — not add facts beyond it, not omit facts within it. Separate fields (`rationale`, `rejection_reason`) carry *why*; `_note` carries *what the record says*.
5. **Uncertainty flag.** The agent must mark PR-level uncertainty. High-uncertainty PRs get a label that routes them to a human reviewer first or to a second-opinion agent.
6. **No hidden state.** The agent does not remember previous invocations. Everything it needs comes from Git; everything it produces goes to Git.

This contract is what makes the fleet reliable. Each invocation is reproducible (re-run with same inputs produces equivalent PR), auditable (Git history is complete, rationale colocated with data), and bounded (context budget is enforced). Failures localize — a garbage output triggers a retry or human routing via the PR, not cascading spec corruption.

### Sessions over time

The algorithm runs over weeks. Agent sessions are spawned as needed and discarded. Continuity lives in Git, not in any session's memory.

A specific iteration: orchestrator queries Git for open state-event cells in `round-2/`; finds 5; dispatches 5 agent tasks, one per cell, each with just that cell's file and neighbors as context; collects 5 PRs; labels them by affected stakeholder; digest bot notifies the ops lead; ops lead reviews 5 PRs in their dashboard, merges 3, requests changes on 1, closes 1; CI re-runs affected Quint invariants and traceability checks; any new counterexamples open follow-up PRs; cycle continues.

A human never waits on the system; the system waits on humans. Agents run asynchronously while humans sleep; PRs accumulate; stakeholders open their digest over coffee and spend 30–45 minutes on decisions.

### Failure modes and mitigations

**Agents disagree.** Two agents open PRs that modify the same region. Standard Git merge conflict. Resolution is a specific agent type: given two PRs and their annotations, either produce a reconciling PR or escalate to a human with a crisp question.

**Agents hallucinate.** An agent proposes a PR that references a non-existent entity ID, or invents an invariant. CI referential-integrity check fails; PR is blocked from merge. The orchestrator sees the failing check and either retries the agent with corrective context or routes to a human. Schema validation in CI is the single most important defense against this failure mode.

**Agents miss things.** A Round 7 agent fails to generate a scenario a human would have thought of. Mitigations: run multiple agents with different prompts against the same context and diff their outputs; have a human spot-check rate that samples PRs for missing coverage.

**Humans change their minds.** A stakeholder merges C2.7, then two weeks later wants to revert. `git revert` creates a new commit undoing the earlier decision. Downstream CI re-runs and identifies what else needs to change. History is preserved.

**Orchestrator bugs.** The orchestrator is a program written by humans and can be wrong. Keep it small and deterministic. Do not let LLMs write the orchestrator logic; let them write artifacts that the orchestrator shuffles. Because the orchestrator is stateless, a buggy orchestrator can be rolled back and re-run without data loss.

## What's next

The architecture above produces a behaviorally complete specification, reviewable by humans, evolved through PR workflow, validated by CI. The next question is how the actual implementation code respects that specification — and what to do when you start with code that has no specification yet. Both are covered in [ghosts-in-the-code](ghosts-in-the-code.md).

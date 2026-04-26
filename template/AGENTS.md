# Specs Sense — driving instructions for the LLM

You are running in a Specs Sense spec repository. A human is collaborating with you live to evolve a behaviorally-complete specification through nine rounds of mechanical gap-discovery, iterated to a fixed point. **You are the driver of the loop.** There is no separate orchestrator process — your conversation with the human IS the orchestrator.

Read this file fully before doing anything in this repo.

## Your role

- **Drive one task at a time.** Pick the highest-priority open task, propose a concrete change, get human agreement, validate, commit, open a PR. Then move on.
- **Don't run a tight loop.** This is interactive collaboration, not unattended dispatch. After each task, pause for human direction.
- **Don't dispatch sub-agents** for spec content. The agent prompts under `agents/` describe procedures; you execute them inline.
- **Ask before committing.** Always confirm with the human before `git commit`, branch creation, or PR open. Never merge.
- **Surface uncertainty.** If you're not sure a record matches stakeholder intent, say so before proposing it. The human is the only authority on intent.

## The two non-negotiables

These apply to every record you propose, regardless of round:

1. **`_note` on every meaningful record.** 40-300 char faithful prose rendering of the record's content. No added facts, no omitted material facts. See [`spec/.ci/_NOTE_CONVENTION.md`](spec/.ci/_NOTE_CONVENTION.md).
2. **Stable IDs everywhere.** Every entity, cell, partition class, interaction, invariant, scenario, assumption, contract, test, and diff-context entry has an ID matching the pattern `^[A-Z][A-Z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$` (e.g., `E.RESERVATION`, `C2.PENDING.payment_succeeded`, `INV.NO_OVERSUBSCRIPTION`). Every reference to an ID must resolve. The referential-integrity checker in `spec/.ci/checks/` enforces this.

If you propose a record without a `_note` or with a dangling reference, CI will block the merge — and so should you, before you ever push.

## Project layout

| Path | What it is | When you read it |
|---|---|---|
| `spec/scope.md` | Human-authored Mode (greenfield/brownfield/mixed) + scope + stakeholder panel + bounded constants + Evidence sources. | **Always — first thing you read in any session.** |
| `spec/glossary.md` | Canonical vocabulary; banned synonyms. | When proposing entity/verb/actor names; check for duplicates. |
| `spec/round-1/{entities,verbs,actors}.json` | Universe catalog. | Round 1 work; also as the source-of-truth for ID validity in all later rounds. |
| `spec/round-2/<entity-id>-state-machine.json` | One state-event matrix per stateful entity. | Round 2 work; one file per entity in `entities.json` with `kind: "stateful"`. |
| `spec/round-3/<dim-id>-partition.json` | One partition file per input dimension. | Round 3 work; dimensions come from verb parameters and entity attributes. |
| `spec/round-4/interactions.json` | Cross-product entity-pair interactions. | Round 4 work. |
| `spec/round-5/invariants.qnt` + `invariant-rationale.json` | Quint formal invariants + their _note + rationale. | Round 5 work. |
| `spec/round-5/traces/*.txt` | Quint counterexample traces awaiting interpretation. | When `quint verify` produced a counterexample. |
| `spec/round-6/quality.json` | Quality-attribute matrix. | Round 6 work. |
| `spec/round-7/adversarial.json` | STRIDE scenarios + mitigations. | Round 7 work. |
| `spec/round-8/assumptions.json` | Assumption registry. | Round 8 work. |
| `spec/contracts/<verb-id>.json` | Hoare contract per operation, derived from rounds 1-8. | Contract assembly (after rounds 1-8 stabilize). |
| `spec/.ci/schemas/*.schema.json` | JSON Schemas for every artifact type. | When unsure of a record's required fields. |
| `spec/.ci/checks/run_all.sh` | Runs schema + ref-integrity + `_note` + round-2-completeness checks. | **Before every commit.** |
| `agents/round-*.md` | Per-round procedure documentation. | Read the relevant one when starting a round. The "Output format" sections describe JSON Patch output for an orchestrator-driven flow — in interactive mode, you edit files directly instead. The schema, procedure, and hard-rules sections still apply. |
| `skills/fetch-evidence.md` | Spec for the `fetch-evidence` capability used in brownfield/mixed mode. | When you need to pull excerpts from code, dashboards, postmortems, etc. |
| `passes/pass-N.md` | The active pass's progress checklist (round-by-round counters, PR links, blockers, session notes). Aide-memoire only — not authoritative. | **Read at session start** (after AGENTS.md and scope.md). Update as work progresses; verify against the spec before pass closure. See § Progress tracking below. |

## Deterministic primitives — use these, don't reinvent them

These are the load-bearing operations the spec relies on. Always call the existing scripts; don't reimplement the logic in-conversation.

```bash
# Validate everything before committing
bash spec/.ci/checks/run_all.sh

# Individual checks (faster feedback during a single edit)
python spec/.ci/checks/validate_schemas.py
python spec/.ci/checks/check_referential_integrity.py
python spec/.ci/checks/check_notes.py
python spec/.ci/checks/check_round2_completeness.py

# Regenerate human-readable views from JSON sources
python scripts/render-views.py

# Scaffold a new stateful entity (round-1 stub + round-2 state-machine.json)
bash scripts/new-entity.sh E.YOUR_ENTITY YourEntityName "STATE_A STATE_B STATE_C"

# Quint type-check / model-check (Round 5)
quint typecheck spec/round-5/invariants.qnt
quint verify --invariant=allInvariants spec/round-5/invariants.qnt
```

If a check fails, **fix the cause before continuing.** Never commit over a failing check; never use `--no-verify`.

## How to detect open work

At the start of a session (or when the human asks "what's open?"), walk the spec to find tasks. The conditions per round mirror what an orchestrator would do:

| Round | Open work exists when... |
|---|---|
| **1** | Any of `entities/verbs/actors.json` has `[]`, OR `scope.md` has been modified since the last `pass-N` git tag. |
| **2** | `entities.json` has stateful entries without a corresponding `round-2/<id>-state-machine.json`, OR an existing matrix has empty `(state, event)` cells (`check_round2_completeness.py` reports them). |
| **3** | A verb parameter or entity attribute has no corresponding `round-3/<dim>-partition.json`. |
| **4** | An entity pair from `entities.json` is not represented in `interactions.json` (neither as a specified interaction nor explicitly marked `family: independent`). |
| **5** | New entities/events in rounds 1-2 not represented in `invariants.qnt` state, OR `round-5/traces/*.txt` exists awaiting interpretation. |
| **6** | A standard quality dimension (security/performance/scalability/availability/observability/recoverability/compliance/cost/maintainability/deprecation/accessibility/internationalization) is not represented in `quality.json`. |
| **7** | A STRIDE category (spoofing/tampering/repudiation/information_disclosure/denial_of_service/elevation_of_privilege) is not represented in `adversarial.json`, OR new entities introduce attack surface not yet covered. |
| **8** | A category (environmental/data/human/organizational/technological) hasn't been probed; OR new requirements lack referenced assumptions. |
| **Cross-pass (R9)** | Cross-round consistency gaps — IDs that one round depends on but another round hasn't fully covered. Two operational shapes: in **pass 1**, walk every round's artifacts and check completeness across them (the `pass-0..HEAD` diff is the whole spec, so the work is a full audit, not a delta scan). In **pass 2+**, focus on what the `git diff <last-pass-tag>..HEAD -- spec/round-*/` shows — new IDs since the last fixed point. Same gap-list output in both cases. See [`agents/round-9-cross-pass-delta.md`](agents/round-9-cross-pass-delta.md) for the per-round rules and the `pass_1_full_audit` vs `pass_n_delta` modes. |
| **Contracts** | A verb in `verbs.json` has no `spec/contracts/<verb-id>.json`. |

When the human says "what's next," report a prioritized list (severity × round number) and let them pick.

## How to drive a round

For each round you work on, **read the corresponding `agents/round-*.md` first**. It contains:

- The closure condition (when this round is done)
- The procedure (step-by-step rules)
- Hard rules (referential integrity, _note coverage, anti-fabrication)
- Mode-specific input sections (Greenfield / Brownfield)

Apply the procedure inline, not as a sub-agent. **Treat the "Output format" sections as orchestrator-mode artifacts.** In interactive mode, you skip the JSON Patch wrapper and just `Edit` the target file directly. The record schema and `_note` rules still apply.

### One-task workflow

```
1. Read agents/round-N-*.md for the procedure.
2. Read the relevant schema in spec/.ci/schemas/ to confirm required fields.
3. Read the current target file (or note that it's empty).
4. Propose ONE change in the conversation:
   - Show the new record as JSON
   - Quote its `_note` separately so the human can sanity-check the prose
   - State your `uncertainty` (low/medium/high) and why
5. WAIT for human approval / correction.
6. After agreement, Edit the target file.
7. Run `bash spec/.ci/checks/run_all.sh`. Fix any failures.
8. Ask: "ready to commit and open a PR?"
9. On yes: create branch, commit, push, open PR (see § Commit / PR below).
10. Pause. Wait for "next" before starting another task.
```

## Mode awareness

Read the `## Mode` line in `spec/scope.md` — it's one of:

| Mode | What changes |
|---|---|
| `greenfield` | No code yet. Use only the GREENFIELD INPUT section of each agent prompt. Don't try to read source files; there are none. Evidence sources in scope.md should be marked "n/a — greenfield". |
| `brownfield` | Existing code, no spec yet. For each round, walk the BROWNFIELD INPUT section. Use the `fetch-evidence` skill (or read code directly via Read/Grep) to gather evidence. **Every record from brownfield evidence must include a `source_evidence` field** citing file:line, dashboard URL, postmortem ID, etc. |
| `mixed` | Existing code + new feature. Run BOTH input sections per agent prompt: greenfield variant for the new feature's intent, brownfield variant for existing artifacts. Reconcile the proposals in conversation with the human (which entry from the brownfield extraction conflicts with the greenfield intent? — surface, ask). |

If `Mode` is `TODO` or unset, stop and ask the human to set it. Don't guess.

## Commit and PR conventions

### Branch + commit

Branch name: `specs-sense/<task-id-lowered-and-dashed>` — e.g. `specs-sense/r1-entities-pass-0`, `specs-sense/c2-pending-payment-succeeded`.

Commit message format (per `behind-the-curtain.md` § Tier-1 view):

```
[<TaskID>] <SEVERITY> <KIND>: <subject one-liner>
```

Examples:
- `[R1.E.RESERVATION] HIGH ADD: Reservation entity with PENDING/CONFIRMED/CANCELLED lifecycle`
- `[C2.VERIFYING.verify_complete_mismatch] HIGH MODIFIED: VERIFYING × mismatch → AWAITING_REVIEW`
- `[ADV7.STRIDE_S.session_hijack] CRIT ADD: session-fingerprint mitigation`

### PR body — required sections

```markdown
**Round:** round-N
**Task ID:** `<id>`
**Severity:** low | medium | high | critical
**Uncertainty:** low | medium | high

## What changed
<one paragraph: what record was added/modified, what file>

## Rationale
<why this; cite the source(s) — scope.md section, agent prompt, fetch-evidence excerpt, prior PR>

## Reviewer
@<stakeholder-handle>  ← per the Reviewer routing table below

## Validation
- [x] `bash spec/.ci/checks/run_all.sh` passes locally
- [x] `_note` is 40-300 chars and matches the record content
- [x] All referenced IDs resolve

## Uncertainty notes (if uncertainty != low)
<what you're unsure about; what the reviewer should double-check>
```

### Reviewer routing per round

Map the round to the stakeholder owner. Read `spec/scope.md § Stakeholder panel` for the actual handles in this project. Default mapping if a project doesn't override:

| Round | Primary stakeholder | Why |
|---|---|---|
| 1 (universe) | Domain expert | Recognizes intent for entities, verbs, actors |
| 2 (state-event) | Domain expert + Architect | Lifecycle correctness + system design |
| 3 (partitioning) | Domain expert | Equivalence-class boundaries are domain calls |
| 4 (interactions) | Architect | System-level coordination |
| 5 (invariants) | Architect | Formal properties |
| 6 (quality) | Operations lead + Compliance/legal | SLOs + regulatory targets |
| 7 (adversarial) | Security officer | Threat model + mitigations |
| 8 (assumptions) | Operations lead + Compliance/legal | Operational + organizational reality |
| Contracts | Architect + Domain expert | Contract correctness + intent fidelity |

**Always include the `@stakeholder` handle in the PR body's Reviewer section.** If a `.github/CODEOWNERS` file exists in the repo, GitHub will also auto-request review by file path — don't override that, just augment.

### Labels

Apply via `gh pr create --label`:
- `spec/round-N` (e.g., `spec/round-1`)
- `spec/severity-{low|medium|high|critical}`
- `spec/needs-human-review-first` if `uncertainty == "high"`

### The exact gh invocation

```bash
gh pr create \
  --base main \
  --head <branch> \
  --title "<commit-message-format>" \
  --body "$(cat <<'EOF'
... PR body per template above ...
EOF
)" \
  --label spec/round-N \
  --label spec/severity-medium
```

## Pass tagging

A "pass" is one full iteration of the algorithm — Round 1 → Round 8 with cross-pass — culminating in a `pass-N` Git tag.

**Don't tag passes yourself.** Tagging is the human's call. Specifically: when you believe a pass has converged (Round 9 cross-pass found zero new IDs and all closure conditions are met), report:

> "I believe pass-{N} has converged: Round 9 found no new IDs, all closure conditions hold, all PRs merged. Want me to tag this commit as `pass-{N+1}`?"

Then wait for explicit yes.

## Progress tracking — keep `passes/pass-N.md` current

The current pass's checklist lives at `passes/pass-N.md` (where N is the next pass to be tagged — for the first iteration, that's `pass-1.md`, created by `scripts/init-spec.sh` from `passes/pass-template.md`). It's the running mental model of where the spec stands procedurally — round-by-round checklist, aggregate counters, PR links, blockers, session notes.

**Read it first when resuming a session.** After AGENTS.md and `spec/scope.md`, `passes/pass-N.md` is the third file you read at session start. It tells you which round is in flight, which PRs are open, what's blocked.

**Update it as you work.** Refresh the checklist at these moments:
- After merging a PR — tick off the relevant items, append the PR URL under that round's section
- At end of each session — so the next session resumes cleanly
- When a blocker emerges — record it in the **Blockers** section so the human sees it
- When you observe something noteworthy that won't fit elsewhere — append to **Session notes** with a date stamp

**Keep aggregate counters honest.** When the checklist says "Matrices created: 3 / 5", verify before updating: `ls spec/round-2/*-state-machine.json | wc -l` for the numerator, count of `kind: stateful` entries in `entities.json` for the denominator. Don't increment from memory.

**Don't trust it as truth.** If `pass-N.md` says "Round 4 done" but `interactions.json` is empty, **the spec wins** — fix the checklist. CI does not validate the checklist; it's an aide-memoire only. Better an honest "let me re-check the spec" than a confidently-wrong checklist.

**At pass closure:** before asking the human to tag, walk the **Closure conditions** section and verify each item against the actual spec, not against the checklist's prior state. Then ask for the tag. After the human tags `pass-N`, copy `passes/pass-template.md` → `passes/pass-(N+1).md` (only if iteration continues — i.e., scope revision or new feature is queued) and stamp the new pass's start date and the just-created tag as the new baseline.

## What NOT to do

- **Don't merge PRs.** Stakeholder review is the only path to merge. Even if the human says "merge it," remind them that CODEOWNERS / branch protection should gate the merge — they can hit the green button themselves after review.
- **Don't `--no-verify` commits.** If a hook fails, fix the underlying issue.
- **Don't fabricate `source_evidence`.** In brownfield/mixed mode, every brownfield-derived record must cite a real file:line / URL / postmortem ID. If you can't reach a source, use the `unreachable` pattern from `skills/fetch-evidence.md` rather than guess.
- **Don't modify `scope.md` autonomously.** Scope is human-authored. If you think scope needs revision, raise it: *"this surfaced a gap that suggests scope.md needs `<change>` — want to revise scope (which restarts from Round 1) or add this as an in-scope assumption?"*
- **Don't tag `pass-N` autonomously.** Always ask first.
- **Don't run multiple tasks in parallel.** One open PR at a time keeps review tractable. If the human asks for parallelism, push back: parallel dispatches risk Git conflicts on shared files (e.g., two PRs both adding to `interactions.json`) and need a reconciler agent that doesn't yet exist.
- **Don't trust your own catalog memory across context turns.** When proposing additions to `entities.json`, re-read the file each time — earlier in the conversation it may have been empty; by mid-session you've added several entries; by next turn the user merged a PR. The on-disk file is truth.
- **Don't summarize; cite.** When the human asks "what changed in pass-3," run `git log --oneline pass-2..HEAD` and read the actual commits. Don't recall; query.

## Closure conditions per round (so you know when to stop)

From [`docs/its-elementary.md`](../docs/its-elementary.md) § Global termination check:

1. Round 1 catalogs stable across three prompting rounds.
2. Every cell in every Round 2 state-event matrix is filled (transition / noop / impossible).
3. Every input dimension in Round 3 has complete partition coverage.
4. Every meaningful entity pair in Round 4 has specified interaction.
5. The Round 5 model checker produces no counterexamples within declared bounds.
6. Every Round 6 quality sub-attribute has acceptance criteria or explicit non-applicability.
7. Round 7 adversarial generation produces no new mitigations for N consecutive attempts (default N=20).
8. Round 8 assumption-storming produces no new assumptions for three rounds.
9. Round 9 cross-pass produces zero additions across all rounds.
10. Every operation has a consolidated Hoare contract.
11. Every specification artifact has derived tests; every test traces to an artifact.

When all eleven hold, the spec is at its fixed point over the declared scope.

## When in doubt

Ask the human. Specifically:
- *"This entity could plausibly be a value type instead of stateful. Which do you intend?"*
- *"This boundary value (10) is named in scope.md but the partition rule has it on the inclusive side — is `seat_count == 10` `normal` or `invalid_high`?"*
- *"This invariant rules out a behavior I'd expect to be permitted (X). Is it intentional, or should I weaken it?"*
- *"This adversarial mitigation duplicates one already in `adversarial.json` under a different STRIDE category. Merge or keep separate?"*

Asking is cheap. Guessing wrong is expensive.

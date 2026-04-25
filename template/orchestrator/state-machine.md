# Orchestrator state machine

## What "state" means here

The orchestrator is **stateless across restarts** — Git is the only persistence. State machine below describes the per-task and per-pass progression that the orchestrator infers from Git on each loop iteration. Restarting the orchestrator does not reset anything; it just re-reads Git and resumes.

## Per-task lifecycle

```
                ┌────────────────────────────────────────────────┐
                │                                                │
   detect ────▶ DETECTED ──▶ DISPATCHED ──▶ AWAITING_REVIEW ────┴───▶ MERGED   ──▶ (done — captured by next round-9 delta)
                                  │                  │                │
                                  │                  ├───▶ CHANGES_REQUESTED ──▶ DISPATCHED (re-run with reviewer feedback)
                                  │                  │
                                  │                  └───▶ CLOSED_WITHOUT_MERGE ──▶ (done — rejected, no further action)
                                  │
                                  ├──▶ DISPATCH_FAILED  (LLM error, validation error, gh push failure)
                                  │     └──▶ retried up to N times, then routed to a human
                                  │
                                  └──▶ DEDUPLICATED  (an open PR already covers this task ID; skip this iteration)
```

How each state is detected:

| State                  | Detection rule                                                                                  |
|------------------------|--------------------------------------------------------------------------------------------------|
| DETECTED               | A `detect_round_N(repo)` function returns a Task this loop iteration.                             |
| DISPATCHED             | Orchestrator has called the LLM and is awaiting a response (held only in memory; not persisted). |
| AWAITING_REVIEW        | Open PR exists with label `spec/round-N` and `spec/<task-id>` in its body.                       |
| CHANGES_REQUESTED      | PR carries the `needs-rework` label (set by reviewer).                                           |
| MERGED                 | PR is merged. Subsequent detect cycles no longer find this task open (the artifact now exists).  |
| CLOSED_WITHOUT_MERGE   | PR is closed without merge. The task is treated as rejected; do not re-dispatch this iteration.  |
| DEDUPLICATED           | An existing open PR's branch name matches the deterministic branch we'd push to.                 |
| DISPATCH_FAILED        | LLM returned malformed output, schema validation failed, or `gh` push errored.                   |

## Per-pass lifecycle

A "pass" is one full iteration of the algorithm — Round 1 → Round 8 with cross-pass — culminating in a `pass-N` Git tag.

```
   pass-N → (open work in any round) → DISPATCHING → STAKEHOLDER_REVIEW → MERGE
                          ↑                                                  │
                          └──────────────── more open work? ─── yes ────────┘
                                                  │
                                              no  │
                                                  ▼
                                     ROUND_9_CROSS_PASS ──▶ delta is empty? ──▶ tag pass-(N+1) ──▶ DONE
                                                                │
                                                            no  │
                                                                └──▶ back to DISPATCHING (new tasks from delta)
```

Closure conditions for a pass (per `docs/its-elementary.md` § Global termination check):

1. Round 1 catalogs stable across three prompting rounds.
2. Every cell in every Round 2 state-event matrix is filled.
3. Every input dimension in Round 3 has complete partition coverage.
4. Every meaningful entity pair in Round 4 has specified interaction.
5. The Round 5 model checker produces no counterexamples within declared bounds.
6. Every Round 6 quality sub-attribute has acceptance criteria or explicit non-applicability.
7. Round 7 adversarial generation produces no new mitigations for N consecutive attempts.
8. Round 8 assumption-storming produces no new assumptions for three rounds.
9. Round 9 cross-pass produces zero additions across all rounds.
10. Every operation has a consolidated Hoare contract.
11. Every specification artifact has derived tests; every test traces to an artifact.

When all eleven hold, the orchestrator tags `pass-N+1` and the loop continues to look for new work — typically driven by `scope.md` revisions or new feature additions.

## Round transition rules (CI-gated)

Each round transition is a Git query or CI script — not an LLM judgment. Conditions the orchestrator checks before considering a round closed:

| From → To                     | CI query                                                                                                |
|-------------------------------|---------------------------------------------------------------------------------------------------------|
| Round 1 → Round 2             | `entities.json`, `verbs.json`, `actors.json` non-empty AND no detected round-1 task AND `_note` check passes. |
| Round 2 → Round 3             | `spec/.ci/checks/check_round2_completeness.py` exits 0 for every state-machine file.                   |
| Round 3 → Round 4             | One `<dim>-partition.json` exists per identified input dimension; coverage check passes.               |
| Round 4 → Round 5             | Every meaningful entity pair has an entry in `interactions.json` (specified or `independent`).         |
| Round 5 → Round 6             | `quint verify --invariant=allInvariants round-5/invariants.qnt` exits 0.                                |
| Round 6 → Round 7             | Every quality sub-attribute checklist row is either specified or marked `applicable: false`.            |
| Round 7 → Round 8             | N consecutive STRIDE generation attempts produced no new mitigations (configurable; default N=20).      |
| Round 8 → Round 9             | Three consecutive assumption-storming attempts produced no new assumptions.                             |
| Round 9 → Pass complete       | One full cross-pass produced zero additions in every round AND all CI checks pass on HEAD.              |

Today's MVP detector functions implement the simple version of these (Round 1 fully; Rounds 2-9 stubbed). The CI scripts in `spec/.ci/checks/` are the authoritative gate — the orchestrator's role is to refrain from advancing rounds while they fail.

## Operational notes

- **Restart safety.** The orchestrator can be killed at any point. Open PRs persist; open work re-detects from Git on next start; in-flight LLM calls are lost (the agent emits idempotent JSON Patches, so a re-dispatched task produces an equivalent PR).
- **Concurrency.** The MVP runs one task per pass. `poll.max_parallel_dispatches` in config is a placeholder for a future fan-out — when implemented, two tasks touching the same target file must serialize to avoid Git conflicts.
- **Branch hygiene.** Each task's deterministic branch name (`specs-sense/<task-id>`) means re-dispatching the same task force-recreates the branch only if the original PR was closed; otherwise the orchestrator dedupes.

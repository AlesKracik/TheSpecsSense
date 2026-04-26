# Pass {{N}} — progress checklist

> **DELETE-ME — guidance:** copy this file to `passes/pass-{{N}}.md` (replacing `{{N}}` with the actual number, e.g. `pass-1.md`) at the start of each pass. Stamp the metadata below, then delete this guidance blockquote and remove `{{...}}` placeholders. Update this file as work progresses; freeze it when the corresponding `pass-{{N}}` git tag is created.

**Started:** {{YYYY-MM-DD}}
**Mode:** greenfield | brownfield | mixed
**Baseline tag:** `{{previous-pass-tag}}` (e.g. `pass-0` for pass 1)
**`scope.md` commit at pass start:** `{{commit-sha}}`
**Target closure date:** {{date or "n/a — exploratory"}}

---

## Round 1 — Universe

- [ ] Entities catalog non-empty
- [ ] Verbs catalog non-empty
- [ ] Actors catalog non-empty
- [ ] All cross-references resolve (every verb subject/object, every actor's permitted_verbs)
- [ ] Glossary updated for any new canonical terms or banned synonyms
- [ ] `_note` + schema CI passes for round-1 files

PRs:
- _(append as opened: `#NN — entities · @reviewer · merged|open|needs-rework`)_

## Round 2 — State-event matrices

Aggregate counters:
- Total stateful entities (kind=stateful in entities.json): **___**
- State-machine.json files created: **___ / ___**
- Matrices with all cells filled (transition / noop / impossible): **___ / ___**

- [ ] `python spec/.ci/checks/check_round2_completeness.py` exits 0
- [ ] Every "impossible" cell has a real `justification_ref` resolving to an invariant or other artifact

PRs:
- _(append per matrix or per cell-batch as merged)_

## Round 3 — Input partitioning

Aggregate counters:
- Total input dimensions identified (verb params + entity attributes): **___**
- Partition files created: **___ / ___**

- [ ] Every boundary value explicitly assigned to a class in `boundary_assigned_here`
- [ ] Every class has min / typical / max representatives

PRs:
- _(append)_

## Round 4 — Cross-product interactions

Aggregate counters:
- Entity pairs identified: **___**
- Pairs analyzed (specified interaction OR pruned `family: independent` with rationale): **___ / ___**

PRs:
- _(append)_

## Round 5 — Formal invariants

Aggregate counters:
- Invariants in `invariants.qnt`: **___**
- Each has matching rationale entry in `invariant-rationale.json`: [ ]
- Open counterexample traces in `round-5/traces/`: **___**

- [ ] `quint typecheck spec/round-5/invariants.qnt` passes
- [ ] `quint verify --invariant=allInvariants spec/round-5/invariants.qnt` produces no counterexamples within bounded scope

PRs:
- _(append)_

## Round 6 — Quality attributes

Coverage of standard quality dimensions (each must have entries with target/criterion/method, OR `applicable: false` + `rationale_not_applicable`):

- [ ] security
- [ ] performance
- [ ] scalability
- [ ] availability
- [ ] observability
- [ ] recoverability
- [ ] compliance
- [ ] cost
- [ ] maintainability
- [ ] deprecation
- [ ] accessibility
- [ ] internationalization

PRs:
- _(append)_

## Round 7 — Adversarial scenarios

Coverage of STRIDE categories (each must have at least one scenario with mitigation_requirement, or accepted_risk + signoff):

- [ ] spoofing
- [ ] tampering
- [ ] repudiation
- [ ] information_disclosure
- [ ] denial_of_service
- [ ] elevation_of_privilege

Termination metric:
- Consecutive generation attempts producing no new mitigations (default N=20): **___ / N**

PRs:
- _(append)_

## Round 8 — Assumptions

Coverage of standard categories:

- [ ] environmental
- [ ] data
- [ ] human
- [ ] organizational
- [ ] technological

Termination metric:
- Consecutive storming rounds producing no new assumptions (target: 3): **___ / 3**

- [ ] All assumptions have non-empty `referenced_by` (each assumption is load-bearing for at least one other artifact)

PRs:
- _(append)_

## Round 9 — Cross-pass / cross-round gap discovery

Mode: `pass_1_full_audit` | `pass_n_delta`  *(see [`agents/round-9-cross-pass-delta.md`](../agents/round-9-cross-pass-delta.md))*

- [ ] Round 9 procedure executed
- [ ] Gaps reported (count this run: **___**)
- [ ] All gaps resolved (each → follow-up task → merged)
- [ ] **Final** Round 9 run produces zero new gaps

Gap-resolution PRs:
- _(append)_

## Contracts assembly

Aggregate counters:
- Total verbs in `verbs.json`: **___**
- Contracts drafted at `spec/contracts/<verb-id>.json`: **___ / ___**

- [ ] All `requires` / `ensures` / `preserves` clauses have non-empty `traces_to`
- [ ] Referential integrity check passes against contracts

PRs:
- _(append)_

## Tests derivation

Aggregate counters:
- Total spec artifacts (entities + verbs + cells + classes + interactions + invariants + qualities + scenarios + assumptions): **___**
- Spec artifacts with at least one derived test: **___ / ___**
- Test files with no spec reference (orphans): **___**  *(must be 0 at closure)*

PRs:
- _(append)_

## Closure conditions (Global Termination Check)

All eleven must hold to declare pass {{N}} converged. From [`docs/its-elementary.md` § Global termination check](../../docs/its-elementary.md):

- [ ] 1. Round 1 catalogs stable across three prompting rounds
- [ ] 2. Every cell in every Round 2 state-event matrix is filled
- [ ] 3. Every input dimension in Round 3 has complete partition coverage
- [ ] 4. Every meaningful entity pair in Round 4 has specified interaction
- [ ] 5. Round 5 model checker produces no counterexamples within declared bounds
- [ ] 6. Every Round 6 quality sub-attribute has acceptance criteria or explicit non-applicability
- [ ] 7. Round 7 adversarial generation produces no new mitigations for N consecutive attempts (default N=20)
- [ ] 8. Round 8 assumption-storming produces no new assumptions for three consecutive rounds
- [ ] 9. Round 9 cross-pass produces zero additions across all rounds
- [ ] 10. Every operation has a consolidated Hoare contract
- [ ] 11. Every specification artifact has derived tests; every test traces to an artifact

## Tag

- [ ] LLM driver reported convergence to human and listed evidence per closure condition
- [ ] Human approved
- [ ] `bash spec/.ci/checks/run_all.sh` passes on HEAD
- [ ] `git tag pass-{{N}}` executed
- [ ] `git push origin pass-{{N}}` executed
- [ ] `passes/pass-{{N+1}}.md` created from template (if iteration continues — i.e., if scope revision or new feature is queued)

## Blockers

Things waiting on a human decision that the LLM cannot proceed past on its own:

- _(append: "blocked: <description> · waiting on @stakeholder · since YYYY-MM-DD")_

## Session notes

Free-form observations across sessions — surprises, judgment calls worth flagging at pass review, things to revisit:

- _(append timestamped notes)_

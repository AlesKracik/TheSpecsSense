# Specs Sense — project template

Copy this folder into the root of a new (or existing) project and start running the algorithm with an LLM as your collaborator. This template is the physical realization of [the algorithm](../docs/its-elementary.md), driven interactively by an LLM under live human direction. Stakeholder review still happens via PRs.

The whole template lives under a single `spec/` subtree, so it drops into any repo (spec-only or mixed with code) without polluting the project root.

## Install

```bash
cp -r path/to/this/repo/spec ./spec       # one subtree, everything self-contained
bash spec/scripts/init-spec.sh             # layout check, deps, pre-commit hook, pass-0 tag, pass-1.md
```

Then open the repo in your LLM driver (Claude Code, Cursor, Codex, Aider, or any LLM you can point at a file) and tell it: *"Read `spec/AGENTS.md` and start Round 1 against `spec/scope.md`."*

> **Note on auto-loading.** `AGENTS.md` lives at `spec/AGENTS.md`, not at repo root, so tools that auto-load `AGENTS.md` only at root won't pick it up automatically. If you want auto-load on a spec-only repo, drop a 3-line stub `AGENTS.md` at repo root that says "this is a Specs Sense repo; read `spec/AGENTS.md` for driving instructions." For mixed repos, this is a feature — your code's `AGENTS.md` (if any) and the Specs Sense one don't collide.

## How this template runs

This template **is not a turnkey program.** It's a structured spec store + a set of prompt templates + a `spec/AGENTS.md` that tells an LLM how to drive the algorithm interactively.

```
   Human ◄─── live conversation ───► LLM driver (Claude Code / Cursor / Codex / Aider / etc.)
                                        │
                                        │ reads
                                        ▼
                                    spec/AGENTS.md       ◄─── start here
                                    spec/scope.md
                                    spec/agents/round-*.md
                                        │
                                        │ calls
                                        ▼
                                    Deterministic primitives:
                                    bash spec/.ci/checks/run_all.sh
                                    git / gh CLI
                                    Edit / Read / Write / Grep
                                        │
                                        │ proposes change → human approves → commits
                                        ▼
                                    PR opened, labelled, reviewer requested
                                        │
                                        ▼
                                    Stakeholder review (async, in GitHub UI)
                                    → merge → next round / next pass
```

The general loop is: LLM detects open work → proposes one change → human approves → CI validates → PR opened → stakeholder reviews → merge → next task. See [`AGENTS.md`](AGENTS.md) for the full driving instructions.

## How to use this template

Three scenarios. Pick the one that matches where you are; the substrate is identical across all three (`spec/` subtree). What changes is the `Mode` field in `spec/scope.md` and which input section of each agent prompt the LLM uses.

### 1. Greenfield mode — cold start from informal requirements

You have a sentence or paragraph describing what you want to build. No code yet.

1. **Write `spec/scope.md`.** This is the single most important input. Set `Mode: greenfield`. Name what's in scope, what's out, the stakeholder panel, and bounded constants for the model checker. Leave the Evidence sources section blank or annotate "n/a — greenfield".
2. **Optionally seed `spec/glossary.md`** with terms you already know are canonical. Or leave it; the LLM will propose additions via PR as it works.
3. **Open the repo in your LLM driver** and tell it: *"Read `spec/AGENTS.md` and start Round 1 against `spec/scope.md`."*
4. **Iterate one task at a time.** The LLM proposes one entity / verb / actor at a time, you approve or correct each, the LLM validates and opens a PR. Move to Round 2 once Round 1 closes.
5. **Stakeholder PR review** happens out-of-band (GitHub UI, the assigned reviewer per [`spec/AGENTS.md § Reviewer routing`](AGENTS.md)).
6. **Tag passes when ready.** When the LLM reports a pass has converged (closure conditions met, Round 9 found no new IDs), it asks you whether to tag — you decide.
7. **Code generation comes later**, downstream of the spec, via the seven-layer conformance pipeline ([ghosts-in-the-code.md](../docs/ghosts-in-the-code.md)). The spec repo holds the truth; the implementation repo respects it.

### 2. Mixed mode — new feature on top of a stabilized spec

You shipped, code exists, the spec is at a fixed point. Now add a feature.

1. **Flip `spec/scope.md` Mode to `mixed`** (if not already) and fill in the Evidence sources section pointing at the existing codebase, dashboards, runbooks, etc. Freeform markdown — URLs, paths, query examples, one-line annotations.
2. **Decide: scope revision, or just add R₀?**
   - If the feature fits inside the existing scope, just add the new requirement text. No further `scope.md` edit.
   - If the feature changes scope (new actor type, new domain, new compliance regime), formally revise `scope.md` and log the revision in its table. This exits the main loop per "Scope revision as meta-loop"; you re-enter Round 1 with the revised scope.
3. **Tell the LLM** *"We're in mixed mode. The new feature is `<text>`. Existing relevant code lives at `<paths>`. Walk Round 1 — propose deltas only, don't disturb existing entries unless the feature requires it."* The LLM walks both the GREENFIELD INPUT (your text) and BROWNFIELD INPUT (existing artifacts + code) sections of the agent prompt and reconciles in conversation.
4. **Run rounds 2-8 only on the delta.** New stateful entities get fresh matrices; existing entities get new event columns where the feature introduces new triggers. Skip rounds the feature does not touch.
5. **Round 9 does the heavy lifting.** New material almost always exposes gaps in old rounds. Tell the LLM *"Run cross-pass between `pass-N` and HEAD; report what new IDs need to land in earlier rounds."* It walks the procedure in `spec/agents/round-9-cross-pass-delta.md` and reports gaps for follow-up.
6. **Conformance pipeline drift gate** still applies — see [ghosts-in-the-code.md](../docs/ghosts-in-the-code.md) for how downstream code re-review gets triggered when spec clauses change.

### 3. Brownfield mode — extract a spec from an existing codebase

You have a codebase, possibly years old, with no formal spec. Postmortems, runbooks, ADRs, and tribal knowledge are your secondary inputs.

1. **Write `spec/scope.md`** anyway. Brownfield doesn't skip scope declaration — scope is "the part of this existing codebase we are choosing to specify now." Most retrofits start with one bounded subsystem.
2. **Set `Mode: brownfield` and fill `Evidence sources`** — codebase paths, dashboards, alert configs, postmortems, runbooks, ADRs, prior security audits, compliance checklists. If a section is genuinely unavailable, write "n/a" with a one-line reason rather than leaving TODO. For sources behind walls (closed-SaaS dashboards, air-gapped wikis), drop a manual snapshot under `spec/.snapshots/<source-id>/`.
3. **Tell the LLM** *"We're in brownfield mode. Walk Round 1 by reading the code structures (types, classes, modules, DB schemas, API surfaces, route handlers) and propose catalog entries. Each must include `source_evidence` citing file:line."* The LLM uses Read/Grep on the codebase (or invokes the [`fetch-evidence`](skills/fetch-evidence.md) skill if registered).
4. **Stakeholder triage is the work.** Each extracted entry gets one of four labels via PR review:
   - **intentional** → confirmed spec clause (normal merge).
   - **accidental-acceptable** → file as a Round 8 assumption with severity LOW and mitigation `accept`.
   - **accidental-wrong** → file as a Round 5 counterexample; spec captures correct behavior, code goes on the remediation queue.
   - **disputed** → normal stakeholder disagreement; surface through PR discussion.
5. **Rounds 1, 2, 5, 8 are strong** in brownfield because code, runbooks, postmortems, and dynamic invariant traces are rich sources. **Rounds 3, 4, 6, 7 still need fresh stakeholder thinking** — code branches don't reliably correspond to intended equivalence classes; threat models almost never live in code. The LLM should explicitly switch back to stakeholder elicitation for those.
6. **Conformance layers come online incrementally** — the **ratchet, not rewrite** pattern. Layer 5 (traceability) starts enforcing on every change from the moment the first spec clauses are confirmed; legacy code is grandfathered until modified.
7. **Three signals say "don't retrofit"**: 80%+ of extracted candidates label as accidental-wrong (rewrite, don't spec); original intent is genuinely lost (document the contract surface only); cost exceeds benefit window (system slated for replacement). See [ghosts-in-the-code.md § When brownfield is the wrong answer](../docs/ghosts-in-the-code.md).

### The three modes summarized

| Mode | When to use | What the LLM does |
|---|---|---|
| `greenfield` | No code yet; spec drives implementation | Reads scope.md and conversation only. Doesn't touch source files (there are none). |
| `mixed` | Stabilized spec + code, adding a feature or revising | Reconciles new intent against existing artifacts + code. Both GREENFIELD and BROWNFIELD INPUT sections of each agent prompt apply. |
| `brownfield` | Existing code, no spec; extracting one | Reads code structures + runbooks + ADRs as primary input; cites `source_evidence` on every record. |

From the second commit of any project onward, the realistic mode is `mixed`. Pure `greenfield` is a one-shot at project birth; pure `brownfield` is a one-shot at retrofit start. Most ongoing work happens in `mixed`.

## What's in here

All paths are project-root-relative — i.e., what you'd type from your project's top-level directory after `cp -r .../spec ./spec`.

| Path | Purpose |
|---|---|
| `spec/AGENTS.md` | **The driving instructions for the LLM.** Defines the role, layout, primitives, per-round procedure, commit/PR conventions, reviewer routing, mode awareness, and what NOT to do. **Read this first.** |
| `spec/README.md` | This file. |
| `spec/scope.md` | Prose declaration of Mode + what is in / out of scope + stakeholder panel + bounded constants + Evidence sources. Human-authored. The single most important input. |
| `spec/glossary.md` | Shared vocabulary. Human-curated, but the LLM proposes additions via PR. |
| `spec/round-1/` | Entities, verbs, actors. JSON. |
| `spec/round-2/` | One state-event matrix file per stateful entity. JSON. |
| `spec/round-3/` | One partition file per input dimension. JSON. |
| `spec/round-4/` | Cross-product interaction table. JSON. |
| `spec/round-5/` | Quint formal invariants + rationale + counterexample traces. |
| `spec/round-6/` | Quality-attribute matrix. JSON. |
| `spec/round-7/` | Adversarial scenario catalog (STRIDE). JSON. |
| `spec/round-8/` | Assumption registry. JSON. |
| `spec/contracts/` | One Hoare contract file per operation. JSON. Derived from rounds 1-8. |
| `spec/tests/` | Test metadata and source. Each test references the spec ID it derives from. |
| `spec/agents/` | Per-round procedure documentation. The LLM reads these as reference when starting a round. |
| `spec/skills/` | Reusable capabilities the LLM invokes during reasoning (e.g. `fetch-evidence` for brownfield/mixed source resolution). |
| `spec/passes/` | Per-pass progress checklists — the running mental model of where the spec stands procedurally. `pass-template.md` is frozen; `pass-1.md` (created by `init-spec.sh`) and subsequent `pass-N.md` files track round-by-round progress, PR links, blockers, and session notes. **Aide-memoire only — not authoritative.** See [`passes/_README.md`](passes/_README.md). |
| `spec/scripts/` | `init-spec.sh` (one-time setup), `render-views.py` (regenerate views), `new-entity.sh` (scaffold round-1 + round-2 stubs for a new stateful entity). |
| `spec/.diff-context/` | Tier-3 PR annotations. Auto-generated by pre-commit hook. |
| `spec/.snapshots/` | Manual evidence snapshots for sources the `fetch-evidence` skill cannot reach (closed-SaaS dashboards, air-gapped wikis). Gitignored by default. |
| `spec/.ci/schemas/` | JSON Schema files for every artifact type. |
| `spec/.ci/checks/` | CI scripts: schema validation, referential integrity, `_note` consistency, Round-2 completeness. **Run before every commit.** |
| `spec/.views/rendered/` | Auto-generated markdown views for human reading. Never edit by hand; regenerate via `spec/scripts/render-views.py`. |

## The two non-negotiables

1. **`_note` on every record.** Every meaningful record carries a 40-300 character human-language rendering of its content. CI rejects records without it. See [`spec/.ci/_NOTE_CONVENTION.md`](.ci/_NOTE_CONVENTION.md).
2. **Stable IDs everywhere.** Every entity, cell, partition, invariant, scenario, assumption, contract, test, and diff-context entry has an ID. The referential-integrity checker (`spec/.ci/checks/check_referential_integrity.py`) fails CI when an ID is referenced but not defined.

## Running CI locally

```bash
bash spec/.ci/checks/run_all.sh
```

This runs:
- Schema validation against every JSON file
- Referential-integrity check across all rounds
- `_note` presence and length check
- Round-2 completeness check (no empty cells)
- Quint model checker on `round-5/invariants.qnt` (if `quint` is installed)

Wire it into your CI provider as a single step. PRs that fail any check are blocked from merge. The LLM (per `spec/AGENTS.md`) runs this locally before every commit it proposes.

## What this template does NOT include

- **An automated orchestrator.** The previous version of this template included one; it's been replaced with the LLM-driven flow described in `spec/AGENTS.md`. If you want unattended dispatch (cron-driven, multi-task fan-out, PR-event-driven re-dispatch), you'll need to write your own orchestrator — the spec layout, agent prompts, skills, and CI checks are designed to be reusable across drivers.
- **Conformance pipeline.** The seven-layer downstream pipeline ([ghosts-in-the-code.md](../docs/ghosts-in-the-code.md)) lives in your implementation repo, not the spec repo. Hooks for traceability metadata are stubbed in `spec/tests/` but the runtime/type/property-test layers are language-specific.
- **Reviewer assignment automation.** Use a `.github/CODEOWNERS` file mapping `spec/round-1/*` etc. to your stakeholder GitHub handles — that's what gets reviewers auto-requested on PRs. The `spec/AGENTS.md` reviewer-routing table tells the LLM which stakeholder to mention in PR bodies; CODEOWNERS makes the actual review-request happen.

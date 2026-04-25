# Specs Sense — project template

Copy this folder into the root of a new (or existing) project, rename it to `spec/` (or keep `template/` and split out as you prefer), and start running the algorithm. This template is the physical realization of [the algorithm](../docs/its-elementary.md) described in the Specs Sense methodology, using the architecture from [behind-the-curtain.md](../docs/behind-the-curtain.md).

## Install

```bash
cp -r path/to/this/template/spec .
cp -r path/to/this/template/agents .
cp -r path/to/this/template/skills .          # portable skill specs — runtime location varies
cp -r path/to/this/template/scripts .
cp -r path/to/this/template/orchestrator .    # reference Python orchestrator
bash scripts/init-spec.sh                     # layout check, deps, pre-commit hook, pass-0 tag
```

The `skills/` directory holds **portable spec definitions**, not runtime-loaded files. Where each skill needs to physically live so your LLM runtime can find it depends on the runtime — see [`skills/_README.md § Where skills live at runtime`](skills/_README.md) for the per-runtime mapping. For Claude Code, symlink each spec into `.claude/skills/`; for the Anthropic SDK or OpenAI, the orchestrator reads `skills/*.md` and registers them programmatically.

The general loop, regardless of scenario, is: agent proposes → CI validates → PR opened → stakeholder reviews → merge → next round (or next pass). See [docs/its-elementary.md](../docs/its-elementary.md) for what each round does and when it closes.

## How to use this template

Three scenarios. Pick the one that matches where you are; the substrate (spec/, agents/, CI) is identical across all three.

### 1. Greenfield mode — cold start from informal requirements

You have a sentence or paragraph describing what you want to build. No code yet.

1. **Write `spec/scope.md`.** This is the single most important input. Set `Mode: greenfield`. Name what's in scope, what's out, the stakeholder panel, and bounded constants for the model checker. Leave the Evidence sources section blank or annotate "n/a — greenfield". The algorithm cannot derive scope; it can only iterate inside it.
2. **Optionally seed `spec/glossary.md`** with terms you already know are canonical. Or leave it; agents propose additions via PR.
3. **Dispatch Round 1** with the informal requirement text and `scope.md` as input. Use the GREENFIELD INPUT section of [`agents/round-1-universe.md`](agents/round-1-universe.md). One invocation per catalog kind (entities, then verbs, then actors).
4. **Iterate rounds 2-8** as Round 1 stabilizes. Round 2 fills state machines, Round 3 partitions inputs, Round 5 adds Quint invariants, etc. Each round's agent prompt is in `agents/`.
5. **Round 9 cross-pass** finds gaps that later rounds expose in earlier ones. Loop until a full cross-pass produces zero new entries (typically 3-6 passes for moderate systems).
6. **Tag each iteration**: `git tag pass-1`, `pass-2`, ... — Round 9 uses tag boundaries to compute deltas.
7. **Code generation comes later**, downstream of the spec, via the seven-layer conformance pipeline ([ghosts-in-the-code.md](../docs/ghosts-in-the-code.md)). The spec repo holds the truth; the implementation repo respects it.

### 2. Mixed mode - New feature on top of a stabilized spec

You shipped, code exists, the spec is at a fixed point. Now add a feature. This is what `Mode: mixed` is for. The orchestrator dispatches **both** agent variants in parallel: greenfield against the new feature's informal text, brownfield against the existing spec catalogs and the code that already realizes them. R₀ for this iteration is the union of new feature text + existing spec + existing code; the proposals merge through standard PR review.

Mixed mode is structurally distinct from cold brownfield (scenario 3). Cold brownfield extracts an entire spec from code; mixed extends a stabilized spec by reconciling new intent against existing reality.

1. **Flip `scope.md` Mode to `mixed`** (if not already) and fill in the Evidence sources section pointing at the existing codebase, dashboards, runbooks, etc. The format is freeform markdown — URLs, paths, query examples, one-line annotations. The orchestrator does not parse this directly; it loads the [`fetch-evidence`](skills/fetch-evidence.md) skill on the round-N agent, which resolves each source via tool / skill APIs (web_fetch, file_read, MCP servers) when the agent invokes it during reasoning.
2. **Decide: scope revision, or just add R₀?**
   - If the feature fits inside the existing scope, just add the new requirement text. No further `scope.md` edit.
   - If the feature changes scope (new actor type, new domain, new compliance regime), formally revise `scope.md` and log the revision in its table. This exits the main loop per "Scope revision as meta-loop"; you re-enter Round 1 with the revised scope.
3. **Dispatch Round 1 with both inputs**: the new feature's GREENFIELD INPUT (its informal text) **and** the BROWNFIELD INPUT (existing entities/verbs/actors as committed catalog files; existing code that the feature touches). The agent's job is to propose only deltas — existing entries stay frozen unless the feature changes them.
4. **Run rounds 2-8 only on the delta.** New stateful entities get fresh matrices; existing entities get new event columns where the feature introduces new triggers; new verbs get partitions; new operations get new invariants and quality targets. Skip rounds the feature does not touch.
5. **Round 9 does the heavy lifting.** New material almost always exposes gaps in old rounds — a new entity that needs to appear in existing cross-product interactions, a new actor that calls existing verbs, a new assumption old invariants depend on. Run [`agents/round-9-cross-pass-delta.md`](agents/round-9-cross-pass-delta.md) with your most recent `pass-N` tag as the previous-iteration boundary; tag the result `pass-N+1` once it converges.
6. **Conformance pipeline drift gate is critical.** When the new feature changes existing spec clauses, Layer 5 (drift gate) auto-creates issues or draft PRs against every implementation file referencing those clauses. Without it, the new feature lands cleanly but you silently break old code that quietly relied on the unchanged version.

### 3. Brownfield mode — extract a spec from an existing codebase

You have a codebase, possibly years old, with no formal spec. Postmortems, runbooks, ADRs, and tribal knowledge are your secondary inputs.

1. **Write `spec/scope.md`** anyway. Brownfield does not skip scope declaration — it just means scope is "the part of this existing codebase we are choosing to specify now." Most retrofits start with one bounded subsystem, not the whole repo.
2. **Set `Mode: brownfield` and fill `Evidence sources`** — codebase paths, dashboards, alert configs, postmortems, runbooks, ADRs, prior security audits, compliance checklists. Freeform markdown; URLs, paths, query examples, annotations. Round-N agents (with the [`fetch-evidence`](skills/fetch-evidence.md) skill loaded) read this as the source map and resolve entries via tool / skill APIs. If a section is genuinely unavailable, write "n/a" with a one-line reason rather than leaving TODO. For sources behind walls the skill cannot reach (closed-SaaS dashboards, air-gapped wikis), drop a manual snapshot under `spec/.snapshots/<source-id>/` and the skill will treat it as canonical.
3. **Dispatch Round 1 in BROWNFIELD INPUT mode**. The agent reads code structures (types, classes, modules, DB schemas, API surfaces, route handlers, IAM principals) and proposes catalog entries. Each proposal carries a `source_evidence` field citing the file:line that motivated it.
4. **Stakeholder triage is the work**. Each extracted entry gets one of four labels via the standard PR review:
   - **intentional** → confirmed spec clause (normal merge).
   - **accidental-acceptable** → file as a Round 8 assumption with severity LOW and mitigation `accept`.
   - **accidental-wrong** → file as a Round 5 counterexample; spec captures correct behavior, code goes on the remediation queue.
   - **disputed** → normal stakeholder disagreement; surface through readback.
5. **Rounds 1, 2, 5, 8 are strong** in brownfield because code, runbooks, postmortems, and dynamic invariant traces are rich sources. **Rounds 3, 4, 6, 7 still need fresh stakeholder thinking** — code branches do not reliably correspond to intended equivalence classes; threat models almost never live in code. Run those rounds against stakeholders the same way as greenfield.
6. **Conformance layers come online incrementally**. Layer 5 (traceability) starts enforcing on every change from the moment the first spec clauses are confirmed. Legacy code is grandfathered until modified. The pattern is **ratchet, not rewrite** — every change to legacy code is held to the new standard; existing code is grandfathered until touched.
7. **Three signals say "don't retrofit"**: 80%+ of extracted candidates label as accidental-wrong (rewrite, don't spec); original intent is genuinely lost (document the contract surface only); cost exceeds benefit window (system slated for replacement). See [ghosts-in-the-code.md § When brownfield is the wrong answer](../docs/ghosts-in-the-code.md).

### The three modes summarized

| Mode | When to use | Agent dispatch |
|---|---|---|
| `greenfield` | No code yet; spec drives implementation | Greenfield-variant agents only |
| `mixed` | Stabilized spec + code, adding a feature or revising | Both variants in parallel: greenfield over new intent, brownfield over existing artifacts/code |
| `brownfield` | Existing code, no spec; extracting one | Brownfield-variant agents only |

From the second commit of any project onward, the realistic mode is `mixed`. Pure `greenfield` is a one-shot at project birth; pure `brownfield` is a one-shot at retrofit start. Most ongoing work happens in `mixed`.

## What's in here

| Path | Purpose |
|---|---|
| `spec/scope.md` | Prose declaration of what is in / out of scope. Human-authored. The single most important input. |
| `spec/glossary.md` | Shared vocabulary. Human-curated, but agents may propose additions via PR. |
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
| `spec/.diff-context/` | Tier-3 PR annotations. Auto-generated by pre-commit hook. |
| `spec/.ci/schemas/` | JSON Schema files. Used by structured-output APIs and CI validation. |
| `spec/.ci/checks/` | CI scripts: schema validation, referential integrity, `_note` consistency, completeness. |
| `spec/.views/rendered/` | Auto-generated markdown views for human reading. Never edit by hand. |
| `agents/` | Per-round agent prompt templates. Plug into your agent runner. |
| `skills/` | Reusable capabilities agents invoke during reasoning (e.g. `fetch-evidence` for brownfield/mixed source resolution). |
| `scripts/` | Initialization, view rendering, helpers. |
| `orchestrator/` | Reference Python orchestrator (Anthropic SDK + `gh` CLI). Round 1 wired end-to-end; rounds 2-9 stubbed. See [orchestrator/README.md](orchestrator/README.md). |

## The two non-negotiables

1. **`_note` on every record.** Every meaningful record carries a 40-300 character human-language rendering of its content. CI rejects records without it. See `_NOTE_CONVENTION.md` in `spec/.ci/`.
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

Wire it into your CI provider as a single step. PRs that fail any check are blocked from merge.

## What this template does NOT include

- **A production orchestrator.** The reference implementation under `orchestrator/` wires Round 1 end-to-end and is enough to dispatch agents against a real `scope.md` on a real repo, but rounds 2-9 + contracts are detector stubs. Adding the next round is ~30 lines (one detector function + one `ROUND_CONFIGS` entry) — see [orchestrator/README.md](orchestrator/README.md) and [orchestrator/state-machine.md](orchestrator/state-machine.md). Replace with your own orchestrator (any language, any deployment model) and the spec/agents/skills layout is unchanged.
- **Conformance pipeline.** The seven-layer downstream pipeline ([ghosts-in-the-code.md](../docs/ghosts-in-the-code.md)) lives in your implementation repo, not the spec repo. Hooks for traceability metadata are stubbed in `spec/tests/` but the runtime/type/property-test layers are language-specific.

# Agent prompt templates

Each file is a self-contained prompt template describing one round's procedure: scope, inputs, schema, hard rules, and (where applicable) tool requirements.

> **Note on terminology.** These prompts were written for an orchestrator-dispatched flow and use "orchestrator" / "agent invocation" throughout. **In this template's current default flow, there is no orchestrator process** — an LLM driven by [`../AGENTS.md`](../AGENTS.md) executes the procedures interactively under live human direction. When you read "the orchestrator dispatches X" or "the agent invocation," substitute "the LLM driver picks the next task and applies this procedure inline." When you read "Output format: a JSON object with `{uncertainty, patch, rationale_for_pr_body}`," that's the orchestrator-mode artifact — in interactive mode, the LLM `Edit`s the target file directly and writes the rationale into the PR body. The **schema, hard rules, and `_note` conventions still apply** regardless of driver.

Each prompt template — and each invocation, when an orchestrator dispatches one — substitutes `{{...}}` placeholders with concrete values before use.

Every agent must obey the **agent contract** from [behind-the-curtain.md § Agent contract](../../docs/behind-the-curtain.md):

1. **Narrow scope.** Do exactly the task asked. Do not range further.
2. **Bounded context.** Only the slice provided. Do not request more files.
3. **Structured output.** JSON conforming to the schema(s) named in the prompt. Use the LLM provider's structured-output / JSON-mode API where available.
4. **Faithful `_note`.** Every record includes a 40-300 char `_note` matching the data. See [_NOTE_CONVENTION.md](../spec/.ci/_NOTE_CONVENTION.md).
5. **Uncertainty flag.** Each PR carries `uncertainty: low | medium | high` so the orchestrator can route high-uncertainty work to a human reviewer first.
6. **No hidden state.** Everything you need is in the prompt; everything you produce goes to a PR.

## Project mode vs agent variant

`spec/scope.md` declares one of three project-level modes: `greenfield`, `brownfield`, or `mixed`. Each agent prompt below has only **two** input variants — GREENFIELD INPUT and BROWNFIELD INPUT — because per-invocation an agent always operates against exactly one source. The asymmetry is intentional.

The orchestrator translates project mode into per-invocation dispatch:

| `scope.md` Mode | Per task, the orchestrator invokes... |
|---|---|
| `greenfield` | One agent invocation with **GREENFIELD INPUT** |
| `brownfield` | One agent invocation with **BROWNFIELD INPUT** |
| `mixed` | **Two parallel invocations** — one GREENFIELD (over the new intent text) and one BROWNFIELD (over existing artifacts and code). Their proposals reconcile at PR review (or via a dedicated reconciler agent if both touch the same record). |

So `mixed` is not a third variant — it is an orchestration pattern that runs the same agent prompt twice and merges results. **Do not add MIXED INPUT sections to the prompts**; the duality at the prompt level is intentional and keeps each invocation's task narrow.

The four mode-agnostic agents — `round-9-cross-pass-delta.md`, `round-5-counterexample-interpreter.md`, `contract-assembly.md`, `note-vs-data.md` — have no input-variant sections because their work (delta computation, trace analysis, consolidation, semantic check) is independent of input source.

## Source resolution — the fetch-evidence skill

For brownfield and mixed modes, evidence lives in many places and many formats: code in a Git repo, dashboards behind SSO, postmortems in a wiki, ADRs in a docs folder, audit reports as PDFs, log archives in cloud storage. Rather than make the orchestrator deterministically parse each kind, source resolution is delegated to a **skill** — [`fetch-evidence`](../skills/fetch-evidence.md) — that the round-N agent invokes during its own reasoning. The skill uses tool / skill APIs (web_fetch, file_read, grep, MCP servers) to fetch from each source kind and returns excerpts with citations directly into the agent's context.

Dispatch flow per round-N task:

```
detect work        →  round-N agent (with fetch-evidence skill loaded)   →  PR
(orchestrator,        ├─ reasons about the task
 deterministic)       ├─ invokes fetch-evidence skill as needed (mid-task)
                      ├─ refines slice request based on what it gets back
                      └─ emits structured JSON proposal
                                                                            (Git)
```

Why a skill, not an agent: the round-N agent decides when to fetch, how to refine slices, and when it has enough evidence — refining mid-task is natural inside one LLM invocation, awkward across two. Skills compose; rigid two-call dispatch loses that.

Greenfield projects do not load the skill — there is nothing to fetch beyond the prose already in `spec/`.

The skill's contract — input shape, output shape, tool requirements, citation rules, snapshot fallback for unreachable sources — is in [`../skills/fetch-evidence.md`](../skills/fetch-evidence.md).

Why this beats deterministic source adapters: scope.md stays freeform markdown (humans like it that way); orchestrator stays deterministic in the bits that matter (work detection, dispatch, PR routing); new evidence kinds become "install the relevant MCP server and document it in scope.md," not "ship a new orchestrator release with a custom adapter." The cost is that the skill makes LLM-mediated tool calls — but those replace what would otherwise be brittle per-source parser code and are auditable through the agent's tool-call transcript.

## Files

| File | Round |
|---|---|
| `round-1-universe.md` | 1 — entities, verbs, actors |
| `round-2-state-event.md` | 2 — state-event matrix cells |
| `round-3-partition.md` | 3 — input partitioning |
| `round-4-interaction.md` | 4 — cross-product |
| `round-5-invariant.md` | 5 — formal invariants in Quint |
| `round-5-counterexample-interpreter.md` | 5 — turn Quint counterexamples into PRs |
| `round-6-quality.md` | 6 — quality attributes |
| `round-7-adversarial.md` | 7 — STRIDE scenarios |
| `round-8-assumption.md` | 8 — assumption excavation |
| `round-9-cross-pass-delta.md` | 9 — find new gaps in re-runs |
| `contract-assembly.md` | Consolidation — Hoare contracts |
| `note-vs-data.md` | CI semantic check — does the `_note` match the data? |

Source resolution for brownfield / mixed mode is provided by a **skill**, not an agent — see [`../skills/fetch-evidence.md`](../skills/fetch-evidence.md) and [`../skills/_README.md`](../skills/_README.md) for the contract and rationale.

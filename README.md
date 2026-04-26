# Specs Sense

A methodology for converting informal requirements into behaviorally complete specifications, designed to run on top of Git with AI agents handling the mechanical work and humans handling judgment.


## The four files

This documentation is split into four files. Each is sized to a single sitting and stands on its own; together they form a sequence.

| # | File | What it covers |
|---|---|---|
| 1 | [docs/i-see-dead-specs.md](docs/i-see-dead-specs.md) | Overview: what Specs Sense is, why it exists, the irreducible role of human judgment |
| 2 | [docs/its-elementary.md](docs/its-elementary.md) | The algorithm: nine rounds of mechanical gap-discovery, iterated to a fixed point |
| 3 | [docs/behind-the-curtain.md](docs/behind-the-curtain.md) | Physical implementation: Git, JSON, agents, orchestrator, readback, diffs |
| 4 | [docs/ghosts-in-the-code.md](docs/ghosts-in-the-code.md) | Connecting spec to code: conformance layers and brownfield retrofit |

## Where to start

| If you are... | Read first |
|---|---|
| Skeptical, want the pitch in fifteen minutes | `docs/i-see-dead-specs` |
| About to run the methodology on a real system | `docs/its-elementary` |
| Building the tooling and infrastructure | `docs/behind-the-curtain` |
| Retrofitting an existing codebase | `docs/ghosts-in-the-code` |
| Reading end-to-end | In order, 1 → 4 |

The files cross-reference each other where relevant. Concepts introduced in one file get a one-sentence recap when used in another, so any file can be read on its own without backtracking — but the full picture lives in the sequence.

## The template

[`spec/`](spec/) is a copyable template — a structured spec store + agent prompts + skills + per-pass progress checklists + an `AGENTS.md` driving file that tells an LLM how to run the algorithm interactively. Drop the entire `spec/` subtree into any project (spec-only or mixed with code) to get started. See [`spec/README.md`](spec/README.md) for usage.

## The honest pitch

Most informal requirements are radically incomplete. 

The mechanical part can be automated and run to a fixed point. What can't be automated is two things: declaring scope (deciding what's in and out) and recognizing intent (deciding whether a surfaced gap matches what stakeholders actually want). Specs Sense draws the line at exactly these two places: everything else is a mechanical loop, and these two are where humans live in the architecture.

The methodology is not a magic wand. It does not produce *correct* specifications; it produces *complete* ones. Correctness — goodness, fit-for-purpose — comes from the human review layer at every step. The architecture's job is to make that review tractable at scale, even when the spec runs to tens of thousands of words.

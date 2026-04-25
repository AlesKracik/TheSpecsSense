# I see dead specs

## Specs Sense / 1 — Overview ##

Where this fits: this file is the conceptual entry point. The algorithm itself is in [its-elementary](its-elementary.md). The physical implementation — Git, JSON, agents, orchestrator — is in [behind-the-curtain](behind-the-curtain.md). Connecting spec to code, including how to apply this to existing codebases, is in [ghosts-in-the-code](ghosts-in-the-code.md).

## What Specs Sense is

A methodology for converting an informal requirement — possibly as short as a single sentence — into a specification that is behaviorally complete over an explicitly bounded scope. *Behaviorally complete* means: for every input scenario within scope, the specification determines a unique permissible output or set of outputs.

The methodology runs nine rounds of mechanical gap-discovery, iterated to a fixed point where further iteration produces no new requirements. AI agents handle the mechanical work; human reviewers handle the judgment.

## Why this is hard, and why automation helps

The gap between initial single sentence requirement and a specification a competent team could implement without ambiguity is roughly a thousandfold expansion in word count. Almost all of that expansion is mechanical: enumerating entities, filling state-event matrices, partitioning input spaces, checking invariants, generating adversarial scenarios, surfacing assumptions. People give up on writing complete specs not because they can't, but because the labor is tedious and the value is back-loaded.

Automation changes the economics. Each individual mechanical task is small, well-defined, and well-suited to an LLM agent on a narrow context. Run thousands of these in parallel, with humans reviewing the outputs at a manageable rate, and behavioral completeness becomes affordable instead of aspirational. The architecture exists to make this exchange — affordable mechanical labor for unaffordable manual labor — actually work at scale.

## Completeness vs goodness

Completeness is not the same as goodness. A specification can be complete and still specify the wrong system: complete against a misunderstood scope, complete against misread stakeholder intent, complete against assumptions that turn out to be wrong. Specs Sense claims only to produce completeness; it does not claim to produce goodness.

This distinction shapes the entire architecture. The *mechanical loop* — entity enumeration, matrix filling, partition discovery, invariant checking, adversarial generation, assumption excavation — handles completeness. It has closure conditions, terminates at a fixed point, and can be parallelized across agents. The *readback and diff layers* handle goodness: they present each surfaced gap to the stakeholder best placed to judge whether the current draft matches what they actually want, and route their decisions back into the loop. The execution architecture exists to connect the two.

The methodology's value is that it surfaces every gap a specifier might otherwise miss — the missed state-event cell, the unconsidered input class, the unexamined interaction, the unstated assumption. Gap discovery is what mechanical thoroughness is genuinely good at and what humans are genuinely bad at. Goodness judgment is the opposite: the gap, once surfaced, is something only the human can evaluate. The architecture splits labor along this exact line.

## What the methodology does not do

It does not produce proofs of implementation correctness. The classical impossibility results (Rice's theorem, halting, Gödel) constrain *verification* of arbitrary programs against properties; they do not constrain *specification* writing, which is a finite act over finite structures. Specs Sense produces specifications; making code respect those specifications is a separate downstream pipeline covered in [ghosts-in-the-code](ghosts-in-the-code.md).

It does not eliminate human judgment. It draws the line at two places where human judgment is irreducible — see "The two irreducibles" below.

It does not require the specifier to know in advance what a complete specification looks like. The pipeline discovers the structure as it runs.

## Inputs

1. **Informal requirement R₀.** One or more sources of intent and observed behavior. Greenfield projects start from natural-language sentences. Brownfield projects use existing code, production telemetry, postmortems, runbooks, prior specifications, comments, and ADRs as additional sources. The pipeline extracts proposals from whatever sources are provided and runs them through the standard rounds. From the second commit of any project onward, every system is a mix of original intent and current implementation reality.

2. **Scope declaration S.** An explicit statement of what is in and out of scope. Scope itself is a requirement and may be revised as a meta-decision outside the main loop.

3. **Stakeholder panel P.** A set of humans with authority to answer questions about intent. Multiple roles recommended (domain expert, end user, security, operations, compliance).

4. **Agent fleet A.** A set of LLM-based agents capable of narrow, context-bounded specification tasks: entity proposal, transition drafting, partition analysis, invariant generation, counterexample interpretation, adversarial scenario generation, assumption excavation. Each agent satisfies a strict contract — narrow scope, bounded context, structured output, uncertainty flagging, no hidden state — defined in [behind-the-curtain](behind-the-curtain.md). The fleet generates candidate artifacts; the stakeholder panel evaluates them.

## Outputs

The methodology produces a versioned, queryable specification with the following artifact types:

- **Entity catalog** with attributes and value ranges
- **Verb catalog** with actors and side effects
- **Actor catalog** with permissions and concerns
- **State-event matrix** per primary entity, every cell filled
- **Input-partition tables** per input dimension
- **Cross-product interaction table** for entity pairs
- **Formal invariants** in a machine-checkable specification language
- **Quality-attribute matrix** with acceptance criteria
- **Adversarial scenario catalog** with mitigations
- **Assumption registry** with severity and mitigations
- **Per-operation Hoare contracts** derived from the above
- **Test case set** derived from each round
- **Per-round readback documents** structured for human review, gaps-first
- **Pass-over-pass diff entries** showing what changed, with spatial and dependency context
- **Master synthesis document** — one-page status across all rounds, per iteration
- **Per-stakeholder views** — filtered readbacks scoped to each reviewer's decisions

Storage formats and the directory layout for these artifacts are described in [behind-the-curtain](behind-the-curtain.md).

## The labor split, made concrete

| Activity | Who does it | Why |
|---|---|---|
| Propose entities, transitions, partitions, invariants | AI agent | Mechanical thoroughness, parallelizable |
| Run formal model checker on invariants | Non-AI tool (e.g., Quint) | Deterministic, reproducible |
| Generate adversarial scenarios | AI agent | Volume and breadth |
| Excavate assumptions | AI agent | Mining documents and code |
| Decide whether scope is right | Human | Domain authority |
| Decide whether a proposed entity reflects real intent | Human | Goodness judgment |
| Decide whether to accept a state-event cell as drafted | Human | Goodness judgment |
| Decide whether a counterexample is a real bug or a spec gap | Human | Domain context |
| Approve a change for merge | Human | Final authority |

Each row is a different kind of work. The architecture's job is to route each piece to the right doer at the right time without overwhelming anyone.

## The two irreducibles

Two places in the methodology require human judgment that cannot be factored out.

**Scope declaration.** What is in and what is out is a question of stakeholder authority, not algorithmic discovery. The pipeline can iterate scope as a meta-decision when it turns out to be wrong, but it cannot derive scope from anywhere. Scope is the input the algorithm takes; it cannot bootstrap its own purpose.

**Recognition of intent.** When the pipeline surfaces a gap and proposes a way to fill it, only a human stakeholder can say "yes, that matches what we want" or "no, here's what we actually want instead." The agent can guess; the model checker can verify mechanical properties; the human is the only authority on whether the spec captures the actual intent.

These are not weaknesses in the methodology. They are the methodology's I/O ports — the places where human authority enters the system. Everything else is mechanical and exhaustive.

## What's next

If you're skeptical and want to see the algorithm in detail: [its-elementary](its-elementary.md).

If you want to know how the algorithm actually runs as a system: [behind-the-curtain](behind-the-curtain.md).

If you want to apply this to an existing codebase: [ghosts-in-the-code](ghosts-in-the-code.md).

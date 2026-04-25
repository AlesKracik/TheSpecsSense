# ghosts-in-the-code

*Specs Sense / 4 — Connecting spec to code*

> Where this fits: this file describes how AI-generated code respects the specification, and how the methodology applies to existing codebases. The framing is in [i-see-dead-specs](i-see-dead-specs.md). The algorithm itself is in [its-elementary](its-elementary.md). The execution architecture — Git, JSON, agents, orchestrator — is in [behind-the-curtain](behind-the-curtain.md).

## The downstream problem

The specification describes what is true about the system. The code is one possible realization. Many implementations satisfy the spec; many more do not. AI-generated code is particularly prone to confidently-wrong output, because LLMs lack a stable mental model of the spec to check against.

Closing the gap between spec and implementation requires a layered set of mechanisms, each catching a different class of violation, each automated enough to run on every change. The hierarchy of confidence runs roughly: formal proof > exhaustive model checking > comprehensive property testing > example-based testing > runtime assertion > code review > "the LLM said it followed the spec." The strategy is to stack layers and accept that no single one is sufficient.

## Seven layers, ordered by confidence

### Layer 1: Constrain generation by giving the model the spec

The cheapest and most effective intervention: when an LLM writes code, its context includes the *relevant slices* of the spec, not just the task description.

- Hoare contracts for the operation being implemented.
- State-event matrix cells the code must implement.
- Invariants the code must preserve.
- Test cases derived from the spec for this operation.

Compliance becomes the prompt. The model still writes code, but it writes against constraints visible in its context. In the same call, the agent produces a structured per-clause justification — for each `requires`/`ensures` clause, name the line of code that establishes it. That justification is checkable in subsequent layers.

This is necessary but nowhere near sufficient. Models confidently produce code that "implements" a spec they misread. The next layers catch what this one misses.

### Layer 2: Type the contracts into the code

Modern type systems express significant chunks of the spec directly, where the compiler enforces them. The compiler is not an LLM; it does not hallucinate; it does not let through code that violates the types.

Concrete moves:

- **Sum types for states.** A spec state machine with twelve states becomes a sum type with twelve variants; the compiler enforces exhaustive matching. Code that forgets a state on a transition fails to compile.
- **Newtype wrappers for distinct value classes.** Round 3 partitions (Tiny / Small / Medium / Large / Huge) become distinct types, not raw integers. Functions operating on Huge VMs cannot be called with a Small VM by mistake.
- **Phantom types for invariants.** A `Snapshot<Pinned>` and `Snapshot<Unpinned>` are different types; functions requiring a pinned snapshot reject unpinned input at compile time.
- **Refinement types where available.** Liquid Haskell, F*, Idris, Dafny, and (with effort) Rust let "VM size in 1..10000 GB" be a compiler-checked type.

The Round 1 type catalog should map directly onto types in the implementation. This is the single highest-leverage move — every constraint expressed in types is one LLMs cannot violate without the compiler catching them.

### Layer 3: Property-based tests derived from the spec

For everything the type system cannot express, property-based tests are the next layer. These tests are derived *from the spec* by an agent (using the spec slice as input), not written from scratch.

- The Round 2 state-event matrix becomes a test that drives the system through random valid event sequences and asserts the next-state matches the matrix.
- The Round 5 invariants become properties asserted after every operation.
- The Round 3 partitions become generators producing test inputs covering every equivalence class.

Run with thousands of generated cases per property. Failures yield minimized counterexamples pointing at the exact violation. Tools include Hypothesis (Python), QuickCheck (Haskell), proptest (Rust), fast-check (TypeScript), jqwik (Java).

These tests run against every code change, not just spec changes. Because tests are derived from spec IDs, when a spec clause changes, the corresponding test is auto-flagged for regeneration. The traceability chain — spec ID → test ID → CI result — closes the loop.

### Layer 4: Runtime contract enforcement

For contracts the type system does not capture and property tests might miss, runtime assertions enforce them in production.

- Every Hoare-contract `requires` becomes an assertion at function entry.
- Every `ensures` becomes an assertion at function exit.
- Every invariant is checked at appropriate points.

Design-by-contract languages (Eiffel, Ada SPARK, Dafny) make this native. For others, libraries fill the gap: Bean Validation (Java), Pydantic (Python), Zod (TypeScript), or hand-written assertions. The key property: assertions are *generated from the same Hoare contracts that drove code generation*, so they cannot drift independently.

Failure modes: too slow (the production hit is real for high-frequency operations) and too loud (every failure becomes an incident). Mitigations: sampling, configurable enforcement levels per environment, and routing contract violations to a triage channel that classifies them as "find the bug" or "fix the contract."

### Layer 5: Bidirectional traceability with CI gates

Every commit to the implementation references the spec clauses it implements or modifies. Every spec clause references the implementation files realizing it. Captured in machine-readable traceability metadata — JSON files mapping `spec_id` to `[implementation_file:lineno, test_id, contract_id]` — checked into the repo and validated by CI.

Three CI gates close the loop:

1. **Coverage gate.** Every spec clause has at least one implementation reference. A clause without one is either out of scope (explicit annotation required) or a gap (PR fails CI).
2. **Bidirectional gate.** Every implementation file declares which spec clauses it implements. Code implementing no spec clause is either utility (annotated) or unanchored (PR fails CI).
3. **Drift gate.** When a spec clause changes, all implementation references are flagged for re-review. The PR that changes the spec auto-creates issues or draft PRs for every implementation reference, requiring explicit re-confirmation.

The drift gate catches the slow-rot failure mode where spec evolves and implementation lags. Without it, the spec becomes documentation of what the system *used* to be supposed to do.

### Layer 6: Formal verification, where cost is justified

For the highest-stakes invariants — security properties, safety properties, anything that cannot be wrong silently — go past tests into proof. The Quint specs from Round 5 already exist; for critical properties, write the implementation in a verified language (Dafny, F*, Lean, Coq, Rust with Verus) and prove the implementation refines the spec.

This is expensive. CompCert, seL4, and the Tezos Michelson interpreter took years per kloc. The discipline is to pick three to five most critical invariants, prove only those, and accept lower-confidence layers for everything else. "Critical" usually means invariants where silent violation produces data loss or security compromise — KMS-key-retention is a candidate; rendering details are not.

### Layer 7: AI review against the spec

Beyond mechanical layers, an LLM-based reviewer reads each PR with the relevant spec slice as context and answers structured questions:

- Which spec clauses does this PR claim to implement?
- For each clause, does the code actually establish what the contract requires?
- What spec clauses touch the same area but are not mentioned?
- What reasonable inputs are not handled?

This is not reliable enough to be a CI gate by itself, but it supplements human review well — especially for catching "the code looks fine but does not actually implement what was asked." Run as advisory; route output to PR comments; let humans accept or dismiss.

## The full pipeline

The mechanisms compose into a code-quality pipeline running alongside the spec pipeline:

1. **Generation** by an agent with spec slice in context, producing code plus per-clause justification.
2. **Type checking** — compiler enforces spec-derived types.
3. **Property tests** derived from spec, run on every change.
4. **Runtime contracts** enforce remaining invariants.
5. **Traceability metadata** committed and CI-validated.
6. **Spec-drift detection** triggers re-review of implementation when spec clauses change.
7. **Formal proof** for the critical handful.
8. **AI review** as advisory layer.
9. **Human review** on the synthesized PR with all CI signals visible.

Each layer catches a different failure class. None alone is sufficient. The combination is what makes "AI-generated code follows the spec" a defensible claim rather than a hope.

## What this requires beyond the spec architecture

The spec architecture in [behind-the-curtain](behind-the-curtain.md) handles the upstream side. Implementation conformance is the downstream side, and is roughly as much work.

Required additions:

- **Spec store extensions.** Implementation-side metadata: traceability files, type-mapping declarations, contract-derived assertion templates.
- **CI infrastructure extensions.** The three traceability gates, property-test runners, runtime-assertion telemetry pipelines.
- **Agent fleet extensions.** A code-generation agent (consumes spec slice, produces code + justification), a property-test-derivation agent (consumes spec, produces tests), an AI-review agent (consumes PR + spec slice, produces structured review).
- **Orchestrator extensions.** Cross-repo coordination — when the spec repo merges a clause change, work is triggered in the implementation repo via webhooks or scheduled syncs.

Each piece is a narrow, well-understood engineering problem with existing tooling. The architecture is the same as before: small composable pieces, Git-native where possible, structured data with schemas, agents on narrow tasks, humans reviewing meaningful diffs.

## The honest limit

You cannot make *sure* AI-generated code follows the spec. You can stack layers that each catch a different class of failure, automate them to run on every change, and accept that residual risk lives where the layers do not reach. The goal is not certainty; it is reducing silent spec violations to a probability low enough that remaining ones surface at human review or in production telemetry.

The most important property of the whole pipeline: when a violation slips through, it must be *findable* — clear traceability from the production incident back to the violated spec clause and the failed (or missing) CI gate. Each violation becomes a learning event that strengthens the next layer.

This is the same logic as the upstream spec pipeline, applied to code: completeness handled mechanically where possible, goodness verified by humans where required, with the architecture making both kinds of work tractable at scale.

---

## Brownfield: existing code as R₀

The pipeline above assumes a spec exists. What about codebases that don't have one yet?

The pipeline as described works for any source of R₀, not just natural-language requirements. An existing codebase — possibly with years of accumulated production telemetry, postmortems, runbooks, and tribal knowledge — is a valid R₀. Treating brownfield retrofit as a special case is a category error; it is the standard pipeline with richer initial inputs.

This framing has implications worth naming explicitly.

### No separate retrofit phase

A naive retrofit treats spec extraction as a one-time bulk operation: run static analysis, mine invariants, walk the entire output, label every entry as intentional or accidental. This produces an unreviewable document — exactly the failure mode the readback layer was designed to prevent.

The iterative pipeline avoids this by construction. Round 1 stakeholders see entity proposals at a manageable rate; Round 2 stakeholders see state machines one entity at a time; rounds run in dependency order; closure conditions enforce stability before moving on. Brownfield retrofit becomes the normal work of the rounds, applied to code-as-source.

### Triage maps onto existing pipeline mechanisms

The four labels a retrofit must apply to extracted entries — *intentional*, *accidental-acceptable*, *accidental-wrong*, *disputed* — correspond to mechanisms the pipeline already has:

- **Intentional** is the normal "agent proposes, stakeholder accepts" flow. The extracted entry becomes a confirmed spec clause.
- **Accidental-acceptable** is a Round 8 assumption. "The code does this for no good reason but it works fine; we are inheriting it as an assumption with severity LOW and mitigation: tolerate."
- **Accidental-wrong** is a Round 5 counterexample. The code violates an invariant the spec should enforce. The clause is added to the spec; the violation is filed as a bug or remediation task; CI gates eventually catch the gap.
- **Disputed** is normal stakeholder disagreement, surfaced through readback in the standard way.

There is no separate triage phase because triage *is* the readback work the pipeline already performs.

### Per-round agent variants

The pipeline's agents need brownfield-specific prompt templates. The shape of each agent's output is unchanged; the input shape varies:

| Round | Greenfield input | Brownfield input |
|---|---|---|
| 1 | Informal requirement text | Code structures (types, classes, modules), DB schemas, API surfaces |
| 2 | Spec'd entity list | Code state enums, transition functions, event handlers |
| 3 | Spec'd input types | Code branches and validators (weak signal) |
| 4 | Spec'd entities | Cross-module call graphs (weak signal) |
| 5 | Stakeholder properties | Code + dynamic invariant traces from production runs (Daikon-style) |
| 6 | Quality checklist | Existing SLOs, monitoring configs, runbooks, alerts |
| 7 | STRIDE prompts | Existing security audits, threat models, incident history |
| 8 | Stakeholder probing | Postmortems, runbooks, comments, ADRs, deployment scripts |

Each row is a small, mechanical change to an existing agent prompt. The orchestrator selects the appropriate variant based on whether the spec repo is configured greenfield or brownfield (or, more commonly, mixed — original intent plus accumulated implementation reality).

### Rounds with weak code signal

Rounds 3, 4, 6, and 7 have weak signal from code. Code branches do not reliably correspond to intended equivalence classes; cross-module calls do not reliably reflect intentional interactions; quality SLOs are usually nowhere in code; threat models almost never are. These rounds run unchanged from the standard pipeline — they require fresh stakeholder thinking regardless of source.

The result is a spec with strong rounds 1, 2, 5, 8 (extracted-and-confirmed from rich brownfield sources) and rounds 3, 4, 6, 7 done at standard quality through normal stakeholder elicitation. This asymmetry is fine; the pipeline does not require uniform input strength across rounds.

### Conformance layers come online incrementally

The seven layers above apply to brownfield with one adjustment: adoption is incremental rather than complete from day one.

- **Layer 1** (spec in code-gen context) applies to *new* code only. Untouched legacy code stays untouched.
- **Layer 2** (types) tightens gradually as modules are modified. Languages with gradual typing make this practical.
- **Layer 3** (property tests) accumulates as spec clauses are confirmed.
- **Layer 4** (runtime contracts) adds with low friction; assertions can be sprinkled into existing code immediately.
- **Layer 5** (traceability) starts enforcing on every change from the moment the first spec clauses are confirmed. Legacy code is grandfathered until modified.
- **Layer 6** (formal proof) is rarely applied retroactively; reserved for new safety-critical components.
- **Layer 7** (AI review) applies immediately. The reviewer reads each PR with the relevant extracted spec slice and flags drift.

The pattern is *ratchet, not rewrite*: every change to legacy code is held to the new standard; existing code is grandfathered until modified. Coverage rises naturally without a big-bang rewrite.

### When brownfield is the wrong answer

Three signals suggest a codebase should not be retrofitted.

**Behavior is mostly accidental and mostly wrong.** If 80% of extracted candidates get labeled accidental-wrong during triage, the result is not a spec but a documentation of bugs. The right move is rewrite, not spec extraction.

**Original intent is genuinely lost.** If stakeholders cannot reliably triage extracted entries because nobody remembers what the code was supposed to do, the resulting spec is a guess. That spec has near-zero authority for resolving future disputes. Better to declare the system "as-is — no intentional spec," document the externally-visible contract surface only, and leave the internals unspecified until they are rewritten.

**Cost exceeds benefit window.** A multi-month retrofit of a system slated for replacement in two years is wasted effort. Document the contract surface and skip the internals.

For codebases that are actively maintained, well-understood by current stakeholders, and expected to live for years, brownfield retrofit through the standard pipeline is straightforwardly worth it.

### The greenfield implication

There is a corollary worth stating: as soon as code is written, the project becomes partially brownfield. The next iteration of the spec considers not just original stakeholder intent but also what the code now does. Spec drift, once code exists, can flow in either direction — the spec evolving, or the code evolving, or both. The pipeline handles this naturally because R₀ is allowed to grow over time and to include both intent and observed reality.

In practice this means: every project is greenfield for its first commit and brownfield from the second commit onward. The architecture treats both uniformly. The single pipeline serves both cases through choice of agent variants and choice of input sources.

## Closing synthesis

Specs Sense, in full: an algorithm that takes any source of intent and observed behavior and produces a behaviorally complete specification through nine rounds of mechanical gap-discovery iterated to a fixed point; a Git-based execution architecture that runs the algorithm at scale with AI agents on narrow tasks and humans reviewing meaningful diffs; a seven-layer conformance pipeline that ensures generated code respects the spec; uniform application to both greenfield and brownfield projects; and an honest acknowledgment that two irreducibles — scope declaration and intent recognition — remain places where human judgment cannot be factored out.

Everything between those two endpoints is mechanical and exhaustive. The methodology surfaces gaps; humans decide which gaps matter. The architecture's job is to make both kinds of work tractable at scale, even when the spec runs to tens of thousands of words and the codebase to hundreds of thousands of lines.

Done well, this turns specification from a document nobody reads into a living artifact that the implementation actually has to honor — and that human reviewers can engage with at a sustainable pace, week after week, until the system stabilizes at its fixed point.

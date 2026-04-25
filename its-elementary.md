# Its elementary

## Specs Sense / 2 — The algorithm ##

Where this fits: this file describes the algorithm itself — nine rounds of mechanical gap-discovery iterated to a fixed point. It is format-agnostic and tooling-agnostic. A reader could run it with paper and pencil. The framing of why it exists is in [i-see-dead-specs](i-see-dead-specs.md). How it actually runs as a system, with Git, JSON, and AI agents, is in [behind-the-curtain](behind-the-curtain.md). How spec connects to code is in [ghosts-in-the-code](ghosts-in-the-code.md).

## Termination guarantee

Let R_n denote the requirement set after iteration n. The sequence {R_n} is monotonically increasing in a finite lattice — the set of behaviorally distinct scenarios over a bounded scope. Every monotonically increasing sequence in a finite lattice stabilizes. Therefore the algorithm reaches a fixed point in finite time.

This guarantee depends on three assumptions stated explicitly in [i-see-dead-specs](i-see-dead-specs.md): a bounded scope can be named, stakeholders can recognize intent when shown a scenario, and the specification language admits mechanical consistency checking. Violations of these assumptions do not break termination but may cause the resulting specification to diverge from true stakeholder intent. Mitigation lives in the readback layer, described in [behind-the-curtain](behind-the-curtain.md).

## Round 1: Universe construction

### Goal
Enumerate the vocabulary of the system. Nothing downstream can reference a concept that is not declared here.

### Procedure

1. Extract all nouns from R₀ and any clarifying discussion. For each noun, decide whether it is an entity (stateful, has identity), a value (attribute of an entity), or a role (actor).
2. For each entity, list attributes. For each attribute, declare type and value range.
3. Extract all verbs. For each verb, identify subject (actor or entity), object (entity affected), and side effects (which other entities change state).
4. Enumerate actors. For each actor, list permitted verbs and primary concerns.
5. Prompt stakeholders: "What entity / verb / actor is missing?" Record answers. Repeat until a round of prompting produces no additions.

### Closure condition
Three consecutive prompting rounds produce no new entries in any of the three catalogs.

### Artifacts produced
- Entity catalog (table: entity, attributes, types, ranges, notes)
- Verb catalog (table: verb, subject, object, side effects)
- Actor catalog (table: actor, permitted verbs, concerns)

## Round 2: State-event matrix

### Goal
For each stateful entity, exhaustively specify the transition behavior under every possible event.

### Procedure

1. For each entity with identity, identify its lifecycle states. States are mutually exclusive; every instance of the entity is always in exactly one.
2. Enumerate all events that can affect the entity. Events include external triggers, internal completions, failures, timeouts, and actor-initiated operations.
3. Construct the Cartesian product State × Event as a matrix. Each cell represents "what happens if this event occurs while the entity is in this state."
4. Fill every cell with one of:
   - A transition to a named next state, plus any actions (side effects).
   - An explicit no-op rule with rationale ("ignore; log").
   - An explicit "impossible by construction" with justification (e.g., this event cannot occur in this state because an earlier invariant forbids it).
5. For transitions, specify: guard conditions, output events, effects on other entities.
6. Review: for each "impossible by construction" cell, verify the invariant that makes it impossible is actually enforced elsewhere.

### Closure condition
Zero empty cells. Every "impossible" claim is backed by an explicit enforcement mechanism.

### Artifacts produced
- One state-event matrix per stateful entity
- A transition table: (state, event) → (next_state, guard, actions, output_events)

### Hoare-logic interpretation
Each non-empty cell is a triple:
```
{ entity.state = S ∧ event = E ∧ guard }
  handle_event(entity, event)
{ entity.state = S' ∧ actions_applied }
```

## Round 3: Input space partitioning

### Goal
Divide each input dimension into equivalence classes such that all values within a class receive the same specified treatment, and specify behavior per class.

### Procedure

1. From the entity and verb catalogs, list every input dimension: parameters of operations, attributes read from the environment, externally-supplied values.
2. For each dimension, identify natural boundaries: type limits, physical limits, business limits, performance regime changes, error modes.
3. Partition the value space into a finite set of equivalence classes. Name each class.
4. For each class, specify behavior: acceptance, rejection, alternative path, warning, escalation.
5. For each boundary between classes, explicitly assign the boundary value to exactly one class. Record the choice and rationale.
6. For each class, add test-representative values: the minimum, typical, and maximum of the class.

### Closure condition
Every input dimension has complete partition coverage (classes are mutually exclusive and collectively exhaustive). Every boundary is assigned. Every class has specified behavior.

### Artifacts produced
- Partition table per input dimension (columns: class, range, behavior, representative values)

### Hoare-logic interpretation
Preconditions on operations become disjunctions over classes:
```
{ input ∈ class_1 ∨ input ∈ class_2 ∨ ... }
  operation(input)
{ ... }
```

## Round 4: Cross-product interaction matrix

### Goal
Specify behavior for every meaningful interaction between entities.

### Procedure

1. List entity pairs (and triples, where interactions are genuinely three-way). Not all pairs have meaningful interaction; prune by inspection.
2. For each meaningful pair (A, B), enumerate the situations in which A and B co-exist in states that could conflict or affect each other.
3. For each such situation, specify joint behavior: which entity's rule takes precedence, whether the operation is deferred, rejected, or requires coordination.
4. Pay particular attention to:
   - Same-entity concurrency (two operations on one entity).
   - Lifecycle overlaps (one entity depends on another that is being deleted, retired, or modified).
   - Resource contention (entities competing for shared capacity).
   - Temporal ordering (events from different entities arriving in unexpected order).

### Closure condition
Every meaningful pair has been inspected. For each pair, either the interaction is specified or explicitly marked as "independent — no interaction possible."

### Artifacts produced
- Interaction table (columns: entity A, entity B, situation, specified behavior, rationale)

### Hoare-logic interpretation
Multi-entity preconditions emerge:
```
{ A.state = S_A ∧ B.state = S_B ∧ joint_condition }
  operation_on(A, B)
{ joint_postcondition }
```

## Round 5: Formal invariants

### Goal
Express system-wide properties that must hold across all states and transitions, in a logic that admits mechanical checking.

### Procedure

1. From the preceding rounds, identify statements of the form "X is always true" (safety), "Y eventually happens" (liveness), "no starvation" (fairness).
2. Translate each into a formal specification language. Preferred: Quint (executable specs, inspired by TLA but with modern syntax, integrates Apalache and TLC as model-checker backends). Alternatives: Alloy for structural properties; Z or VDM for pre/post-style.
3. For each invariant, identify which actions could violate it. This produces a proof obligation: for each such action, show the invariant is preserved.
4. Run a model checker (Quint's simulator via `quint run` for quick feedback; Apalache or TLC backends via `quint verify` for exhaustive checking; Alloy Analyzer; SPIN for Promela) over a bounded instance of the model.
5. For each counterexample produced, one of two outcomes:
   - The counterexample reveals a missing requirement: add it and re-run.
   - The counterexample reveals an over-strong invariant: weaken it.
6. Iterate until the model checker produces no counterexamples within the bounded instance.

### Closure condition
Zero counterexamples from the model checker within the declared scope bounds. Every invariant has an explicit list of actions that must preserve it.

### Artifacts produced
- Formal specification file
- Invariant list with proof obligations
- Model-checker configuration and result log

### Hoare-logic interpretation
Invariants are universal postconditions: every triple in the system must preserve them.
```
∀ triple { P } S { Q } in specification.
  { P ∧ Invariant } S { Q ∧ Invariant }
```

## Round 6: Quality-attribute matrix

### Goal
Specify non-functional requirements across all relevant quality dimensions, each with measurable acceptance criteria.

### Procedure

1. Walk a standard quality-attribute checklist. Include at minimum: security, performance, scalability, availability, observability, recoverability, compliance, cost, maintainability, deprecation, accessibility, internationalization.
2. For each attribute, decompose into sub-attributes relevant to this system.
3. For each sub-attribute, specify:
   - Target (the desired behavior or bound).
   - Acceptance criterion (how success is measured).
   - Test method (how the criterion is checked).
4. For sub-attributes deemed not applicable, record explicitly: "not applicable because ___."

### Closure condition
Every row of the quality-attribute checklist is either specified with a target, acceptance criterion, and test method, or marked not applicable with rationale.

### Artifacts produced
- Quality-attribute matrix (columns: quality, sub-attribute, target, acceptance criterion, test method)

### Hoare-logic interpretation
Non-functional postconditions, often requiring temporal or probabilistic extension:
```
{ P }  operation  { Q ∧ duration ≤ T ∧ resource_use ≤ B }
```

## Round 7: Adversarial scenario catalog

### Goal
Enumerate hostile or abusive scenarios and specify required mitigations.

### Procedure

1. Apply a threat-modeling framework. STRIDE (Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege) is a standard starting point.
2. For each category, generate scenarios specific to this system. Prompts:
   - Who would benefit from compromising this?
   - What is the most valuable asset to protect?
   - What attacks have hit similar systems?
3. Rotate through personas: malicious outsider, compromised insider, curious insider, negligent operator, state actor, extortionist.
4. For each scenario, specify:
   - Affected asset.
   - Attack vector.
   - Required mitigation (which becomes a functional or quality requirement).
5. Generate scenarios mechanically where possible: fuzz-test inputs, chaos-engineering faults, time-skew attacks, resource-exhaustion attacks.

### Closure condition
N consecutive generated scenarios (suggested N = 20) produce no new mitigation requirements.

### Artifacts produced
- Adversarial catalog (columns: category, scenario, affected asset, vector, mitigation requirement)

### Hoare-logic interpretation
Adversarial postconditions with universal quantification over hostile action sequences:
```
∀ attacker_action_sequence α.
  { initial_state }  α  { safety_invariants_preserved }
```

## Round 8: Assumption excavation

### Goal
Make every implicit assumption explicit. Each assumption either becomes a precondition of the system or a requirement to handle its violation.

### Procedure

1. Review all preceding artifacts. For each requirement, ask: "what must be true about the world for this to work?"
2. Categories of assumption to probe:
   - Environmental (network, time, hardware, third-party services).
   - Data (format, encoding, size, language, validity).
   - Human (operator competence, availability, training).
   - Organizational (legal authority, policy stability, personnel retention).
   - Technological (platform longevity, API stability, algorithm soundness).
3. For each assumption, record:
   - Statement of the assumption.
   - Risk if violated.
   - Severity (low / medium / high / critical).
   - Mitigation: either accept the risk, transfer it (insurance, contract), reduce it (detection, fallback), or convert it to a requirement ("system must detect and handle violation of A").
4. Reference the assumption from every requirement that depends on it. This produces a traceability graph.

### Closure condition
Assumption-storming sessions with the stakeholder panel produce no new entries for three consecutive rounds.

### Artifacts produced
- Assumption registry (columns: ID, statement, risk, severity, mitigation, referenced by)

### Hoare-logic interpretation
Assumptions are system-level preconditions:
```
{ system_preconditions ∧ A_1 ∧ A_2 ∧ ... }
  system_operation
{ guarantees }
```

## Round 9: Cross-pass to fixed point

### Goal
Re-execute rounds 1 through 8 with the now-expanded model. Each pass typically discovers new entries. Continue until a full pass produces zero additions.

### Procedure

1. Re-run Round 1. New entities discovered in later rounds (catalogs, quotas, approvals, audit events) often need to be added to the universe.
2. Re-run Round 2 for any new stateful entity. Build its state-event matrix.
3. Re-run Round 3 for any new input dimension.
4. Re-run Round 4 including the new entities in the cross-product.
5. Re-run Round 5, adding invariants involving the new entities, and re-running the model checker.
6. Re-run Round 6 to check whether new entities introduce new quality concerns.
7. Re-run Round 7 to generate new adversarial scenarios involving the new surface.
8. Re-run Round 8 to catalog new assumptions exposed by the expanded model.
9. Count new entries added by this pass. If > 0, repeat from step 1.

### Closure condition
One full cross-pass produces zero additions in every round.

### Termination metric
Expected number of cross-passes: 3 to 6 for a moderately complex system. More than 8 indicates scope is poorly bounded or stakeholders disagree on intent; pause and revisit scope declaration S.

## Consolidation: Hoare-contract assembly

### Goal
Reassemble the distributed pre/post-conditions from rounds 2, 3, 4, 5, 7, 8 into per-operation contract files.

### Procedure

For each operation in the verb catalog, produce a contract:

```
operation: <operation_name>(<parameters>)

  requires:
    - <precondition from Round 1 entity validity>
    - <precondition from Round 3 input partition>
    - <precondition from Round 4 cross-entity condition>
    - <assumption reference from Round 8>
    - <actor permission from Round 1 actor catalog>

  ensures:
    - <postcondition from Round 2 state transition>
    - <side effect from Round 2 action>
    - <audit obligation from Round 7 mitigation>
    - <quality obligation from Round 6>

  preserves (invariants):
    - <invariant from Round 5>
```

Each clause carries a reference back to the round and artifact that produced it. This reference is the traceability link used in Round 9's closure check and in the conformance pipeline described in [ghosts-in-the-code](ghosts-in-the-code.md).

### Closure condition
Every operation in the verb catalog has a contract file. Every clause in every contract traces to a specific upstream artifact.

## Test derivation

Each round produces a directly-derivable class of tests. The test set is a mechanical projection of the specification.

| Round | Test class | Derivation rule |
|---|---|---|
| 2 | State-transition | One test per non-impossible cell: set up pre-state, inject event, assert post-state and actions |
| 3 | Boundary and equivalence | Three tests per class boundary (below, at, above); one per equivalence class representative |
| 4 | Cross-entity interaction | One integration test per row of the cross-product table |
| 5 | Property-based + model-check | Each invariant becomes a property test (generate random operation sequences, assert invariant holds); run model checker directly on the formal spec |
| 6 | Acceptance and SLO | Each acceptance criterion becomes a test; performance criteria become load tests and ongoing probes |
| 7 | Security and chaos | Each adversarial scenario becomes a security test or fault-injection test |
| 8 | Assumption-violation | Each assumption becomes a negative test: violate the assumption, verify the system detects and handles it per the declared mitigation |

### Closure condition
Every specification artifact has at least one derived test. Every test traces to a specific artifact. Orphans in either direction are resolved by adding the missing test or removing the orphaned test.

## Global termination check

The algorithm as a whole terminates when all of the following hold simultaneously:

1. Round 1 catalogs are stable across three prompting rounds.
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

When all eleven conditions hold, the specification is at its fixed point over the declared scope.

## Scope revision as meta-loop

Scope S is declared before Round 1 and held fixed during the main loop. However, running the algorithm often reveals that S itself was wrong: a case "out of scope" turns out to matter, or a case "in scope" turns out to be ill-defined.

When this happens:

1. Exit the main loop.
2. Revise S with explicit rationale for the change.
3. Restart from Round 1. Much of the work from prior iterations carries forward; the algorithm is idempotent where scope did not change.

Scope revision is bounded by stakeholder patience and calendar, not by the algorithm. In practice, 2 to 4 scope revisions are typical before the first stable fixed-point specification.

## What's next

The algorithm above is format-agnostic. To run it as an actual system — with a versioned store, AI agents handling rounds in parallel, human reviewers processing diffs at a manageable rate, and the whole loop coordinated by an orchestrator — see [behind-the-curtain](behind-the-curtain.md).

To connect the produced specification to actual code (or to start from existing code instead of a blank slate), see [ghosts-in-the-code](ghosts-in-the-code.md).

// Round 5 — Formal invariants
//
// Quint module. Run locally:
//   quint typecheck spec/round-5/invariants.qnt
//   quint run       spec/round-5/invariants.qnt --invariant=allInvariants
//   quint verify    spec/round-5/invariants.qnt --invariant=allInvariants
//
// Every invariant declared here must have a matching entry in
// invariant-rationale.json that carries the human-readable _note plus the
// list of actions that could violate it.
//
// This file is an empty scaffold. The Round 5 agent fills it as the spec
// grows. See agents/round-5-invariant.md.

module Spec {

  // ---- State ---------------------------------------------------------------
  // Declare `var` bindings as you add stateful entities (Round 1) and
  // their lifecycle states (Round 2). Example shape:
  //
  //   type FooState = INITIAL | ACTIVE | RETIRED
  //   var foos: Set[{ id: int, state: FooState }]

  // ---- Initial state ------------------------------------------------------

  action init = all {
    // Set every `var` to its initial value here, e.g. `foos' = Set()`.
  }

  // ---- Actions ------------------------------------------------------------
  // One `action` per state-event cell that mutates state. Wire them into
  // `step` so the model checker can explore reachable states.

  action step = all {
    // Replace with `any { actionA, actionB, ... }` as you add actions.
  }

  // ---- Invariants ---------------------------------------------------------
  // One `val ... = <bool predicate>` per invariant. AND them into
  // `allInvariants` below. Each must have a matching entry in
  // invariant-rationale.json with the same `qnt_name`.

  val allInvariants = true
}

# Scope

> **This file is human-authored. Agents may read it but must not modify it.**
> Scope is the input the algorithm takes; it cannot bootstrap its own purpose.
> Revising scope is a meta-decision that exits the main loop. See [its-elementary.md § Scope revision as meta-loop](../../docs/its-elementary.md).

> **DELETE-ME — how to use this file:** every section below has a `DELETE-ME — guidance` blockquote and a `TODO` placeholder. Replace each `TODO` with real content, then delete the matching guidance blockquote. Search the file for `DELETE-ME` to find anything still pending.

## Mode

> **DELETE-ME — guidance:** one of `greenfield`, `brownfield`, or `mixed`.
> - `greenfield` — no existing code; pipeline drives entirely from informal requirements and stakeholder input.
> - `brownfield` — existing codebase as primary R₀; pipeline extracts spec from code + operational evidence.
> - `mixed` — existing code being extended with a new feature; both stakeholder text and code as inputs.
>
> The orchestrator reads this field to pick agent input variants per round.

`TODO`

## System under specification

> **DELETE-ME — guidance:** one sentence. What is this system? Example: *"An online cinema-ticket reservation system serving a single chain of theaters in one country."*

TODO

## In scope

> **DELETE-ME — guidance:** bulleted list of capabilities, entities, integrations, environments, and user populations the spec WILL cover. Be concrete. Vague scope is the leading cause of runaway cross-pass counts in Round 9.

- TODO

## Out of scope

> **DELETE-ME — guidance:** equally important. Bulleted list of things explicitly NOT covered. Each entry should be something a reasonable reader might otherwise expect to be in scope.

- TODO

## Stakeholder panel

> **DELETE-ME — guidance:** named roles (and ideally named people) who have authority to answer questions for each domain. The orchestrator routes PRs to these stakeholders by label.

| Role | Owner | Responsibility |
|---|---|---|
| Domain expert | TODO | Recognizes intent for entities, verbs, state transitions |
| End user representative | TODO | Validates user-facing flows |
| Security officer | TODO | Reviews Round 7 adversarial scenarios |
| Operations lead | TODO | Reviews Round 6 quality and Round 8 operational assumptions |
| Compliance / legal | TODO | Reviews Round 6 compliance, Round 8 organizational assumptions |
| Architect | TODO | Reviews Round 4 interactions, Round 5 invariants |

## Bounded constants

> **DELETE-ME — guidance:** concrete bounds for the model checker in Round 5. Bounds must be small enough to verify exhaustively, large enough to expose representative behavior.

- Max concurrent users: TODO
- Max items per transaction: TODO
- Max retries: TODO

## Evidence sources

> **DELETE-ME — guidance:** required when Mode is `brownfield` or `mixed`. Greenfield projects may leave subsections blank or write `n/a — greenfield`.
>
> The orchestrator reads this section to compute per-round context budgets — which files / dashboards / archives to slice into the prompt for each agent invocation. Agents themselves do NOT read scope.md; they receive the relevant slice from the orchestrator. This is the single project-wide pointer table.
>
> For each subsection, list locations as paths (relative to repo root) or URLs. Add one-line annotations where the source is non-obvious. The orchestrator uses the Round → subsection mapping in each subsection header below.

### Codebase  *(used by rounds 1, 2, 3, 4, 5)*

- **Repository:** TODO  *(URL or local path)*
- **Languages / frameworks:** TODO
- **Module / entry-point map:** TODO
  - `<path>` — `<one-line description>`
- **Build & test commands:** TODO  *(so the orchestrator can validate proposals against a real build)*

### Operational telemetry  *(used by round 6)*

- **Monitoring dashboards:** TODO
- **Alert configuration:** TODO
- **SLO definitions / error budgets:** TODO
- **Performance reports / capacity-planning docs:** TODO

### Dynamic invariant evidence  *(used by round 5)*

- **Tracing / Daikon-style tool:** TODO
- **Trace store location & retention:** TODO
- **Production assertion log:** TODO

### Documentation archives  *(used by rounds 1, 5, 8)*

- **Postmortems:** TODO
- **Runbooks:** TODO
- **ADRs:** TODO
- **Architecture / design docs:** TODO

### Security artifacts  *(used by round 7)*

- **Past audits / pentests:** TODO
- **Threat models:** TODO
- **Bug-bounty submissions:** TODO
- **WAF / IDS / abuse-reporting tickets:** TODO

### Compliance  *(used by round 6)*

- **Applicable regulations:** TODO
- **Audit checklists in use:** TODO
- **Data-residency / retention policies:** TODO

## Revision log

> **DELETE-ME — guidance:** append-only. Every scope revision documented with date, change, and rationale. A scope revision restarts the main loop from Round 1.

| Date | Pass # | Change | Rationale |
|---|---|---|---|
| YYYY-MM-DD | 0 | Initial scope | — |

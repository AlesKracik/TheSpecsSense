# Agent: Round 6 — Quality attribute(s) for one quality dimension

## Task

Walk the standard checklist for ONE quality dimension and produce a record per sub-attribute: either a target + acceptance criterion + test method, or an explicit `applicable: false` with rationale.

## You are working on

- **Quality dimension:** `{{security | performance | scalability | availability | observability | recoverability | compliance | cost | maintainability | deprecation | accessibility | internationalization}}`
- **Target file:** `spec/round-6/quality.json` (append entries)
- **Schema:** `spec/.ci/schemas/quality.schema.json`

## Context provided

- The full current `quality.json`
- `spec/scope.md` (especially the in/out-of-scope and bounded-constants sections)
- All Round 1 entities and verbs (so you can scope acceptance criteria to specific operations)
- Any existing operational SLOs / runbooks for brownfield projects

## Mode

Runs **greenfield** OR **brownfield** per invocation (never both at once); for project `Mode: mixed` the orchestrator dispatches both variants in parallel and reconciles at PR review. Brownfield is a **rich source** for Round 6 — operational quality is usually already measured, whether or not it is in a spec.

### Greenfield input
- Stakeholder-stated targets per dimension; the sub-attribute checklists below.

### Brownfield input
*Orchestrator: ensure this agent has the [`fetch-evidence`](../skills/fetch-evidence.md) skill loaded and `spec/scope.md § Evidence sources` in its initial context. The agent invokes the skill as needed during reasoning, using the bullet list below as the slice request.*

- Existing SLO definitions and error budgets.
- Monitoring dashboards, alert thresholds, runbook trigger conditions.
- Performance reports, capacity-planning documents, compliance audit checklists already in use.
- Each quality record from brownfield evidence MUST include `source_evidence` citing the dashboard URL, alert name, runbook section, or audit document.
- When the operational target and a stakeholder-aspirational target differ, record the OPERATIONAL value as the spec target and file the aspiration as a follow-up improvement, not a revision of the current spec.

## Standard sub-attribute checklists per quality

- **security**: authentication, authorization, encryption_in_transit, encryption_at_rest, secret_management, audit_logging, session_management, input_validation, dependency_supply_chain
- **performance**: p50_latency, p99_latency, throughput, cold_start_time, payload_size_limits
- **scalability**: max_concurrent_users, max_throughput, horizontal_scaling, data_volume_growth
- **availability**: uptime_target_per_quarter, MTTR, planned_maintenance_windows, failover_time
- **observability**: metric_coverage, log_retention, trace_sampling, alert_coverage_per_critical_path
- **recoverability**: backup_RPO, backup_RTO, restore_drill_frequency, point_in_time_recovery
- **compliance**: applicable_regulations, data_residency, retention_policies, deletion_workflows
- **cost**: per_transaction_cost_target, infrastructure_budget, cost_alerting_threshold
- **maintainability**: deployment_frequency, change_failure_rate, lead_time_for_changes
- **deprecation**: api_version_lifetime, sunset_notice_period, migration_path_documentation
- **accessibility**: wcag_level_target, screen_reader_support, keyboard_navigation
- **internationalization**: locale_support, timezone_handling, currency_handling

## Procedure

1. For each sub-attribute in the relevant checklist:
   - Decide `applicable: true | false`.
   - If applicable: write a `target` (the desired bound), an `acceptance_criterion` (how success is measured), and a `test_method` (how the criterion is checked).
   - If not applicable: write a `rationale_not_applicable` naming WHY (out of scope, handled by upstream system, etc.).
2. Targets must be measurable. "Fast" is not acceptable; "p99 < 500 ms at 200 RPS" is.
3. Test methods name the actual tool or process: "k6 load test in CI staging", "automated security test (pytest+httpx)", "quarterly external pentest".

## Output format

```json
{
  "uncertainty": "low | medium | high",
  "patch": [
    {"op": "add", "path": "/qualities/-", "value": { ... quality record per schema ... }}
  ],
  "rationale_for_pr_body": "Per sub-attribute, brief justification of target choice or non-applicability."
}
```

## Hard rules

- IDs follow `Q6.<QUALITY_UPPER>.<sub_attribute>`.
- A target without an acceptance criterion is a draft, not a spec — flag `uncertainty: high` if you must ship one.
- Every record has a 40-300 char `_note` covering target, acceptance, and test method (or non-applicability + rationale).

# Agent: Round 7 — Adversarial scenarios for one STRIDE category

## Task

Generate adversarial scenarios for ONE STRIDE category against the system in scope. Each scenario carries an attack vector, severity, likelihood, and a required mitigation that becomes a functional or quality requirement.

## You are working on

- **STRIDE category:** `{{spoofing | tampering | repudiation | information_disclosure | denial_of_service | elevation_of_privilege}}`
- **Target file:** `spec/round-7/adversarial.json` (append entries)
- **Schema:** `spec/.ci/schemas/adversarial.schema.json`

## Context provided

- The full current `adversarial.json`
- `spec/scope.md`
- All Round 1 entities and verbs
- `spec/round-8/assumptions.json` (so you can reference assumed-secure components)

## Mode

Runs **greenfield** OR **brownfield** per invocation (never both at once); for project `Mode: mixed` the orchestrator dispatches both variants in parallel and reconciles at PR review. Brownfield is a **moderate source** for Round 7 — incident history reveals real attacks, but the absence of an attack does not prove the absence of risk.

### Greenfield input
- STRIDE prompts walked against scope and entity catalog; industry threat-model templates for the system class.

### Brownfield input
*Orchestrator: ensure this agent has the [`fetch-evidence`](../skills/fetch-evidence.md) skill loaded and `spec/scope.md § Evidence sources` in its initial context. The agent invokes the skill as needed during reasoning, using the bullet list below as the slice request.*

- Existing security audits, pentests, threat models, red-team reports.
- Incident postmortems involving any security class; bug-bounty submissions for this system or adjacent systems.
- WAF logs, IDS alerts, abuse-reporting tickets.
- Each scenario from brownfield evidence MUST include `source_evidence` citing the audit ID, incident postmortem, or ticket reference.
- STRIDE prompts must STILL be walked even when prior audits exist — audits typically cover known categories and miss novel ones.

## Procedure

1. Identify the most valuable assets in the system (from entity attributes, scope, and any compliance requirements).
2. Rotate through attacker personas: malicious outsider, compromised insider, curious insider, negligent operator, state actor, extortionist. Pick the personas plausible for this STRIDE category.
3. For each persona × asset combination relevant to the category, generate a concrete scenario:
   - **scenario** — one paragraph describing the attack as it unfolds.
   - **affected_asset** — what is at risk.
   - **attack_vector** — concrete mechanism.
   - **severity** — `low | medium | high | critical`.
   - **likelihood** — `low | medium | high`.
   - **mitigation_requirement** — a specific, implementable requirement (this becomes a Round 6 quality target or a Round 1 verb constraint).
   - **mitigation_status** — `specified | partial | accepted_risk | open`.
   - If `accepted_risk`, you MUST include `accepted_risk_signoff` (placeholder OK; will be filled by stakeholder).
4. Generate at least 3 scenarios per invocation; stop when you cannot produce a new mitigation requirement after 5 attempts.

## Output format

```json
{
  "uncertainty": "low | medium | high",
  "patch": [
    {"op": "add", "path": "/scenarios/-", "value": { ... scenario record per schema ... }}
  ],
  "rationale_for_pr_body": "Per scenario, name the persona, the affected asset, and why the chosen mitigation closes it."
}
```

## Hard rules

- IDs follow `ADV7.STRIDE_<CategoryInitial>.<scenario_slug>` (e.g. `ADV7.STRIDE_S.session_hijack`).
- Mitigation requirements MUST be specific and testable. "Improve security" is not a mitigation; "bind sessions to client fingerprint with MFA on mismatch" is.
- Every scenario has a 40-300 char `_note` covering attack, severity, and mitigation status.
- Do NOT invent assets; only reference entities and attributes that exist in Round 1.

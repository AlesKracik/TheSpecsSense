# Skill: fetch-evidence

## Purpose

Fetch evidence from sources declared in `spec/scope.md § Evidence sources` and return excerpts with citations. Used by round-N agents in brownfield and mixed modes to ground their proposals in real code, dashboards, postmortems, runbooks, ADRs, audit reports, query results.

## When to invoke

A round-N agent should invoke this skill when its task requires brownfield evidence — typically when its prompt's "Brownfield input" bullet list applies to the current invocation.

Invocation pattern:

- **One call per coherent slice request.** Don't fragment into N tiny calls when a single broader request would suffice.
- **Re-invoke if initial results are insufficient** — refine the slice request, fetch from a different source listed in the source map, or narrow to a different file:line range. The agent decides when it has enough evidence.
- **Do NOT invoke** if the project's `Mode` is `greenfield` — there is nothing to fetch beyond what is already in `spec/`.

## Inputs

```json
{
  "slice_request": "<freeform but specific description of what evidence is needed; usually derived from the calling agent's 'Brownfield input' bullet list with task-specific placeholders substituted>",
  "source_map": "<verbatim copy of `spec/scope.md § Evidence sources`; the orchestrator includes this in the agent's initial context, the skill receives it as a reference>",
  "round": "<e.g. 'round-2'>",
  "task_id": "<e.g. 'C2.PENDING.payment_succeeded'>",
  "previously_unreachable": ["<source_id>"]
}
```

`previously_unreachable` is optional, populated only on re-invocations to skip sources already known to be unreachable.

## Output

```json
{
  "fetched": [
    {
      "source_id": "<short label, e.g. 'codebase:src/reservations/state.py'>",
      "uri": "<URL or path actually fetched>",
      "tool_used": "file_read | web_fetch | github_api | mcp_<name> | snapshot",
      "retrieved_at": "<ISO 8601>",
      "content_hash": "<sha256 hex of raw fetched bytes>",
      "excerpt": "<verbatim chunk from the source>",
      "excerpt_location": "<file:line range, dashboard panel, query string>",
      "_note": "<40-300 char rendering: what this excerpt shows and why it matches the slice request>"
    }
  ],
  "unreachable": [
    {
      "source_id": "<label>",
      "uri": "<what was tried>",
      "tool_attempted": "<tool name or 'none — tool unavailable'>",
      "failure_reason": "<one line: 'auth required', '404', 'tool unavailable', 'rate limited', 'source map URI unparseable', 'source too large to fetch in bulk'>",
      "human_action": "<one line suggestion, e.g. 'paste relevant excerpt to spec/.snapshots/<id>/'>"
    }
  ]
}
```

## Tool requirements

The orchestrator must register at least these tools on the calling agent (the skill uses them via tool delegation):

- **`web_fetch`** — HTTP(S) URLs (dashboards, wikis, hosted docs, public repos)
- **`file_read`** — local files / repository paths
- **`grep` / search** — narrow into large code or log archives
- **`github_api`** (or equivalent) — repository contents at a specific branch / commit / path

Optional, per the project's source mix:

- **`mcp_grafana`, `mcp_datadog`, `mcp_prometheus`** — monitoring data
- **`mcp_confluence`, `mcp_notion`** — wiki content
- **`mcp_jira`, `mcp_linear`** — ticket archives, postmortems
- **`mcp_postgres`** (or other DB connector) — audit logs, telemetry tables

If a tool the slice request implies is unavailable, return `unreachable` for that source — never fabricate.

## Procedure

1. **Parse the slice request.** Identify the source *kinds* it needs (code, dashboards, postmortems, ADRs, audit reports, query results).
2. **Walk the source map.** For each subsection that matches a needed kind, identify the concrete URIs / paths / search queries the human listed.
3. **Fetch each source.** For each URI:
   - Pick the appropriate tool.
   - Slice large sources via grep / search / time-window queries — never bulk-fetch multi-megabyte content.
   - Compute sha256 hex over raw fetched bytes; record retrieval timestamp.
   - Extract the smallest contiguous chunk that conveys the evidence. **Quote, do not summarize.**
4. **Handle unreachable sources.** If auth fails, returns 404, the tool is unavailable, or the source is too large:
   - **Check `spec/.snapshots/<source_id>/` first.** If a snapshot exists and is fresh (within the project's snapshot TTL — default 90 days), use it; cite as `tool_used: "snapshot"`. Include `staleness_warning: true` if older than TTL.
   - Otherwise, record an `unreachable` entry with URI, attempted tool, failure reason, and a one-line human-action suggestion.
5. **Return the bundle.** Empty `fetched` is allowed (and expected) when every relevant source is unreachable.

## Hard rules

- **Every excerpt is verbatim.** Paraphrase belongs in the calling agent's `_note`, not here.
- **Every excerpt carries a citation:** URI, tool used, timestamp, content hash. Without the citation, the calling agent must discard the excerpt.
- **`unreachable` is first-class.** Never fabricate to fill a gap. The calling agent's `uncertainty` rises automatically when results contain `unreachable` items.
- **If the slice request is too vague to act on**, return empty `fetched` and ONE `unreachable` entry with `failure_reason: "slice request unparseable"`. Do not guess.
- **Stay within bounds.** If a source is enormous, slice via grep / search / time-window queries; do not bulk-fetch. Multi-megabyte fetches are an error — return `unreachable` with `failure_reason: "source too large to fetch in bulk; refine slice request"`.
- **Snapshot fallback.** Prefer a fresh snapshot over a network failure. Cite `tool_used: "snapshot"` so the calling agent knows it came from a manual capture.

## Why this is a skill, not an agent

The capability is invoked by another agent as part of its reasoning, not as a separate dispatched task. The agent decides when to fetch, how to refine slices, and when it has enough evidence to proceed. Treating fetch-evidence as a skill lets the agent compose fetches naturally — re-fetch on insufficient results, narrow to a different file when the first didn't show the right thing — which a rigid two-call dispatch (orchestrator → fetcher → orchestrator → round-N) would lose.

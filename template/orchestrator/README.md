# Orchestrator — minimum-viable reference implementation

A small, deterministic Python program that drives the Specs Sense loop: detect open work, dispatch the right agent against the right context slice, open PRs, and process stakeholder decisions.

## Status: MVP

Round 1 (universe agent) is wired end-to-end. Rounds 2-9 + contracts have detector stubs and `dispatch.py` `ROUND_CONFIGS` slots — adding the next round is ~30 lines (one detector function + one config entry). See [state-machine.md](state-machine.md) for the full transition rules and how the orchestrator infers state from Git.

What this MVP **does**:
- Reads `spec/scope.md` to determine project mode.
- Detects open Round 1 work (catalogs empty or `scope.md` modified since last `pass-N` tag).
- Dispatches the round-1-universe agent via the Anthropic SDK with prompt caching.
- Validates structured output (forced via `tool_choice` on a `submit_proposal` tool).
- Applies the JSON Patch to the target catalog file.
- Opens a PR via `gh` CLI with severity / round / `needs-human-review-first` labels as appropriate.
- Logs every event to `.orchestrator/logs/`, tracks tokens + USD in `.orchestrator/cost.json`, snapshots running state in `.orchestrator/status.json`, and saves full LLM transcripts in `.orchestrator/transcripts/`.

What this MVP **does not yet do** (TODOs in code):
- Rounds 2-9 + contract assembly dispatch.
- Quint integration for Round 5 (counterexample interpretation, `quint verify` gate).
- PR-event processing for `needs-rework` re-dispatch (would require either a webhook listener or a polling `gh pr list` loop).
- Multi-task parallelism within one pass.
- The `fetch-evidence` skill — agents currently run greenfield-only. Brownfield/mixed mode requires either registering the skill with the agent (Claude Agent SDK / Skills API) or writing per-runtime registration code.

Each TODO is named and scoped — adding any of them is a discrete change, not a redesign.

## Files

| File | Purpose |
|---|---|
| `orchestrator.py` | CLI entry point + main loop. Subcommands: `run`, `once`, `dispatch`, `status`, `tail`, `transcript`. |
| `dispatch.py` | Anthropic SDK call. Builds cached system prompt, forces structured output via tool, returns a typed `Proposal`. |
| `detect.py` | Work detection. Round 1 is fully implemented; rounds 2-9 are stub functions with the design intent in their docstrings. |
| `pr.py` | JSON Patch application + branch/commit/push/PR via `gh` CLI. |
| `observability.py` | Structured logger, cost tracker, status snapshot, transcript store. All under `.orchestrator/`. |
| `state-machine.md` | Per-task and per-pass lifecycle, plus CI-gated round transition rules. |
| `config.example.yaml` | Settings: model, effort, repo path, label conventions, log paths. Copy to `config.yaml` and edit. |
| `requirements.txt` | `anthropic`, `pyyaml`, `jsonschema`, `referencing`. |

## Install + run

```bash
# 1. Install dependencies (one-time)
pip install -r orchestrator/requirements.txt

# 2. Configure
cp orchestrator/config.example.yaml orchestrator/config.yaml
$EDITOR orchestrator/config.yaml          # set repo_path, model, auth mode, label prefix, etc.

# 3. Set credentials per the auth mode you chose (see § Auth modes below)
export ANTHROPIC_API_KEY=sk-ant-...                       # api_key (default)
# OR
export ANTHROPIC_AUTH_TOKEN=sk-ant-oat01-...              # subscription_oauth
# OR (claude_code_cli) — no env var; Claude Code's own auth applies
# OR
export AUGMENT_SESSION_AUTH="$(cat ~/.augment/session.json)"  # augment_session

# 4. Make sure `gh` is installed and authenticated for your spec repo
gh --version
gh auth status

# 5. Run the loop (Ctrl-C to stop)
python orchestrator/orchestrator.py run

# Or one pass at a time (good for cron / manual nudges)
python orchestrator/orchestrator.py once
```

## Auth modes

The orchestrator supports four ways to authenticate. Pick one in `orchestrator/config.yaml` under `llm.auth.mode`:

| Mode | Provider | Auth env var | Best for |
|---|---|---|---|
| `api_key` (default) | Anthropic API | `ANTHROPIC_API_KEY` | Production. No rate-limit ceiling, full feature surface (tool_choice, prompt caching, batch API). |
| `subscription_oauth` | Anthropic API + Claude Pro/Team/Max | `ANTHROPIC_AUTH_TOKEN` (from `claude setup-token`) | Hobbyist / early iteration without separate Anthropic billing. Same SDK code path as api_key — only env var differs. |
| `claude_code_cli` | `claude` CLI subprocess (inherits whatever `claude login` set up) | (none — Claude Code's own auth) | Environments without the Python SDK; single auth context across Claude Code and the orchestrator. |
| `augment_session` | Augment Code via `auggie` CLI subprocess + session-key auth | `AUGMENT_SESSION_AUTH` (contents of `~/.augment/session.json` after `auggie login`); or unset to use auggie's on-disk session | Users with an existing Augment subscription and no Anthropic account. **Read the caveats below — most lossy of the four.** |

### Capability matrix

| | `api_key` | `subscription_oauth` | `claude_code_cli` | `augment_session` |
|---|:-:|:-:|:-:|:-:|
| Forced structured output (`tool_choice`) | ✅ | ✅ | ❌ (prompt-instructed; tolerant parser) | ❌ (prompt-instructed; tolerant parser) |
| Token telemetry per call | ✅ | ✅ | ✅ | ❌ (Augment doesn't expose this in `--print` mode) |
| Per-call USD | ✅ | ❌ (flat fee) | ❌ (flat fee) | ❌ (per-message credits, not visible) |
| Prompt caching (tunable) | ✅ | ✅ | Opaque | ❌ |
| Configurable model / effort | ✅ | ✅ | ✅ | ❌ (Augment picks its own model) |
| Adaptive thinking | ✅ | ✅ | Inherited | N/A |
| Rate-limit / quota ceiling | None (paid) | Pro ~50 req/min, Max ~500 req/min | Inherits Claude Code's auth | Subscription credits per month (Indie 25, Developer 600, Pro 1500, Max 5000+ messages) |

### When to use each

**`api_key`** is the safe default. No rate-limit surprises, works under load, and `tool_choice` enforces strict structured output. Use this for any deployment where the orchestrator runs outside your personal workstation.

**`subscription_oauth`** is the right pick if you already have a paid Claude subscription and want to avoid setting up a separate billing account. **Caveat: subscription rate limits.** Claude Pro caps at ~50 requests/minute, which the orchestrator can hit on a busy round-1 pass against a complex `scope.md` (3-5 catalog dispatches plus retries). Claude Max (~500 req/min) is the practical floor for sustained orchestrator use. If you see 429s, raise `poll.interval_seconds` to back off, or move to `api_key`.

**`claude_code_cli`** is the most portable Claude option but less feature-complete than the SDK:
- Cannot force structured output via `tool_choice` — the agent is instructed via prompt to emit JSON. Expect occasional retry if the model wraps its output in a markdown code fence (the parser is tolerant but not infallible).
- Prompt caching is opaque (Claude Code uses it internally; not tunable here).
- Subscription billing if `claude login` was set up that way; otherwise falls back to whatever auth Claude Code has.

**`augment_session`** is the **most lossy** mode and only worth it if you already pay for Augment and don't want to add Anthropic billing. Caveats:
- Same prompt-instructed JSON output as `claude_code_cli` (no `tool_choice` forcing).
- **No token telemetry.** Augment doesn't expose per-call token usage in `--print` mode (their [issue #82](https://github.com/augmentcode/auggie/issues/82)). Token columns in `cost.json` will all read 0; you cannot infer rate-limit headroom from cost data.
- **Credit-based billing** — Augment bills per User Message, not per token. The orchestrator can't surface "how many credits left" — track that in Augment's own dashboard.
- **No system prompt channel.** System content gets folded into the user prompt with a `# System instructions` header. Augment may weight it slightly differently than a true system message.
- **No model / effort knobs.** Augment selects its own model and manages its own context window. The `model:` and `effort:` fields in `config.yaml` are accepted but ignored when this backend is active.
- **5-round tool call cap** — irrelevant here since we instruct no tool use, but worth knowing if you ever extend this backend.
- ⚠️ **ToS gray zone.** Augment's documentation steers automation toward Enterprise [Service Accounts](https://docs.augmentcode.com/cli/automation/service-accounts) rather than personal session tokens. Sustained orchestrator use against a personal session token may trip anomaly detection or violate Augment's terms depending on tier — review their ToS before relying on this in production. For team / sustained use, get a Service Account.

### Setup commands per mode

```bash
# api_key
export ANTHROPIC_API_KEY=sk-ant-api03-...

# subscription_oauth
claude login                              # browser flow, one-time
claude setup-token                        # generates a long-lived OAuth token
export ANTHROPIC_AUTH_TOKEN=sk-ant-oat01-...

# claude_code_cli
claude login                              # only thing needed; auth is on-disk

# augment_session
npm install -g @augmentcode/auggie        # one-time
auggie login                              # browser flow; writes ~/.augment/session.json
# Optionally export the session for portability across machines:
export AUGMENT_SESSION_AUTH="$(cat ~/.augment/session.json)"
```

### Cost / usage reporting per mode

| Mode | What `cost.json` shows | What `orchestrator.py status` prints |
|---|---|---|
| `api_key` | Per-call USD computed from token rates in `observability.py`'s `PRICING_USD_PER_1M_TOKENS` table | `Cost total: $X.YZ (N calls)` |
| `subscription_oauth` | Tokens only (USD always 0.0 — flat monthly fee) | `Subscription billing — flat monthly fee. Tokens used: in=X out=Y (N calls)` |
| `claude_code_cli` | Tokens only (USD always 0.0 — same reasoning) | `Subscription billing — flat monthly fee. Tokens used: in=X out=Y (N calls)` |
| `augment_session` | Nothing useful — both USD and tokens are 0; only `calls` is meaningful | `Subscription billing — flat monthly fee. Tokens used: in=0 out=0 (N calls)` (track credit consumption in Augment's own dashboard) |

Tokens are tracked under both subscription modes so you can correlate against your subscription's rate-limit headroom even though the per-call USD is meaningless.

## Subcommands

```bash
# Live status snapshot
python orchestrator/orchestrator.py status

# Tail the JSON-lines log with a readable formatter
python orchestrator/orchestrator.py tail

# Replay the full LLM transcript for one task
python orchestrator/orchestrator.py transcript R1.entities.pass-0

# Manually trigger a single dispatch (debug)
python orchestrator/orchestrator.py dispatch \
    --round round-1 --agent round-1-universe \
    --inputs '{"catalog_kind": "ENTITY"}' \
    --severity high
```

## Design choices

**Why Python.** Easiest to audit, fastest to write, the Anthropic SDK is mature, and the data flow is bounded enough that performance doesn't matter. The orchestrator is a glue layer, not a hot path.

**Why `gh` CLI for GitHub.** It handles auth, repo discovery, GitHub Enterprise URLs, and label/reviewer assignment without us maintaining a REST adapter. The whole `pr.py` module is ~150 lines because of it. Replace with a Gitea / GitLab adapter by writing a sibling module — `dispatch.py` doesn't care.

**Why polling, not webhooks.** Webhooks need a public HTTP endpoint, TLS termination, and replay handling on missed deliveries. Polling needs `gh pr list` every 60 seconds. For a spec repo where work moves at human-review speed, polling is enough. (`poll.interval_seconds` is configurable; reduce it during active iteration.)

**Why one task per pass.** The agent contract guarantees idempotent JSON Patches, so multi-task fan-out is mechanically safe — but two PRs touching the same target file create Git merge conflicts that need a reconciler agent. The MVP serializes; lift it once the reconciler is in place.

**Why prompt caching by default.** The agent prompt + scope.md + glossary.md are stable across most dispatches. With Opus 4.7 pricing, a single cache hit pays back the ~1.25× write premium on the second invocation. See [`shared/prompt-caching.md`](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) (consumed via the `claude-api` skill) for the prefix-match invariant we depend on.

**Why force structured output via a tool.** `tool_choice: {"type": "tool", "name": "submit_proposal"}` is the most reliable way to get strict JSON adherence to a schema across Anthropic models. The alternative (`output_config: {format: {type: "json_schema", ...}}`) works too but has more limitations on schema features (no recursive types, no `minLength`/`maxLength`).

**Why the orchestrator must NOT use an LLM for routing.** The whole point of "small, deterministic, replaceable" is that bugs in routing logic are auditable and reversible. If routing decisions are themselves LLM calls, debugging becomes impossible: you can't reproduce why the orchestrator skipped Round 5 because the LLM's reasoning is gone after the call. Keep LLMs in the artifacts; keep the orchestrator in the procedure.

## Cost expectations

A typical Round 1 invocation:
- System (cached after first call): ~3K-8K tokens depending on scope.md size
- User message: ~500-2K tokens (current catalog + task description)
- Output: ~1K-3K tokens (the proposal)

At Opus 4.7 pricing (`$5 / $25` per 1M input/output, `$0.50` per 1M cache reads), most subsequent calls land at **~$0.05 per dispatch** with cache hits. The first call of a session pays ~$0.10-0.20 for cache writes. Use `python orchestrator.py status` for the running tally.

For high-volume catalog work or rounds 6/7 (which have wider scope), expect $0.10-0.50 per dispatch. The cost tracker exposes per-round and per-agent breakdowns in `.orchestrator/cost.json`.

## Failure modes & mitigations

| Failure | Mitigation in this MVP |
|---|---|
| LLM returns non-JSON / malformed output | `tool_choice` enforces tool call shape; one-shot dispatch errors are logged + status updated, no auto-retry yet |
| Schema validation fails on patched result | Caught when `pr.py` writes the file and the pre-commit hook runs CI checks; PR fails CI, blocks merge |
| `gh` CLI missing / unauthenticated | `pr.py` raises `PRError` on first invocation with an actionable message |
| Working tree dirty | `pr.py` refuses to PR over local edits; status records the error |
| Two PRs target the same file | Git merge conflict at review time; future reconciler agent will collapse them — MVP just lets the human resolve |
| API rate limit / 5xx | Anthropic SDK auto-retries 429 + 5xx with backoff (default `max_retries=2`); persistent failures route to status |

## What lives outside this orchestrator

- **The spec.** Lives in `spec/`, owned by the agents and reviewers.
- **The CI checks.** Live in `spec/.ci/checks/`; the orchestrator does not run them — the pre-commit hook + your CI provider do.
- **The conformance pipeline.** `ghosts-in-the-code.md` describes a seven-layer downstream pipeline (types, property tests, runtime contracts, traceability, drift gate, formal proof, AI review) that lives in your implementation repo, not here.
- **Stakeholder review.** Happens in the GitHub PR UI. The orchestrator just opens PRs and reads their merge state.

"""Agent dispatch — call Claude (or Augment) with the agent prompt + sliced context.

Four auth modes (selected via config `llm.auth.mode`):
  - api_key             SDK call billed via console.anthropic.com pay-per-token
  - subscription_oauth  SDK call billed against your Claude Pro/Team/Max subscription
                        (uses ANTHROPIC_AUTH_TOKEN from `claude setup-token`)
  - claude_code_cli     Subprocess call to the `claude` CLI in headless mode.
                        Inherits Claude Code's auth. Cannot force tool_choice; relies
                        on prompt instruction for JSON output (less reliable).
  - augment_session     Subprocess call to the `auggie` CLI (Augment Code) in headless
                        mode using session-key auth (AUGMENT_SESSION_AUTH from
                        `auggie login`). Same caveats as claude_code_cli PLUS no token
                        telemetry and credit-based (not token-based) billing.

The first two share the SDK code path — only the env var the SDK reads differs.
The CLI backends share a tolerant JSON parser since neither can force tool_choice.

The agent emits a wrapper object:
    {
      "uncertainty": "low | medium | high",
      "patch":       [JSON Patch ops],
      "rationale_for_pr_body": "..."
    }

The orchestrator applies the patch, validates the result against the round's
artifact schema, and opens a PR.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from detect import Task
from observability import Observability, task_span


# ---------------------------------------------------------------------------
# Per-round wiring — which agent prompt, target file, schema, and what context
# the agent needs. Round 1 is the only one fully wired in this MVP.
# ---------------------------------------------------------------------------

@dataclass
class RoundConfig:
    agent_prompt: str            # path under agents/, e.g. "round-1-universe.md"
    target_file_template: str    # path under spec/, with {placeholders} from task.inputs
    schema_file: str             # path under spec/.ci/schemas/
    context_files: list[str]     # additional spec/ files to include in cached system prompt


ROUND_CONFIGS: dict[str, RoundConfig] = {
    "round-1": RoundConfig(
        agent_prompt="round-1-universe.md",
        target_file_template="round-1/{catalog_kind_lower}.json",
        schema_file="entity.schema.json",  # overridden per catalog_kind below
        context_files=["scope.md", "glossary.md"],
    ),
    # Rounds 2-9 + contracts: TODO — same shape, different prompt + target + schema.
}

CATALOG_KIND_TO_SCHEMA = {
    "ENTITY": "entity.schema.json",
    "VERB":   "verb.schema.json",
    "ACTOR":  "actor.schema.json",
}


# Tool the agent must call — forcing a tool with tool_choice gives us strict
# JSON output that matches the wrapper schema below.
SUBMIT_PROPOSAL_TOOL = {
    "name": "submit_proposal",
    "description": (
        "Submit your structured proposal for the assigned task. "
        "Always call this tool exactly once. Never respond with plain text."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "uncertainty": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "Your confidence in the proposal. Use 'high' to route to a human reviewer first.",
            },
            "patch": {
                "type": "array",
                "description": (
                    "JSON Patch operations to apply against the target file. "
                    "Supported ops: 'add' (with /path/to/array/- to append) and 'replace' "
                    "(with empty path '' to replace the whole document)."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "op":    {"type": "string", "enum": ["add", "replace"]},
                        "path":  {"type": "string"},
                        "value": {},
                    },
                    "required": ["op", "path", "value"],
                },
            },
            "rationale_for_pr_body": {
                "type": "string",
                "description": (
                    "Free-form summary for the PR description. Cite the source(s) you used "
                    "and any judgment calls. 1-3 short paragraphs."
                ),
            },
        },
        "required": ["uncertainty", "patch", "rationale_for_pr_body"],
        "additionalProperties": False,
    },
}


@dataclass
class Proposal:
    uncertainty: str
    patch: list[dict]
    rationale_for_pr_body: str
    raw_response: dict        # full message JSON for the transcript
    usage: dict               # token usage for cost tracking


# ---------------------------------------------------------------------------
# Backend abstraction
# ---------------------------------------------------------------------------

class Backend(ABC):
    """One LLM dispatch implementation. Subclasses pick API vs CLI."""

    billing_mode: str  # "api" | "subscription" — drives cost tracker behavior

    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def call(self, *, system_blocks: list[dict], user_message: str, model: str,
             max_tokens: int, effort: str) -> tuple[Proposal, dict]:
        """
        Returns (proposal, request_payload_for_transcript).
        Raises on unrecoverable error.
        """


def make_backend(cfg: dict) -> Backend:
    auth = cfg.get("llm", {}).get("auth", {})
    mode = auth.get("mode", "api_key")
    if mode == "api_key":
        env = auth.get("api_key_env", "ANTHROPIC_API_KEY")
        if not os.environ.get(env):
            raise RuntimeError(f"auth mode is 'api_key' but ${env} is not set.")
        # Anthropic SDK reads ANTHROPIC_API_KEY by default; if config uses a different
        # env var name, copy it across so SDK's auto-detection picks it up.
        if env != "ANTHROPIC_API_KEY":
            os.environ["ANTHROPIC_API_KEY"] = os.environ[env]
        return AnthropicSDKBackend(billing_mode="api")
    if mode == "subscription_oauth":
        env = auth.get("oauth_token_env", "ANTHROPIC_AUTH_TOKEN")
        if not os.environ.get(env):
            raise RuntimeError(
                f"auth mode is 'subscription_oauth' but ${env} is not set. "
                f"Generate one with `claude setup-token` (after `claude login`)."
            )
        if env != "ANTHROPIC_AUTH_TOKEN":
            os.environ["ANTHROPIC_AUTH_TOKEN"] = os.environ[env]
        return AnthropicSDKBackend(billing_mode="subscription")
    if mode == "claude_code_cli":
        cli_cmd = auth.get("cli_command", "claude")
        if shutil.which(cli_cmd) is None:
            raise RuntimeError(
                f"auth mode is 'claude_code_cli' but `{cli_cmd}` is not on PATH. "
                f"Install Claude Code from https://code.claude.com/ and run `claude login`."
            )
        return ClaudeCodeCLIBackend(cli_cmd=cli_cmd)
    if mode == "augment_session":
        auggie_cmd = auth.get("auggie_command", "auggie")
        if shutil.which(auggie_cmd) is None:
            raise RuntimeError(
                f"auth mode is 'augment_session' but `{auggie_cmd}` is not on PATH. "
                f"Install Augment's CLI: `npm install -g @augmentcode/auggie` and run `auggie login`."
            )
        env = auth.get("augment_session_env", "AUGMENT_SESSION_AUTH")
        if not os.environ.get(env):
            raise RuntimeError(
                f"auth mode is 'augment_session' but ${env} is not set. "
                f"After `auggie login`, export the contents of ~/.augment/session.json as ${env}, "
                f"or rely on `auggie`'s on-disk credentials by leaving the env var unset and "
                f"setting llm.auth.augment_session_env to a name that's intentionally absent — "
                f"the CLI will fall back to its on-disk session."
            )
        return AugmentSessionBackend(auggie_cmd=auggie_cmd)
    raise RuntimeError(f"unknown llm.auth.mode: {mode!r}")


# ---------------------------------------------------------------------------
# Anthropic SDK backend (covers api_key + subscription_oauth)
# ---------------------------------------------------------------------------

class AnthropicSDKBackend(Backend):
    def __init__(self, *, billing_mode: str) -> None:
        # Defer import so installs without `anthropic` can still use the CLI backend.
        import anthropic  # noqa: F401
        self._client = None
        self.billing_mode = billing_mode

    def name(self) -> str:
        return f"anthropic-sdk ({self.billing_mode})"

    def _get_client(self):
        if self._client is None:
            import anthropic
            # SDK auto-picks ANTHROPIC_AUTH_TOKEN over ANTHROPIC_API_KEY when both are set.
            self._client = anthropic.Anthropic()
        return self._client

    def call(self, *, system_blocks, user_message, model, max_tokens, effort):
        import anthropic

        request_payload = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_blocks,
            "messages": [{"role": "user", "content": user_message}],
            "tools": [SUBMIT_PROPOSAL_TOOL],
            "tool_choice": {"type": "tool", "name": "submit_proposal"},
        }
        # Adaptive thinking + effort are recommended for intelligence-sensitive
        # work. Both fields are silently ignored by models that don't support
        # them, so this is safe across model choices.
        if model.startswith(("claude-opus-4-7", "claude-opus-4-6", "claude-sonnet-4-6")):
            request_payload["thinking"] = {"type": "adaptive"}
            request_payload["output_config"] = {"effort": effort}

        try:
            response = self._get_client().messages.create(**request_payload)
        except anthropic.APIStatusError:
            raise

        usage = {
            "input_tokens":               response.usage.input_tokens,
            "output_tokens":              response.usage.output_tokens,
            "cache_read_input_tokens":    getattr(response.usage, "cache_read_input_tokens", 0) or 0,
            "cache_creation_input_tokens":getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
        }
        proposal = _extract_proposal_from_sdk_response(response, usage)
        return proposal, request_payload


def _extract_proposal_from_sdk_response(response, usage: dict) -> Proposal:
    """Pull the submit_proposal tool call out of the SDK response."""
    if response.stop_reason not in ("tool_use", "end_turn"):
        raise RuntimeError(f"unexpected stop_reason: {response.stop_reason}")
    tool_block = next((b for b in response.content if getattr(b, "type", None) == "tool_use"), None)
    if tool_block is None:
        raise RuntimeError("model did not call submit_proposal — no tool_use block in response")
    if tool_block.name != "submit_proposal":
        raise RuntimeError(f"unexpected tool name: {tool_block.name}")
    inp = tool_block.input
    return Proposal(
        uncertainty=inp.get("uncertainty", "high"),
        patch=inp.get("patch", []),
        rationale_for_pr_body=inp.get("rationale_for_pr_body", ""),
        raw_response=_serialize_sdk_response(response),
        usage=usage,
    )


def _serialize_sdk_response(response) -> dict:
    return response.model_dump() if hasattr(response, "model_dump") else json.loads(response.json())


# ---------------------------------------------------------------------------
# Claude Code CLI backend (subscription billing via `claude login`)
# ---------------------------------------------------------------------------

CLI_JSON_INSTRUCTION = (
    "\n\n## Output format (CLI mode)\n"
    "Respond with ONLY a JSON object on a single line, no markdown, no prose, no code fence. "
    "The object must match this shape exactly:\n"
    "  {\n"
    '    "uncertainty": "low" | "medium" | "high",\n'
    '    "patch": [JSON Patch operations],\n'
    '    "rationale_for_pr_body": "free-form summary"\n'
    "  }\n"
    "Do not call any tools. Do not explain. Just emit the JSON."
)


class ClaudeCodeCLIBackend(Backend):
    """
    Subprocess-based dispatch via `claude -p ... --output-format json`.

    Limitations vs the SDK backend:
      - Cannot force tool_choice — the agent is instructed via prompt to emit JSON.
        Less reliable; expect occasional retry if the model wraps output in markdown.
      - Prompt caching is opaque (Claude Code uses it internally; we can't tune it).
      - Subscription billing — token usage IS reported by the CLI and stored, but
        per-call USD is meaningless under a flat subscription.
    """

    billing_mode = "subscription"

    def __init__(self, *, cli_cmd: str = "claude") -> None:
        self.cli_cmd = cli_cmd

    def name(self) -> str:
        return f"claude-code-cli ({self.cli_cmd})"

    def call(self, *, system_blocks, user_message, model, max_tokens, effort):
        # Compose a single prompt: system blocks + user message + JSON-output instruction.
        # The CLI doesn't expose a separate "system" channel in headless mode — fold it
        # into the user prompt with a clear delimiter.
        system_text = "\n\n".join(b.get("text", "") for b in system_blocks if b.get("type") == "text")
        full_prompt = (
            f"# System instructions\n\n{system_text}\n\n"
            f"# Task\n\n{user_message}\n\n"
            f"{CLI_JSON_INSTRUCTION}"
        )

        cmd = [self.cli_cmd, "-p", full_prompt, "--output-format", "json", "--model", model]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"claude CLI timed out after 600s") from e

        if proc.returncode != 0:
            raise RuntimeError(f"claude CLI exited {proc.returncode}: {proc.stderr.strip()}")

        try:
            envelope = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"claude CLI returned non-JSON envelope: {proc.stdout[:500]}") from e

        result_text = envelope.get("result", "")
        cli_usage = envelope.get("usage", {}) or {}
        usage = {
            "input_tokens":                cli_usage.get("input_tokens", 0),
            "output_tokens":               cli_usage.get("output_tokens", 0),
            "cache_read_input_tokens":     cli_usage.get("cache_read_input_tokens", 0),
            "cache_creation_input_tokens": cli_usage.get("cache_creation_input_tokens", 0),
        }

        proposal_dict = _parse_json_from_text(result_text)
        if proposal_dict is None:
            raise RuntimeError(
                f"claude CLI did not return parseable JSON proposal. "
                f"Result text: {result_text[:500]}"
            )

        return Proposal(
            uncertainty=proposal_dict.get("uncertainty", "high"),
            patch=proposal_dict.get("patch", []),
            rationale_for_pr_body=proposal_dict.get("rationale_for_pr_body", ""),
            raw_response={"cli_envelope": envelope},
            usage=usage,
        ), {"cmd": cmd, "prompt_chars": len(full_prompt)}


# ---------------------------------------------------------------------------
# Augment Code (auggie) backend — session-key auth, no token telemetry
# ---------------------------------------------------------------------------

AUGGIE_JSON_INSTRUCTION = (
    "\n\n## Output format (Augment mode)\n"
    "You are running through the Augment `auggie` CLI which CANNOT force a tool call. "
    "Respond with ONLY a JSON object on a single line: no markdown, no prose, no code fence. "
    "The object MUST match this shape exactly:\n"
    "  {\n"
    '    "uncertainty": "low" | "medium" | "high",\n'
    '    "patch": [JSON Patch operations],\n'
    '    "rationale_for_pr_body": "free-form summary"\n'
    "  }\n"
    "Do not invoke tools. Do not explain. Do not edit files. Just emit the JSON. "
    "If you cannot complete the task, emit the JSON with patch: [] and uncertainty: \"high\" "
    "and explain why in rationale_for_pr_body."
)


class AugmentSessionBackend(Backend):
    """
    Subprocess dispatch via `auggie --print --output-format json --quiet`.

    Auth: session-key (AUGMENT_SESSION_AUTH) or auggie's on-disk session
    (~/.augment/session.json from `auggie login`). The orchestrator passes the
    env var through automatically when set.

    Limitations vs the SDK backends — read these before relying on this mode:
      - Cannot force tool_choice — agent is instructed via prompt to emit JSON.
        Same tolerant parser as ClaudeCodeCLIBackend handles markdown fences /
        leading prose, but expect occasional failures.
      - No system-prompt channel — system content is folded into the user prompt
        with a "# System instructions" header.
      - **No token telemetry** — Augment's per-call usage isn't exposed in --print
        mode (their issue #82). All token counts will be 0; rate-limit headroom
        cannot be inferred from cost.json.
      - **Credit-based billing** — Augment bills per User Message, not per token.
        Your subscription tier (Indie / Developer / Pro / Max) determines the
        message budget.
      - **5-round tool call cap** — irrelevant since we instruct no tool use, but
        worth knowing if you ever extend this backend to allow Augment's tools.
      - **ToS gray zone** — Augment steers automation toward Enterprise Service
        Accounts. Sustained orchestrator use against a personal session token
        may trip anomaly detection. For production, consider a Service Account.
    """

    billing_mode = "subscription"  # flat-fee from our POV; same row as Claude OAuth

    def __init__(self, *, auggie_cmd: str = "auggie") -> None:
        self.auggie_cmd = auggie_cmd

    def name(self) -> str:
        return f"augment-session ({self.auggie_cmd})"

    def call(self, *, system_blocks, user_message, model, max_tokens, effort):
        # `model`, `max_tokens`, and `effort` are accepted by the contract but ignored —
        # Augment selects its own model, manages its own context window, and doesn't
        # expose a thinking-effort knob.
        system_text = "\n\n".join(b.get("text", "") for b in system_blocks if b.get("type") == "text")
        full_prompt = (
            f"# System instructions\n\n{system_text}\n\n"
            f"# Task\n\n{user_message}\n\n"
            f"{AUGGIE_JSON_INSTRUCTION}"
        )

        cmd = [self.auggie_cmd, "--print", "--output-format", "json", "--quiet", full_prompt]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired as e:
            raise RuntimeError("auggie CLI timed out after 600s") from e

        if proc.returncode != 0:
            raise RuntimeError(f"auggie CLI exited {proc.returncode}: {proc.stderr.strip()}")

        # Auggie's --output-format json envelope. Shape:
        #   {"session_id": "...", "request_id": "...", "result": "...", "is_error": false, "num_turns": N}
        try:
            envelope = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"auggie returned non-JSON envelope: {proc.stdout[:500]}") from e

        if envelope.get("is_error"):
            raise RuntimeError(f"auggie reported is_error=true: {envelope.get('result', '')[:500]}")

        result_text = envelope.get("result", "")
        # Augment doesn't expose token usage in --print mode (their issue #82). Record zeros.
        usage = {
            "input_tokens": 0, "output_tokens": 0,
            "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0,
        }

        proposal_dict = _parse_json_from_text(result_text)
        if proposal_dict is None:
            raise RuntimeError(
                f"auggie did not return parseable JSON proposal. Result text: {result_text[:500]}"
            )

        return Proposal(
            uncertainty=proposal_dict.get("uncertainty", "high"),
            patch=proposal_dict.get("patch", []),
            rationale_for_pr_body=proposal_dict.get("rationale_for_pr_body", ""),
            raw_response={"auggie_envelope": envelope},
            usage=usage,
        ), {"cmd": cmd[:-1] + ["<prompt redacted>"], "prompt_chars": len(full_prompt)}


# ---------------------------------------------------------------------------
# Tolerant JSON parser — shared by ClaudeCodeCLIBackend and AugmentSessionBackend
# ---------------------------------------------------------------------------

def _parse_json_from_text(text: str) -> dict | None:
    """Tolerant JSON extractor — handles a model that wrapped its JSON in a code fence."""
    text = text.strip()
    if not text:
        return None
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip markdown code fence
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop first line (```json or ```) and last line if it's ```
        body = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            pass
    # Try to find the first { ... } block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return None


# ---------------------------------------------------------------------------
# Build the prompt (used by both backends)
# ---------------------------------------------------------------------------

def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _build_system(repo: Path, agent_prompt_path: Path, context_files: list[str]) -> list[dict]:
    """
    System prompt = agent prompt template + scope.md + glossary.md.

    Cached as a single block — it doesn't change between dispatches, so subsequent
    invocations within the cache TTL pay ~0.1x for the prefix. See
    `shared/prompt-caching.md` for the prefix-match invariant we're relying on.
    """
    parts: list[str] = []
    parts.append("# Agent prompt\n\n" + _read_text(agent_prompt_path))
    spec = repo / "spec"
    for rel in context_files:
        text = _read_text(spec / rel)
        if text:
            parts.append(f"# spec/{rel}\n\n{text}")
    full_system = "\n\n---\n\n".join(parts)
    return [{
        "type": "text",
        "text": full_system,
        "cache_control": {"type": "ephemeral"},
    }]


def _build_user_message(repo: Path, task: Task) -> str:
    """Per-task message — variable across dispatches, NOT cached."""
    spec = repo / "spec"
    cfg = ROUND_CONFIGS[task.round_name]
    target_rel = _materialize_target(cfg.target_file_template, task.inputs)
    current_content = _read_text(spec / target_rel) or "(file does not exist or is empty)"

    lines = [
        f"## Task",
        f"- round: {task.round_name}",
        f"- agent: {task.agent}",
        f"- task_id: {task.task_id}",
        f"- inputs: {json.dumps(task.inputs)}",
        f"- rationale (why this task is open): {task.rationale}",
        "",
        f"## Target file: spec/{target_rel}",
        "Current contents:",
        "```json",
        current_content.strip(),
        "```",
        "",
        "Execute the procedure in your prompt. Call the `submit_proposal` tool exactly once.",
        "Do NOT respond with plain text — only the tool call.",
    ]
    return "\n".join(lines)


def _materialize_target(template: str, inputs: dict) -> str:
    """Substitute placeholders. round-1: {catalog_kind_lower} -> entities|verbs|actors."""
    out = template
    if "{catalog_kind_lower}" in out:
        kind = inputs.get("catalog_kind", "ENTITY").upper()
        kind_lower = {"ENTITY": "entities", "VERB": "verbs", "ACTOR": "actors"}.get(kind, "entities")
        out = out.replace("{catalog_kind_lower}", kind_lower)
    return out


# ---------------------------------------------------------------------------
# Main dispatch entry point
# ---------------------------------------------------------------------------

def dispatch(
    repo: Path,
    task: Task,
    *,
    cfg: dict,
    obs: Observability,
    backend: Backend,
) -> tuple[Proposal, str]:
    """
    Call the LLM for one task. Returns (proposal, target_file_rel).

    Raises if the round is not yet wired (rounds 2-9 in this MVP) or if the
    backend returns a malformed proposal.
    """
    round_cfg = ROUND_CONFIGS.get(task.round_name)
    if round_cfg is None:
        raise NotImplementedError(
            f"dispatch for {task.round_name} is not yet implemented. "
            "See ROUND_CONFIGS in dispatch.py and detect.py for the wiring stubs."
        )

    target_rel = _materialize_target(round_cfg.target_file_template, task.inputs)
    agent_prompt_path = repo / "agents" / round_cfg.agent_prompt
    llm = cfg["llm"]
    model = llm["model"]
    effort = llm.get("effort", "high")
    max_tokens = int(llm.get("max_tokens", 16000))

    system_blocks = _build_system(repo, agent_prompt_path, round_cfg.context_files)
    user_message = _build_user_message(repo, task)

    with task_span(obs, round_name=task.round_name, agent=task.agent) as (task_id, state):
        obs.logger.info("llm_request",
                        task_id=task_id, model=model, backend=backend.name(),
                        system_chars=sum(len(b["text"]) for b in system_blocks),
                        user_chars=len(user_message))

        try:
            proposal, request_payload = backend.call(
                system_blocks=system_blocks,
                user_message=user_message,
                model=model, max_tokens=max_tokens, effort=effort,
            )
        except Exception as e:
            state["error"] = repr(e)
            obs.logger.error("llm_error", task_id=task_id, backend=backend.name(), error=repr(e))
            raise

        usd = obs.cost.record(
            model=model, round_name=task.round_name, agent_name=task.agent,
            usage=proposal.usage, billing_mode=backend.billing_mode,
        )
        obs.logger.info("llm_response",
                        task_id=task_id, backend=backend.name(),
                        input_tokens=proposal.usage["input_tokens"],
                        output_tokens=proposal.usage["output_tokens"],
                        cache_read=proposal.usage["cache_read_input_tokens"],
                        cache_write=proposal.usage["cache_creation_input_tokens"],
                        billing_mode=backend.billing_mode,
                        cost_usd=round(usd, 4) if usd else "n/a (subscription)")

        obs.transcripts.write(task_id, {
            "task": {
                "round": task.round_name, "agent": task.agent, "task_id": task.task_id,
                "inputs": task.inputs, "rationale": task.rationale,
            },
            "backend": backend.name(),
            "request": request_payload,
            "response": proposal.raw_response,
            "proposal": {
                "uncertainty": proposal.uncertainty,
                "patch": proposal.patch,
                "rationale_for_pr_body": proposal.rationale_for_pr_body,
            },
        })
        state["result"] = "succeeded"
        return proposal, target_rel

# Skills

Skills are reusable capabilities that **agents invoke during their reasoning** — function-call style. They are distinct from agents themselves: an agent is a complete LLM invocation with its own prompt and structured output that goes through PR review; a skill is a focused service the agent calls inline when it needs a specific result.

## Skills vs agents

|  | Agent | Skill |
|---|---|---|
| Granularity | One full LLM invocation per dispatch | One function-call within an LLM invocation |
| Hidden state | None (Git-only) | None |
| Output shape | Structured JSON proposal, typically PR-shaped | Function return value, consumed inline |
| Who invokes | The orchestrator | Other agents (during their own reasoning) |
| Composition | Sequential, mediated by PR review | Inline, mediated by tool/skill calls in the agent transcript |
| Audit | PR diff + agent transcript | Tool/skill-call entries in the agent transcript |

## When to make something a skill vs an agent

- **Skill** if the work is a focused service that other agents need on demand and the output is consumed inline: source resolution, ID lookup, schema validation, computation. Treating these as agents would force a rigid two-call dispatch and lose mid-task refinement.
- **Agent** if the work is a complete reasoning task whose structured output should go through PR review: proposing entities, filling state-event cells, generating adversarial scenarios, building Hoare contracts.

## Files

| File | Purpose |
|---|---|
| `fetch-evidence.md` | Resolve sources declared in `spec/scope.md § Evidence sources` (codebase, dashboards, postmortems, runbooks, ADRs, audit reports). Returns excerpts with citations. Used by every rounds 1-8 agent in brownfield/mixed mode. |

## Registering skills with agents

The orchestrator's job: when dispatching a round-N agent, ensure the agent has the right skills loaded in its skill set. For brownfield/mixed mode, every rounds 1-8 agent must have `fetch-evidence` registered. Mode-agnostic agents (round-9, contract-assembly, counterexample-interpreter, note-vs-data) do not need it today; revisit per skill as the fleet evolves.

The skill-definition file (e.g. `fetch-evidence.md`) is what the agent receives in its skill description; the orchestrator reads it and passes it to the LLM provider's skill / tool registration API.

## Where skills live at runtime

The files in this directory are **portable spec definitions** — provider-agnostic descriptions of what each skill does, when to invoke it, what its input and output look like, and what tools it requires. Where they actually need to be at runtime depends on the agent runner:

| Runtime | Conventional location | How the agent resolves the skill |
|---|---|---|
| **Claude Code** (CLI / IDE extension) | `.claude/skills/<name>.md` (project) or `~/.claude/skills/<name>.md` (user) | Native `Skill` tool resolves by name |
| **Claude Agent SDK** | Not file-based — orchestrator reads the spec and passes it as a tool definition or system-prompt section | Tool / skill registration API |
| **Anthropic API direct** | Same as Agent SDK | Same |
| **OpenAI / Azure OpenAI** | Translate spec into function-call JSON schema | `tools=[...]` request parameter |
| **LangChain / LangGraph** | Wrap as a `Tool` subclass; pass as `tools` to the agent | Standard tool-passing |
| **Custom orchestrator** | Wherever your orchestrator looks | Per your design |

For **Claude Code** specifically, the simplest path is to symlink or copy each spec into `.claude/skills/` so Claude Code's native `Skill` tool finds them by name:

```bash
mkdir -p .claude/skills
ln -sf ../../skills/fetch-evidence.md .claude/skills/
# repeat per skill as the directory grows
```

For other runtimes, the orchestrator's responsibility includes **translating these specs into the runtime's registration format**. The portable spec stays in `skills/` as the canonical source of truth; per-runtime adapters in the orchestrator generate the function-call JSON, the `tools=[...]` argument, the LangChain `Tool` subclass, etc., from the same Markdown source.

The skill spec itself is intentionally Markdown rather than JSON — humans review it, agents read it as their skill description, and orchestrators parse the structured sections (Inputs, Output, Tool requirements) for runtime registration. Same source, three audiences.

"""Work detection — query Git + spec/ filesystem to find what's open.

Each round has a `detect_round_N(repo)` function returning a list of Tasks.
The orchestrator's main loop calls all of them, prioritizes, and dispatches.

Round 1 is implemented fully — universe agent dispatch when scope.md changed
since the last `pass-N` tag, or when round-1 catalog files are empty.
Rounds 2-9 are stubbed with TODOs naming the work-detection rule.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Task:
    """One unit of work the orchestrator can dispatch to an agent."""

    round_name: str            # "round-1", "round-2", ...
    agent: str                 # agent prompt filename (without .md)
    task_id: str               # stable, deterministic — used for dedup across detect cycles
    severity: str = "medium"   # low | medium | high | critical
    inputs: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""        # one-line "why this task is open"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return None


def _git(repo: Path, *args: str) -> str:
    """Run git in the repo and return stdout (stripped). Empty string on failure."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=30,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def _last_pass_tag(repo: Path) -> str | None:
    """Return the highest pass-N tag, or None if no pass tag exists."""
    tags_raw = _git(repo, "tag", "--list", "pass-*")
    if not tags_raw:
        return None
    pass_tags = []
    for tag in tags_raw.splitlines():
        m = re.match(r"^pass-(\d+)$", tag.strip())
        if m:
            pass_tags.append((int(m.group(1)), tag.strip()))
    if not pass_tags:
        return None
    return max(pass_tags)[1]


def _scope_mode(repo: Path) -> str | None:
    """Parse `## Mode` section from scope.md. Returns 'greenfield', 'brownfield', 'mixed', or None."""
    scope = repo / "spec" / "scope.md"
    if not scope.exists():
        return None
    text = scope.read_text(encoding="utf-8")
    # Look for the first non-blockquote, non-empty line after "## Mode"
    lines = text.splitlines()
    in_mode_section = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## Mode"):
            in_mode_section = True
            continue
        if in_mode_section:
            if stripped.startswith("##"):
                return None  # next section without finding mode
            if not stripped or stripped.startswith(">") or stripped.startswith("<!--"):
                continue
            # Mode value — strip backticks, parens, quotes
            value = stripped.strip("`").strip().lower().split()[0] if stripped else ""
            if value in {"greenfield", "brownfield", "mixed"}:
                return value
    return None


# ---------------------------------------------------------------------------
# Round 1 — universe (entities, verbs, actors)
# ---------------------------------------------------------------------------

def detect_round_1(repo: Path) -> list[Task]:
    """Open work for Round 1.

    Open conditions (any of):
      a) round-1/{entities,verbs,actors}.json is empty AND scope.md has been edited
         (i.e., we have inputs but no outputs yet).
      b) scope.md has been modified since the last pass-N tag (re-run round 1 against
         the updated scope).
    """
    tasks: list[Task] = []
    spec = repo / "spec"
    if not (spec / "scope.md").exists():
        return tasks

    last_pass = _last_pass_tag(repo)
    scope_changed = False
    if last_pass:
        diff = _git(repo, "diff", "--name-only", last_pass, "HEAD", "--", "spec/scope.md")
        scope_changed = bool(diff.strip())
    else:
        scope_changed = True  # never tagged → still in pass 0

    catalogs = {
        "entities": _read_json(spec / "round-1" / "entities.json") or {},
        "verbs":    _read_json(spec / "round-1" / "verbs.json") or {},
        "actors":   _read_json(spec / "round-1" / "actors.json") or {},
    }

    for kind, data in catalogs.items():
        items = data.get(kind, [])
        is_empty = len(items) == 0
        if is_empty or scope_changed:
            tasks.append(Task(
                round_name="round-1",
                agent="round-1-universe",
                # Deterministic ID so the same task is not dispatched twice in one pass
                task_id=f"R1.{kind}.{last_pass or 'pass-0'}",
                severity="high" if is_empty else "medium",
                inputs={"catalog_kind": kind.upper().rstrip("S") if kind != "actors" else "ACTOR"},
                rationale=("catalog empty" if is_empty else "scope.md changed since last pass"),
            ))
    return tasks


# ---------------------------------------------------------------------------
# Rounds 2-9 — stubbed
# ---------------------------------------------------------------------------

def detect_round_2(repo: Path) -> list[Task]:
    """Open work for Round 2.

    TODO: For each `spec/round-2/<entity>-state-machine.json`:
      - Compute (state, event) cells declared but missing from `cells[]`.
      - Emit one Task per missing cell, agent="round-2-state-event",
        inputs={"entity": ..., "state": ..., "event": ...}.

    Stub returns nothing for the MVP — Round 2 dispatch is a small extension once
    Round 1 stabilizes and the entity catalog has stateful entries.
    """
    return []


def detect_round_3(repo: Path) -> list[Task]:
    """Open work for Round 3.

    TODO: For each verb parameter in `spec/round-1/verbs.json` and each entity
    attribute that's a value type, check if `spec/round-3/<dim>-partition.json`
    exists. Emit one Task per missing dimension.
    """
    return []


def detect_round_4(repo: Path) -> list[Task]:
    """Open work for Round 4.

    TODO: Enumerate entity pairs from round-1/entities.json. For each pair not
    covered by `interactions.json` (either as a specified interaction or as
    `family: independent`), emit one Task.
    """
    return []


def detect_round_5(repo: Path) -> list[Task]:
    """Open work for Round 5.

    TODO: Two work sources:
      1. `spec/round-5/traces/*.txt` — Quint counterexamples awaiting interpretation.
         Emit Tasks for the round-5-counterexample-interpreter agent.
      2. New entities in round-1 not yet represented in invariants.qnt — emit Tasks
         for the round-5-invariant agent (intelligence-sensitive; Quint integration
         requires the `quint` CLI on PATH).
    """
    return []


def detect_round_6(repo: Path) -> list[Task]:
    """Open work for Round 6.

    TODO: Walk the standard quality dimension checklist (security, performance,
    scalability, ...). For each dimension not represented in `quality.json`,
    emit one Task for the round-6-quality agent.
    """
    return []


def detect_round_7(repo: Path) -> list[Task]:
    """Open work for Round 7.

    TODO: For each STRIDE category not represented in `adversarial.json`
    (and for new entities in round-1 not yet covered), emit Tasks for the
    round-7-adversarial agent.
    """
    return []


def detect_round_8(repo: Path) -> list[Task]:
    """Open work for Round 8.

    TODO: For each assumption category not exhaustively probed
    (environmental, data, human, organizational, technological), emit Tasks
    for the round-8-assumption agent.
    """
    return []


def detect_round_9(repo: Path) -> list[Task]:
    """Open work for Round 9 (cross-pass delta).

    TODO: Compare HEAD to the last pass-N tag. For each round (1-8), count
    new IDs added since the tag. If non-zero, emit a Task for the
    round-9-cross-pass-delta agent with that round as input.
    """
    return []


def detect_contracts(repo: Path) -> list[Task]:
    """Open work for contract assembly.

    TODO: For each verb in `spec/round-1/verbs.json` without a corresponding
    `spec/contracts/<verb-id>.json`, emit one Task for the contract-assembly agent.
    """
    return []


# ---------------------------------------------------------------------------
# Top-level — what every loop iteration calls
# ---------------------------------------------------------------------------

ALL_DETECTORS = [
    ("round-1",   detect_round_1),
    ("round-2",   detect_round_2),
    ("round-3",   detect_round_3),
    ("round-4",   detect_round_4),
    ("round-5",   detect_round_5),
    ("round-6",   detect_round_6),
    ("round-7",   detect_round_7),
    ("round-8",   detect_round_8),
    ("round-9",   detect_round_9),
    ("contracts", detect_contracts),
]


def detect_all(repo: Path) -> list[Task]:
    out: list[Task] = []
    for _, fn in ALL_DETECTORS:
        out.extend(fn(repo))
    return out


SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def prioritize(tasks: list[Task]) -> list[Task]:
    """Sort tasks by (severity, round-number) so critical / earlier rounds run first."""
    def key(t: Task) -> tuple[int, int]:
        sev = SEVERITY_ORDER.get(t.severity, 99)
        m = re.match(r"^round-(\d+)$", t.round_name)
        round_num = int(m.group(1)) if m else 99  # contracts / others go last
        return (sev, round_num)
    return sorted(tasks, key=key)

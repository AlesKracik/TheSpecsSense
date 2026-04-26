#!/usr/bin/env python3
"""
Regenerate the human-readable markdown views in spec/.views/rendered/
from the structured JSON sources. Run on every commit (via pre-commit hook
or CI), never edited by hand.

Output files:
  spec/.views/rendered/round-1.md
  spec/.views/rendered/round-2.md
  spec/.views/rendered/round-3.md
  spec/.views/rendered/round-4.md
  spec/.views/rendered/round-5.md
  spec/.views/rendered/round-6.md
  spec/.views/rendered/round-7.md
  spec/.views/rendered/round-8.md
  spec/.views/rendered/contracts.md
  spec/.views/rendered/master-status.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SPEC = Path(__file__).resolve().parent.parent / "spec"
RENDERED = SPEC / ".views" / "rendered"


def read_json(p: Path) -> dict | None:
    if not p.exists():
        return None
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def status_bar(filled: int, total: int, width: int = 8) -> str:
    if total == 0:
        return "░" * width
    on = round(width * filled / total)
    return "█" * on + "░" * (width - on)


# --- per-round renderers ---------------------------------------------------

def render_round_1() -> str:
    out = ["# Round 1 — Universe\n"]
    for kind, fname in [("Entities", "entities.json"), ("Verbs", "verbs.json"), ("Actors", "actors.json")]:
        data = read_json(SPEC / "round-1" / fname) or {}
        items = data.get(kind.lower(), [])
        out.append(f"\n## {kind} ({len(items)})\n")
        for item in items:
            out.append(f"- **{item.get('id')}** — {item.get('_note', '_(no note)_')}")
    return "\n".join(out) + "\n"


def render_round_2() -> str:
    out = ["# Round 2 — State-event matrices\n"]
    for path in sorted((SPEC / "round-2").glob("*-state-machine.json")):
        data = read_json(path) or {}
        entity = data.get("entity", "?")
        states = data.get("states", [])
        events = data.get("events", [])
        cells = {(c.get("state"), c.get("event")): c for c in data.get("cells", [])}
        total = len(states) * len(events)
        filled = len(cells)
        out.append(f"\n## {entity}  [{status_bar(filled, total)}] {filled}/{total}\n")
        out.append("| state \\ event | " + " | ".join(events) + " |")
        out.append("|" + "---|" * (len(events) + 1))
        for s in states:
            row = [s]
            for e in events:
                c = cells.get((s, e))
                if c is None:
                    row.append("⚠️ open")
                elif c.get("kind") == "transition":
                    row.append(f"→ {c.get('next_state')}")
                elif c.get("kind") == "noop":
                    row.append("noop")
                else:
                    row.append(f"impossible ({c.get('justification_ref', '?')})")
            out.append("| " + " | ".join(row) + " |")
    return "\n".join(out) + "\n"


def render_round_3() -> str:
    out = ["# Round 3 — Input partitions\n"]
    for path in sorted((SPEC / "round-3").glob("*-partition.json")):
        data = read_json(path) or {}
        out.append(f"\n## {data.get('dimension', '?')}\n")
        out.append("| class | range | behavior | _note |")
        out.append("|---|---|---|---|")
        for cls in data.get("classes", []):
            out.append(
                f"| {cls.get('id')} | `{cls.get('range')}` | {cls.get('behavior')} | {cls.get('_note', '')} |"
            )
    return "\n".join(out) + "\n"


def render_round_4() -> str:
    data = read_json(SPEC / "round-4" / "interactions.json") or {}
    out = ["# Round 4 — Cross-product interactions\n"]
    for ix in data.get("interactions", []):
        out.append(f"\n## {ix.get('id')} — {ix.get('family')}")
        out.append(f"- **A × B:** {ix.get('entity_a')} × {ix.get('entity_b')}")
        out.append(f"- **Situation:** {ix.get('situation', '')}")
        out.append(f"- **Behavior:** {ix.get('specified_behavior', '')}")
        out.append(f"- **_note:** {ix.get('_note', '')}")
    return "\n".join(out) + "\n"


def render_round_5() -> str:
    data = read_json(SPEC / "round-5" / "invariant-rationale.json") or {}
    out = ["# Round 5 — Formal invariants\n"]
    for inv in data.get("invariants", []):
        out.append(f"\n## {inv.get('id')} ({inv.get('kind')})")
        out.append(f"- **Quint name:** `{inv.get('qnt_name')}`")
        out.append(f"- **Could be violated by:** {', '.join(inv.get('actions_that_could_violate', []))}")
        out.append(f"- **_note:** {inv.get('_note', '')}")
    traces_dir = SPEC / "round-5" / "traces"
    traces = list(traces_dir.glob("*.txt")) if traces_dir.exists() else []
    if traces:
        out.append(f"\n## Open counterexamples ({len(traces)})\n")
        for t in sorted(traces):
            out.append(f"- `{t.name}`")
    return "\n".join(out) + "\n"


def render_round_6() -> str:
    data = read_json(SPEC / "round-6" / "quality.json") or {}
    out = ["# Round 6 — Quality attributes\n", "| ID | quality | sub-attribute | applicable | _note |", "|---|---|---|---|---|"]
    for q in data.get("qualities", []):
        out.append(
            f"| {q.get('id')} | {q.get('quality')} | {q.get('sub_attribute')} | "
            f"{'✅' if q.get('applicable') else '❌'} | {q.get('_note', '')} |"
        )
    return "\n".join(out) + "\n"


def render_round_7() -> str:
    data = read_json(SPEC / "round-7" / "adversarial.json") or {}
    out = ["# Round 7 — Adversarial scenarios\n"]
    scenarios = sorted(data.get("scenarios", []), key=lambda s: (s.get("severity", ""), s.get("likelihood", "")), reverse=True)
    for s in scenarios:
        out.append(f"\n## {s.get('id')} — {s.get('severity', '?').upper()} / {s.get('likelihood', '?')}")
        out.append(f"- **Category:** {s.get('stride_category')}")
        out.append(f"- **Scenario:** {s.get('scenario', '')}")
        out.append(f"- **Mitigation:** {s.get('mitigation_requirement', '')} ({s.get('mitigation_status', '?')})")
        out.append(f"- **_note:** {s.get('_note', '')}")
    return "\n".join(out) + "\n"


def render_round_8() -> str:
    data = read_json(SPEC / "round-8" / "assumptions.json") or {}
    out = ["# Round 8 — Assumption registry\n", "| ID | category | severity | mitigation | referenced by | _note |", "|---|---|---|---|---|---|"]
    for a in data.get("assumptions", []):
        out.append(
            f"| {a.get('id')} | {a.get('category')} | {a.get('severity', '?').upper()} | "
            f"{a.get('mitigation')} | {', '.join(a.get('referenced_by', []))} | {a.get('_note', '')} |"
        )
    return "\n".join(out) + "\n"


def render_contracts() -> str:
    out = ["# Hoare contracts\n"]
    for path in sorted((SPEC / "contracts").glob("*.json")):
        data = read_json(path) or {}
        out.append(f"\n## {data.get('operation', path.stem)}")
        out.append(f"- **_note:** {data.get('_note', '')}")
        out.append(f"- **Requires:** {len(data.get('requires', []))} clause(s)")
        out.append(f"- **Ensures:** {len(data.get('ensures', []))} clause(s)")
        out.append(f"- **Preserves:** {', '.join(p.get('invariant', '') for p in data.get('preserves', []))}")
    return "\n".join(out) + "\n"


def render_master_status() -> str:
    """One-page executive view across all rounds."""
    out = ["# Specification status\n"]
    counts = []
    for n, name, path, key in [
        (1, "Universe (entities)",     SPEC / "round-1" / "entities.json",      "entities"),
        (1, "Universe (verbs)",        SPEC / "round-1" / "verbs.json",         "verbs"),
        (1, "Universe (actors)",       SPEC / "round-1" / "actors.json",        "actors"),
        (4, "Cross-product",           SPEC / "round-4" / "interactions.json",  "interactions"),
        (5, "Invariants",              SPEC / "round-5" / "invariant-rationale.json", "invariants"),
        (6, "Quality attributes",      SPEC / "round-6" / "quality.json",       "qualities"),
        (7, "Adversarial scenarios",   SPEC / "round-7" / "adversarial.json",   "scenarios"),
        (8, "Assumptions",             SPEC / "round-8" / "assumptions.json",   "assumptions"),
    ]:
        data = read_json(path) or {}
        counts.append((n, name, len(data.get(key, []))))
    out.append("| Round | Catalog | Count |")
    out.append("|---|---|---|")
    for n, name, c in counts:
        out.append(f"| R{n} | {name} | {c} |")
    return "\n".join(out) + "\n"


def main() -> int:
    RENDERED.mkdir(parents=True, exist_ok=True)
    renderers = {
        "round-1.md":         render_round_1,
        "round-2.md":         render_round_2,
        "round-3.md":         render_round_3,
        "round-4.md":         render_round_4,
        "round-5.md":         render_round_5,
        "round-6.md":         render_round_6,
        "round-7.md":         render_round_7,
        "round-8.md":         render_round_8,
        "contracts.md":       render_contracts,
        "master-status.md":   render_master_status,
    }
    for fname, fn in renderers.items():
        (RENDERED / fname).write_text(fn(), encoding="utf-8")
    print(f"Wrote {len(renderers)} rendered view(s) to {RENDERED}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

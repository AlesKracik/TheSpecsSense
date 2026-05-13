#!/usr/bin/env python3
"""
Cross-file consistency check between each Round 2 Quint module and its notes
companion.

For every `round-2/<entity>.qnt` we expect a sibling `round-2/<entity>-notes.json`
(and vice versa). Once both exist, the declared vocabulary must agree:

  * Every state literal in the notes file's `states` array must appear as a
    variant in the module's `type State = ...` declaration.
  * Every event in the notes file's `events` array must have a matching
    `action handle_<event>` (or `action <event>`) in the module.
  * Every state and event the module declares must also appear in the notes.

This is a regex check, not a real Quint parser, so it is best-effort: it
catches the common drift modes (renamed state, missing event) but cannot
verify per-cell branch semantics. That work is deferred to `quint typecheck`
and human review.

The check is a no-op until at least one `<entity>.qnt` exists — the split is
opt-in per entity during migration.

Exit code: 0 if every (.qnt, -notes.json) pair agrees on states/events, 1
otherwise.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SPEC_ROOT = Path(__file__).resolve().parent.parent.parent
ROUND2 = SPEC_ROOT / "round-2"

STATE_LITERAL_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
EVENT_LITERAL_RE = re.compile(r"^[a-z][a-z0-9_]*$")

# `type State = FOO | BAR | BAZ` (possibly spanning multiple lines).
TYPE_STATE_RE = re.compile(
    r"\btype\s+State\s*=\s*([A-Z0-9_|\s]+)",
    re.MULTILINE,
)

# `action handle_<event_name> = ...` or `action <event_name> = ...`.
# We accept both forms so renaming conventions can evolve.
ACTION_RE = re.compile(
    r"^\s*action\s+(handle_)?([a-z][a-z0-9_]*)\s*=",
    re.MULTILINE,
)

# Actions that aren't event handlers — never count these as events.
NON_EVENT_ACTIONS = {"init", "step"}


def parse_states_from_qnt(text: str) -> set[str]:
    states: set[str] = set()
    for m in TYPE_STATE_RE.finditer(text):
        body = m.group(1)
        for tok in re.split(r"[|\s]+", body):
            tok = tok.strip()
            if tok and STATE_LITERAL_RE.match(tok):
                states.add(tok)
    return states


def parse_events_from_qnt(text: str) -> set[str]:
    events: set[str] = set()
    for m in ACTION_RE.finditer(text):
        name = m.group(2)
        if name in NON_EVENT_ACTIONS:
            continue
        if EVENT_LITERAL_RE.match(name):
            events.add(name)
    return events


def main() -> int:
    if not ROUND2.exists():
        print("INFO — round-2/ does not exist; skipping.")
        return 0

    qnt_files = sorted(ROUND2.glob("*.qnt"))
    notes_files = sorted(ROUND2.glob("*-notes.json"))

    if not qnt_files and not notes_files:
        print("INFO — round-2/ has no .qnt or -notes.json files yet; skipping.")
        return 0

    if not qnt_files:
        print("INFO — round-2/ has no .qnt modules yet (migration not started); skipping consistency check.")
        return 0

    # Map base entity slug -> paths.
    qnt_by_slug: dict[str, Path] = {p.stem: p for p in qnt_files}
    notes_by_slug: dict[str, Path] = {p.name[: -len("-notes.json")]: p for p in notes_files}

    failures: list[str] = []
    checked_pairs = 0

    all_slugs = sorted(set(qnt_by_slug) | set(notes_by_slug))
    for slug in all_slugs:
        qnt_path = qnt_by_slug.get(slug)
        notes_path = notes_by_slug.get(slug)

        if qnt_path and not notes_path:
            failures.append(f"{qnt_path}: no matching {slug}-notes.json")
            continue
        if notes_path and not qnt_path:
            # Legacy-only matrix; allowed during migration.
            continue

        assert qnt_path is not None and notes_path is not None

        qnt_text = qnt_path.read_text(encoding="utf-8")
        try:
            notes = json.loads(notes_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            failures.append(f"{notes_path}: invalid JSON: {e}")
            continue

        qnt_states = parse_states_from_qnt(qnt_text)
        qnt_events = parse_events_from_qnt(qnt_text)
        notes_states = set(notes.get("states", []))
        notes_events = set(notes.get("events", []))

        missing_in_qnt_states = notes_states - qnt_states
        missing_in_notes_states = qnt_states - notes_states
        missing_in_qnt_events = notes_events - qnt_events
        missing_in_notes_events = qnt_events - notes_events

        if missing_in_qnt_states:
            failures.append(
                f"{notes_path} declares states absent from {qnt_path.name}: "
                + ", ".join(sorted(missing_in_qnt_states))
            )
        if missing_in_notes_states:
            failures.append(
                f"{qnt_path} declares states absent from {notes_path.name}: "
                + ", ".join(sorted(missing_in_notes_states))
            )
        if missing_in_qnt_events:
            failures.append(
                f"{notes_path} declares events absent from {qnt_path.name} (no `action handle_<event>`): "
                + ", ".join(sorted(missing_in_qnt_events))
            )
        if missing_in_notes_events:
            failures.append(
                f"{qnt_path} declares event handlers absent from {notes_path.name}: "
                + ", ".join(sorted(missing_in_notes_events))
            )
        checked_pairs += 1

    if failures:
        print(f"FAIL — {len(failures)} round-2 consistency issue(s):", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        return 1

    print(f"OK — {checked_pairs} round-2 (.qnt, -notes.json) pair(s) agree on states/events.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Verify the `_note` convention across every record that should have one.

Mechanical checks (this script):
- Every record at meaningful granularity has a `_note` field.
- Every `_note` is between 40 and 300 characters.

Semantic checks (NOT this script — they require an LLM):
- The note matches the data: no added facts, no omitted material facts.
- The note covers the whole record.
- Plain language; no field-name jargon.
Run those via the dedicated `note-vs-data` agent on changed records during PR review.

Exit code: 0 if all OK, 1 otherwise.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable
from pathlib import Path

SPEC_ROOT = Path(__file__).resolve().parent.parent.parent
MIN_LEN = 40
MAX_LEN = 300

# For each schema, the JSON paths whose elements MUST carry a `_note`.
NOTE_REQUIRED_PATHS: dict[str, list[tuple[str, ...]]] = {
    "entity.schema.json":             [("entities", "[]")],
    "verb.schema.json":               [("verbs", "[]")],
    "actor.schema.json":              [("actors", "[]")],
    "state-machine.schema.json":      [("cells", "[]")],
    "partition.schema.json":          [("classes", "[]")],
    "interaction.schema.json":        [("interactions", "[]")],
    "invariant-rationale.schema.json":[("invariants", "[]")],
    "quality.schema.json":            [("qualities", "[]")],
    "adversarial.schema.json":        [("scenarios", "[]")],
    "assumption.schema.json":         [("assumptions", "[]")],
    "contract.schema.json":           [(),],
    "test-metadata.schema.json":      [(),],
    "diff-context.schema.json":       [(),],
}


def walk(data, path: tuple[str, ...]) -> Iterable[tuple[tuple[str, ...], object]]:
    if not path:
        yield (), data
        return
    head, *rest = path
    if head == "[]":
        if not isinstance(data, list):
            return
        for i, item in enumerate(data):
            for sub_path, val in walk(item, tuple(rest)):
                yield (str(i),) + sub_path, val
    else:
        if not isinstance(data, dict) or head not in data:
            return
        for sub_path, val in walk(data[head], tuple(rest)):
            yield (head,) + sub_path, val


def iter_artifact_files() -> list[Path]:
    files = []
    for p in SPEC_ROOT.rglob("*.json"):
        rel = p.relative_to(SPEC_ROOT)
        parts = rel.parts
        if p.name.startswith("_"):
            continue
        if any(part.startswith(".") for part in parts[:-1]) and parts[0] != ".diff-context":
            continue
        if ".views" in parts:
            continue
        files.append(p)
    return files


def main() -> int:
    failures: list[str] = []
    checked = 0

    for path in iter_artifact_files():
        with path.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                failures.append(f"{path}: invalid JSON: {e}")
                continue

        schema_ref = data.get("$schema")
        if not schema_ref:
            continue
        sname = Path(schema_ref).name
        for record_path in NOTE_REQUIRED_PATHS.get(sname, []):
            for loc, record in walk(data, record_path):
                if not isinstance(record, dict):
                    continue
                checked += 1
                note = record.get("_note")
                loc_str = "/".join(loc) or "<root>"
                if note is None:
                    failures.append(f"{path}: {loc_str}: missing _note")
                    continue
                if not isinstance(note, str):
                    failures.append(f"{path}: {loc_str}: _note must be a string")
                    continue
                length = len(note)
                if length < MIN_LEN:
                    failures.append(f"{path}: {loc_str}: _note too short ({length} < {MIN_LEN})")
                elif length > MAX_LEN:
                    failures.append(f"{path}: {loc_str}: _note too long ({length} > {MAX_LEN})")

    if failures:
        print(f"FAIL — {len(failures)} _note violation(s) across {checked} record(s):", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        return 1

    print(f"OK — {checked} record(s) carry a well-sized _note.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

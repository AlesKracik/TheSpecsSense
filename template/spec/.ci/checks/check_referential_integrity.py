#!/usr/bin/env python3
"""
Check referential integrity across all spec artifacts.

Builds a global ID set from every JSON file under spec/, then walks every
JSON value that looks like an ID reference (matches the ID pattern AND
appears in a known reference field) and asserts the target exists.

Reference fields per schema:
  entity:               (none — entities are sources)
  verb:                 subject, object
  actor:                permitted_verbs
  state-machine:        entity, justification_ref
  partition:            (none — dimensions are sources)
  interaction:          entity_a, entity_b, entity_c
  invariant-rationale:  actions_that_could_violate
  quality:              (none)
  adversarial:          (none)
  assumption:           referenced_by
  contract:             operation, requires[].traces_to, ensures[].traces_to, preserves[].invariant
  test-metadata:        derives_from
  diff-context:         depends_on_this.requirements, depends_on_this.tests_*

Exit code: 0 if all references resolve, 1 otherwise.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path

SPEC_ROOT = Path(__file__).resolve().parent.parent.parent
ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$")

# Maps schema $id (filename) -> list of (path-tuples-into-record) that hold ID references.
# Each path-tuple uses "[]" to mean "for every list element".
REFERENCE_PATHS: dict[str, list[tuple[str, ...]]] = {
    "verb.schema.json":               [("verbs", "[]", "subject"), ("verbs", "[]", "object")],
    "actor.schema.json":              [("actors", "[]", "permitted_verbs", "[]")],
    "state-machine.schema.json":      [("entity",), ("cells", "[]", "justification_ref")],
    "interaction.schema.json":        [("interactions", "[]", "entity_a"),
                                       ("interactions", "[]", "entity_b"),
                                       ("interactions", "[]", "entity_c")],
    "invariant-rationale.schema.json":[("invariants", "[]", "actions_that_could_violate", "[]")],
    "assumption.schema.json":         [("assumptions", "[]", "referenced_by", "[]")],
    "contract.schema.json":           [("operation",),
                                       ("requires", "[]", "traces_to", "[]"),
                                       ("ensures", "[]", "traces_to", "[]"),
                                       ("preserves", "[]", "invariant")],
    "test-metadata.schema.json":      [("derives_from", "[]")],
    "diff-context.schema.json":       [("depends_on_this", "requirements", "[]"),
                                       ("depends_on_this", "tests_obsoleted", "[]"),
                                       ("depends_on_this", "tests_to_regenerate", "[]")],
}

# Top-level ID-bearing fields per schema. Used to build the global ID set.
ID_HOLDERS: dict[str, list[tuple[str, ...]]] = {
    "entity.schema.json":             [("entities", "[]", "id")],
    "verb.schema.json":               [("verbs", "[]", "id")],
    "actor.schema.json":              [("actors", "[]", "id")],
    "state-machine.schema.json":      [("cells", "[]", "id")],
    "partition.schema.json":          [("dimension",), ("classes", "[]", "id")],
    "interaction.schema.json":        [("interactions", "[]", "id")],
    "invariant-rationale.schema.json":[("invariants", "[]", "id")],
    "quality.schema.json":            [("qualities", "[]", "id")],
    "adversarial.schema.json":        [("scenarios", "[]", "id")],
    "assumption.schema.json":         [("assumptions", "[]", "id")],
    "contract.schema.json":           [("id",), ("operation",)],
    "test-metadata.schema.json":      [("id",)],
    "diff-context.schema.json":       [("change_id",)],
}


def walk(data, path: tuple[str, ...]) -> Iterable[tuple[tuple[str, ...], object]]:
    """Walk into `data` following `path`. '[]' means iterate over a list."""
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


def schema_name_of(data: dict) -> str | None:
    s = data.get("$schema")
    return Path(s).name if s else None


def collect_ids() -> tuple[set[str], dict[str, Path]]:
    ids: set[str] = set()
    source: dict[str, Path] = {}
    for path in iter_artifact_files():
        with path.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue
        sname = schema_name_of(data)
        if not sname or sname not in ID_HOLDERS:
            continue
        for holder in ID_HOLDERS[sname]:
            for _loc, val in walk(data, holder):
                if isinstance(val, str) and ID_PATTERN.match(val):
                    if val in ids and source[val] != path:
                        # Allow shared IDs across files only if the value is identical.
                        # (Cross-file ID collision is its own bug class — flag here.)
                        print(f"WARN duplicate ID '{val}' in {path} (also in {source[val]})", file=sys.stderr)
                    ids.add(val)
                    source.setdefault(val, path)
    return ids, source


def collect_references() -> list[tuple[Path, str, str]]:
    """Return [(file, json_location, referenced_id)]."""
    refs: list[tuple[Path, str, str]] = []
    for path in iter_artifact_files():
        with path.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue
        sname = schema_name_of(data)
        if not sname or sname not in REFERENCE_PATHS:
            continue
        for ref_path in REFERENCE_PATHS[sname]:
            for loc, val in walk(data, ref_path):
                if isinstance(val, str) and ID_PATTERN.match(val):
                    refs.append((path, "/".join(loc), val))
    return refs


def main() -> int:
    ids, _source = collect_ids()
    refs = collect_references()
    failures: list[str] = []
    for path, loc, ref in refs:
        if ref not in ids:
            failures.append(f"{path}: {loc}: unresolved reference '{ref}'")

    if failures:
        print(f"FAIL — {len(failures)} unresolved reference(s):", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        return 1

    print(f"OK — {len(refs)} reference(s) across {len(ids)} known ID(s) all resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

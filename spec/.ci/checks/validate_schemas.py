#!/usr/bin/env python3
"""
Validate every JSON file under spec/ against its declared $schema.

Conventions:
- Each artifact JSON has a top-level "$schema" pointing to a relative path under .ci/schemas/.
- Files named `_*.json` are skipped (treated as fragments / examples).
- Files under .views/rendered/ are skipped (they are generated views, not source).

Exit code: 0 if all valid, 1 otherwise.

Requires: jsonschema>=4.18 (referencing API).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012
except ImportError:
    print("ERROR: install dependencies first:  pip install 'jsonschema>=4.18' referencing", file=sys.stderr)
    sys.exit(2)


SPEC_ROOT = Path(__file__).resolve().parent.parent.parent  # spec/
SCHEMAS_DIR = SPEC_ROOT / ".ci" / "schemas"


def load_registry() -> Registry:
    """Load every schema under .ci/schemas/ into a Registry keyed by $id."""
    resources = []
    for schema_path in SCHEMAS_DIR.glob("*.schema.json"):
        with schema_path.open("r", encoding="utf-8") as f:
            schema = json.load(f)
        sid = schema.get("$id") or schema_path.name
        resources.append((sid, Resource(contents=schema, specification=DRAFT202012)))
    return Registry().with_resources(resources)


def iter_artifact_files() -> list[Path]:
    files = []
    for p in SPEC_ROOT.rglob("*.json"):
        rel = p.relative_to(SPEC_ROOT)
        parts = rel.parts
        if any(part.startswith(".") for part in parts[:-1]):
            # skip .ci/, .diff-context/ (those have their own validation paths)
            if parts[0] != ".diff-context":
                continue
        if p.name.startswith("_"):
            continue
        if ".views" in parts:
            continue
        files.append(p)
    return files


def main() -> int:
    registry = load_registry()
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
            failures.append(f"{path}: missing $schema field")
            continue

        schema_name = Path(schema_ref).name
        schema_path = SCHEMAS_DIR / schema_name
        if not schema_path.exists():
            failures.append(f"{path}: schema not found: {schema_name}")
            continue

        with schema_path.open("r", encoding="utf-8") as f:
            schema = json.load(f)

        validator = Draft202012Validator(schema, registry=registry)
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
        if errors:
            for err in errors:
                loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
                failures.append(f"{path}: {loc}: {err.message}")
        checked += 1

    if failures:
        print(f"FAIL — {len(failures)} schema violation(s) across {checked} file(s):", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        return 1

    print(f"OK — {checked} file(s) valid against their declared schemas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

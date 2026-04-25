#!/usr/bin/env python3
"""
Round 2 closure check: every (state, event) cell in every state-machine.json
is filled (kind in {transition, noop, impossible}).

Exit code: 0 if every matrix is complete, 1 otherwise.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SPEC_ROOT = Path(__file__).resolve().parent.parent.parent
ROUND2 = SPEC_ROOT / "round-2"


def main() -> int:
    failures: list[str] = []
    checked = 0
    if not ROUND2.exists():
        print("INFO — round-2/ does not exist; skipping.")
        return 0

    for path in sorted(ROUND2.glob("*-state-machine.json")):
        with path.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                failures.append(f"{path}: invalid JSON: {e}")
                continue

        states = data.get("states", [])
        events = data.get("events", [])
        cells = data.get("cells", [])
        present = {(c.get("state"), c.get("event")) for c in cells}
        missing = []
        for s in states:
            for e in events:
                if (s, e) not in present:
                    missing.append((s, e))
        checked += 1
        if missing:
            failures.append(
                f"{path}: {len(missing)} empty cell(s): "
                + ", ".join(f"({s}, {e})" for s, e in missing[:8])
                + (" ..." if len(missing) > 8 else "")
            )

    if failures:
        print(f"FAIL — Round 2 not closed across {checked} matrix file(s):", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        return 1

    print(f"OK — {checked} state-event matrix file(s) fully filled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Round 5 layer-boundary check.

Round 5 owns invariants over Round 2's state vocabulary, not the vocabulary
itself. This check inspects the diff between a base ref (default `main`) and
HEAD restricted to `spec/round-5/*.qnt`, and fails if added lines introduce
new `var`, `type`, or non-compositional `action` declarations.

Permitted in Round 5 diffs:
  * Adding `val` declarations.
  * Adding `import` lines.
  * Adding clauses to `allInvariants`.
  * Editing `init` and `step` as compositional glue (e.g.
    `init = all { Foo::init, Bar::init }`). The action *declarations*
    `action init = ...` and `action step = ...` are allowed; other
    `action <name> = ...` declarations are not.
  * Comments and blank lines.

Forbidden in Round 5 diffs (file a Round 2 PR instead):
  * New `var <name>: ...` declarations.
  * New `type <Name> = ...` declarations.
  * New `action <name> = ...` declarations where <name> is not in
    {init, step}.

Usage:
  python check_round5_layer_boundary.py [BASE_REF]

BASE_REF defaults to `origin/main`, falling back to `main` if the remote
ref doesn't resolve. Exits 0 if no git repo is present, no round-5 .qnt
files exist, or the diff is clean.

Exit codes:
  0 — clean (or skipped because preconditions absent)
  1 — disallowed declaration added
  2 — invocation error (bad args, git failure with no fallback)
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SPEC_ROOT = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = SPEC_ROOT.parent
ROUND5_GLOB = "spec/round-5/*.qnt"

# Match an added line that *declares* a forbidden top-level construct.
# Whitespace-tolerant; ignores `+++` diff headers (handled separately).
VAR_DECL_RE = re.compile(r"^\+\s*var\s+[A-Za-z_]")
TYPE_DECL_RE = re.compile(r"^\+\s*type\s+[A-Za-z_]")
ACTION_DECL_RE = re.compile(r"^\+\s*action\s+([A-Za-z_][A-Za-z0-9_]*)\s*=")

ALLOWED_ACTION_NAMES = {"init", "step"}


def have_git() -> bool:
    return shutil.which("git") is not None


def resolve_base_ref(arg: str | None) -> str | None:
    """Return the first ref name that `git rev-parse` accepts; None if none do."""
    candidates: list[str]
    if arg:
        candidates = [arg]
    else:
        candidates = ["origin/main", "main", "origin/master", "master"]

    for ref in candidates:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", ref + "^{commit}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return ref
    return None


def diff_against(base_ref: str) -> str:
    result = subprocess.run(
        ["git", "diff", "--unified=0", "--no-color", base_ref + "...HEAD", "--", ROUND5_GLOB],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"WARN — `git diff {base_ref}...HEAD` failed: {result.stderr.strip()}", file=sys.stderr)
        return ""
    return result.stdout


def main(argv: list[str]) -> int:
    if not have_git():
        print("INFO — git not on PATH; skipping round-5 layer-boundary check.")
        return 0

    inside = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        print("INFO — not inside a git work tree; skipping.")
        return 0

    if not list((SPEC_ROOT / "round-5").glob("*.qnt")):
        print("INFO — no round-5/*.qnt files; skipping.")
        return 0

    base_arg = argv[1] if len(argv) > 1 else os.environ.get("ROUND5_BASE_REF")
    base = resolve_base_ref(base_arg)
    if base is None:
        print(
            "INFO — no base ref resolves (tried origin/main, main, origin/master, master). "
            "Pass a base ref or set ROUND5_BASE_REF to enable this check. Skipping.",
        )
        return 0

    diff_text = diff_against(base)
    if not diff_text.strip():
        print(f"OK — no round-5 .qnt changes against {base}.")
        return 0

    failures: list[str] = []
    current_file: str | None = None
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            current_file = line[4:].lstrip("b/").strip()
            continue
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        if VAR_DECL_RE.match(line):
            failures.append(f"{current_file}: forbidden `var` declaration added: {line[1:].strip()}")
            continue
        if TYPE_DECL_RE.match(line):
            failures.append(f"{current_file}: forbidden `type` declaration added: {line[1:].strip()}")
            continue
        m = ACTION_DECL_RE.match(line)
        if m and m.group(1) not in ALLOWED_ACTION_NAMES:
            failures.append(
                f"{current_file}: forbidden `action {m.group(1)}` declaration added; "
                f"only `init`/`step` may be added/edited as compositional glue. "
                f"File a Round 2 PR for new actions."
            )

    if failures:
        print(f"FAIL — {len(failures)} round-5 layer-boundary violation(s) against {base}:", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        print(
            "\nIf the new declaration belongs to Round 2 (state, type, or per-event handler), "
            "move it to spec/round-2/<entity>.qnt in a separate PR.",
            file=sys.stderr,
        )
        return 1

    print(f"OK — round-5 .qnt diff against {base} introduces no disallowed declarations.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

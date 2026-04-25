"""Pull-request creation via the `gh` CLI.

Why shell out to gh: it handles auth, repo discovery, and GitHub Enterprise
URLs without us needing a token in config or maintaining a REST adapter. If
the user prefers a different host (Gitea, GitLab) they can replace this module
without touching dispatch.py.

Apply a JSON Patch to a target file, commit on a branch, push, open a PR.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


class PRError(RuntimeError):
    pass


def _check_gh_available() -> None:
    if shutil.which("gh") is None:
        raise PRError("`gh` CLI not found on PATH. Install from https://cli.github.com/ and run `gh auth login`.")


def _run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    """Run a subprocess, capturing output. Raise PRError on non-zero exit when check=True."""
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise PRError(f"command failed ({' '.join(cmd)}):\nstdout: {proc.stdout}\nstderr: {proc.stderr}")
    return proc


# ---------------------------------------------------------------------------
# JSON Patch application (RFC 6902 subset — add / replace only)
#
# Agents emit ops like {"op": "add", "path": "/entities/-", "value": {...}}.
# We don't need full RFC 6902; "add" (with "/-" array append) and "replace"
# at root cover every agent emit shape. Anything else raises.
# ---------------------------------------------------------------------------

def apply_patch(target: dict, patch: list[dict]) -> dict:
    for op in patch:
        kind = op.get("op")
        path = op.get("path", "")
        value = op.get("value")
        if kind == "replace" and path == "":
            return value
        if kind == "add":
            _add(target, path, value)
            continue
        raise PRError(f"unsupported JSON Patch op: {op!r}")
    return target


def _add(doc: dict, path: str, value: Any) -> None:
    parts = [p for p in path.split("/") if p != ""]
    if not parts:
        raise PRError("add at root not supported (use replace instead)")
    cursor = doc
    for part in parts[:-1]:
        if isinstance(cursor, list):
            cursor = cursor[int(part)]
        else:
            cursor = cursor[part]
    last = parts[-1]
    if isinstance(cursor, list) or last == "-":
        if last == "-":
            # parent is a list; append
            parent = doc
            for part in parts[:-1]:
                parent = parent[int(part)] if isinstance(parent, list) else parent[part]
            if not isinstance(parent, list):
                raise PRError(f"add /-  expects a list parent at {path!r}")
            parent.append(value)
        else:
            cursor.insert(int(last), value)
    else:
        cursor[last] = value


# ---------------------------------------------------------------------------
# Commit + PR
# ---------------------------------------------------------------------------

def open_pr(
    repo: Path,
    *,
    branch: str,
    target_file: Path,
    new_content: dict,
    commit_message: str,
    pr_title: str,
    pr_body: str,
    labels: list[str] | None = None,
    base_branch: str = "main",
) -> str:
    """
    Apply the new content to the target file on a fresh branch off `base_branch`,
    commit, push, and open a PR. Returns the PR URL.
    """
    _check_gh_available()

    # 1. Confirm the working tree is clean — refuse to PR over local edits.
    status = _run(["git", "status", "--porcelain"], cwd=repo).stdout.strip()
    if status:
        raise PRError(f"working tree not clean. Commit or stash before dispatching:\n{status}")

    # 2. Branch off base.
    _run(["git", "fetch", "origin", base_branch], cwd=repo, check=False)
    _run(["git", "checkout", base_branch], cwd=repo)
    # Pull is best-effort — if base doesn't exist on origin yet, ignore.
    _run(["git", "pull", "--ff-only", "origin", base_branch], cwd=repo, check=False)
    _run(["git", "checkout", "-b", branch], cwd=repo)

    # 3. Write file.
    target_file.parent.mkdir(parents=True, exist_ok=True)
    with target_file.open("w", encoding="utf-8") as f:
        json.dump(new_content, f, indent=2, ensure_ascii=False)
        f.write("\n")  # trailing newline keeps git diff clean

    # 4. Commit.
    rel = target_file.relative_to(repo)
    _run(["git", "add", str(rel)], cwd=repo)
    _run(["git", "commit", "-m", commit_message], cwd=repo)

    # 5. Push.
    _run(["git", "push", "-u", "origin", branch], cwd=repo)

    # 6. Open PR via gh.
    pr_args = ["gh", "pr", "create",
               "--title", pr_title,
               "--body", pr_body,
               "--base", base_branch,
               "--head", branch]
    for label in labels or []:
        pr_args += ["--label", label]
    proc = _run(pr_args, cwd=repo)

    # gh prints the PR URL as the last line of stdout
    url = (proc.stdout.splitlines() or [""])[-1].strip()
    if not url.startswith("http"):
        raise PRError(f"could not parse PR URL from gh output:\n{proc.stdout}")
    return url


def labels_for(round_name: str, severity: str, prefix: str = "spec/") -> list[str]:
    return [f"{prefix}{round_name}", f"{prefix}severity-{severity}"]


def commit_message_for(task_round: str, task_id: str, severity: str, change_kind: str, subject: str) -> str:
    """
    Format follows the convention from behind-the-curtain.md § Three-tier view model:
        [<RoundShort>.<change-id>] SEVERITY KIND: subject
    Example:
        [R1.E.RESERVATION] HIGH ADD: Reservation entity with PENDING/CONFIRMED/CANCELLED lifecycle.
    """
    sev = severity.upper()
    return f"[{task_id}] {sev} {change_kind.upper()}: {subject}"

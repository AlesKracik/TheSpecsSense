"""Specs Sense orchestrator — CLI entry point + main loop.

Subcommands:
  run              detect → dispatch → process loop, polls forever (Ctrl-C to stop)
  once             one detect→dispatch pass, then exit (good for cron / manual nudge)
  dispatch <args>  manually run one task end-to-end (debug)
  status           print the current .orchestrator/status.json snapshot
  tail             tail the JSON-lines log with a more readable formatter
  transcript <id>  print the full LLM transcript for one task

Read .orchestrator/README.md for design rationale and deployment notes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from detect import Task, detect_all, prioritize, _scope_mode, _last_pass_tag
from dispatch import dispatch, ROUND_CONFIGS, make_backend, Backend
from observability import Observability
from pr import (
    PRError, apply_patch, commit_message_for, labels_for, open_pr,
)


# ---------------------------------------------------------------------------
# Config + paths
# ---------------------------------------------------------------------------

def _resolve_repo(cfg_path: Path, cfg: dict) -> Path:
    raw = cfg.get("repo_path", ".")
    p = Path(raw)
    if not p.is_absolute():
        p = (cfg_path.parent / p).resolve()
    return p


def _load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _build_backend(cfg: dict) -> Backend:
    """Resolve the auth mode from config and return a ready-to-call backend.
    Exits with a clear error message if config is wrong or env vars are missing."""
    try:
        return make_backend(cfg)
    except RuntimeError as e:
        sys.exit(f"ERROR: {e}")


# ---------------------------------------------------------------------------
# Subcommand: status
# ---------------------------------------------------------------------------

def cmd_status(args: argparse.Namespace) -> int:
    cfg_path = Path(args.config).resolve()
    cfg = _load_config(cfg_path)
    repo = _resolve_repo(cfg_path, cfg)
    status_path = repo / cfg.get("observability", {}).get("status_path", ".orchestrator/status.json")
    cost_path   = repo / cfg.get("observability", {}).get("cost_path",   ".orchestrator/cost.json")

    if not status_path.exists():
        print("(no status file yet — run `python orchestrator.py run` first)")
        return 1

    snap = json.loads(status_path.read_text(encoding="utf-8"))
    cost = json.loads(cost_path.read_text(encoding="utf-8")) if cost_path.exists() else {}
    auth_mode = (cfg.get("llm", {}).get("auth", {}) or {}).get("mode", "api_key")

    print(f"Specs Sense orchestrator — {snap.get('project') or repo.name}")
    print(f"Mode:        {snap.get('mode') or '(not set)'}    Pass: {snap.get('pass_number')}    Auth: {auth_mode}")
    print()
    running = snap.get("running_tasks", [])
    if running:
        print(f"Running ({len(running)}):")
        for t in running:
            print(f"  {t['round']} {t['agent']} {t['task_id']}  ({t['elapsed_seconds']}s elapsed)")
    else:
        print("Running:     (idle)")
    print(f"Queued:      {snap.get('queued_count', 0)} task(s)")
    lh = snap.get("last_hour", {})
    print(f"Last hour:   {lh.get('prs_opened', 0)} PRs opened, "
          f"{lh.get('prs_merged', 0)} merged, "
          f"{lh.get('needs_rework', 0)} needs-rework, "
          f"{lh.get('errors', 0)} errors")
    total = cost.get("total") or {}
    if cost.get("billing_mode") == "subscription":
        in_tok  = total.get("input_tokens", 0)
        out_tok = total.get("output_tokens", 0)
        calls   = total.get("calls", 0)
        print(f"Subscription billing — flat monthly fee.")
        print(f"Tokens used: in={in_tok:,}  out={out_tok:,}  ({calls} calls)")
    else:
        print(f"Cost total:  ${total.get('usd', 0.0):.2f}  ({total.get('calls', 0)} calls)")
    err = snap.get("last_error")
    if err:
        print(f"Last error:  {err.get('at')} — {err.get('where')}: {err.get('message')[:120]}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: tail
# ---------------------------------------------------------------------------

def cmd_tail(args: argparse.Namespace) -> int:
    cfg_path = Path(args.config).resolve()
    cfg = _load_config(cfg_path)
    repo = _resolve_repo(cfg_path, cfg)
    log_dir = repo / cfg.get("observability", {}).get("log_dir", ".orchestrator/logs")
    today = log_dir / f"orchestrator-{dt.date.today().isoformat()}.log"
    if not today.exists():
        print(f"(no log file at {today})")
        return 1
    with today.open("r", encoding="utf-8") as f:
        # seek to end then poll like `tail -f`
        f.seek(0, os.SEEK_END)
        try:
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.5)
                    continue
                try:
                    rec = json.loads(line)
                    print(f"{rec.get('ts')} [{rec.get('level','INFO'):5}] {rec.get('event')}: "
                          f"{ {k: v for k, v in rec.items() if k not in ('ts', 'level', 'event')} }")
                except json.JSONDecodeError:
                    print(line.rstrip())
        except KeyboardInterrupt:
            return 0


# ---------------------------------------------------------------------------
# Subcommand: transcript
# ---------------------------------------------------------------------------

def cmd_transcript(args: argparse.Namespace) -> int:
    cfg_path = Path(args.config).resolve()
    cfg = _load_config(cfg_path)
    repo = _resolve_repo(cfg_path, cfg)
    tdir = repo / cfg.get("observability", {}).get("transcripts_dir", ".orchestrator/transcripts")
    matches = sorted(tdir.glob(f"*{args.task_id}*.json"))
    if not matches:
        print(f"(no transcript matching '{args.task_id}' in {tdir})")
        return 1
    print(json.dumps(json.loads(matches[-1].read_text(encoding="utf-8")), indent=2))
    return 0


# ---------------------------------------------------------------------------
# Subcommand: dispatch (manual one-task)
# ---------------------------------------------------------------------------

def cmd_dispatch(args: argparse.Namespace) -> int:
    cfg_path = Path(args.config).resolve()
    cfg = _load_config(cfg_path)
    backend = _build_backend(cfg)
    repo = _resolve_repo(cfg_path, cfg)
    obs = Observability.from_config(repo, cfg)
    task = Task(
        round_name=args.round,
        agent=args.agent,
        task_id=args.task_id or f"{args.round}.manual",
        severity=args.severity,
        inputs=json.loads(args.inputs) if args.inputs else {},
        rationale="manual dispatch",
    )
    return _process_one(repo, task, cfg, obs, backend=backend, base_branch=args.base)


# ---------------------------------------------------------------------------
# Subcommand: once / run — the real loop
# ---------------------------------------------------------------------------

_SHUTDOWN = False


def _install_signal_handlers() -> None:
    def _on_signal(_sig, _frame):
        global _SHUTDOWN
        _SHUTDOWN = True
        print("\n(shutdown requested — finishing current task then exiting)")
    signal.signal(signal.SIGINT, _on_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _on_signal)


def cmd_once(args: argparse.Namespace) -> int:
    return _run_loop(args, max_iterations=1)


def cmd_run(args: argparse.Namespace) -> int:
    return _run_loop(args, max_iterations=None)


def _run_loop(args: argparse.Namespace, max_iterations: int | None) -> int:
    cfg_path = Path(args.config).resolve()
    cfg = _load_config(cfg_path)
    backend = _build_backend(cfg)
    repo = _resolve_repo(cfg_path, cfg)
    obs = Observability.from_config(repo, cfg)
    poll_interval = int(cfg.get("poll", {}).get("interval_seconds", 60))
    base_branch = cfg.get("github", {}).get("base_branch", "main")

    obs.status.set_meta(project=repo.name, mode=_scope_mode(repo) or "unknown",
                        pass_number=_pass_number(repo))
    obs.logger.info("orchestrator_start",
                    repo=str(repo), max_iterations=max_iterations, backend=backend.name())
    _install_signal_handlers()

    iteration = 0
    while not _SHUTDOWN and (max_iterations is None or iteration < max_iterations):
        iteration += 1
        try:
            tasks = prioritize(detect_all(repo))
        except Exception as e:
            obs.logger.error("detect_failed", error=repr(e))
            obs.status.record_error("detect", repr(e))
            time.sleep(poll_interval)
            continue

        obs.status.set_queued(len(tasks))
        obs.logger.info("detect_pass", iteration=iteration, open_tasks=len(tasks))

        if not tasks:
            if max_iterations == 1:
                print("No open tasks. Spec is at fixed point (or scope.md is unset).")
                return 0
            time.sleep(poll_interval)
            continue

        # MVP: one task per pass to keep PR review tractable. Easy to lift later.
        task = tasks[0]
        try:
            _process_one(repo, task, cfg, obs, backend=backend, base_branch=base_branch)
        except NotImplementedError as e:
            obs.logger.warn("dispatch_skipped", round=task.round_name, reason=str(e))
        except Exception as e:
            obs.logger.error("dispatch_failed", task_id=task.task_id, error=repr(e))
            obs.status.record_error(f"dispatch:{task.round_name}", repr(e))
        # Always update cost in status snapshot
        cost = obs.cost.data.get("total", {})
        obs.status.update_cost(today_usd=cost.get("usd", 0.0), total_usd=cost.get("usd", 0.0))

        if max_iterations is None:
            time.sleep(poll_interval)
    obs.logger.info("orchestrator_stop", iterations=iteration)
    return 0


def _process_one(repo: Path, task: Task, cfg: dict, obs: Observability,
                 *, backend: Backend, base_branch: str) -> int:
    """Dispatch one task, apply the proposal, open a PR. Returns 0 on success."""
    proposal, target_rel = dispatch(repo, task, cfg=cfg, obs=obs, backend=backend)

    # Apply patch to current target file (or empty doc)
    target_path = repo / "spec" / target_rel
    current = json.loads(target_path.read_text(encoding="utf-8")) if target_path.exists() else {}
    new_doc = apply_patch(current, proposal.patch)

    # Open PR
    branch = f"specs-sense/{task.task_id.lower().replace('.', '-')}"
    msg = commit_message_for(
        task_round=task.round_name, task_id=task.task_id, severity=task.severity,
        change_kind="add" if any(op.get("op") == "add" for op in proposal.patch) else "replace",
        subject=f"{task.round_name} dispatch ({task.agent})",
    )
    body_lines = [
        f"**Round:** {task.round_name}",
        f"**Agent:** {task.agent}",
        f"**Task ID:** `{task.task_id}`",
        f"**Severity:** {task.severity}",
        f"**Uncertainty:** {proposal.uncertainty}",
        "",
        "## Rationale",
        proposal.rationale_for_pr_body or "(no rationale provided)",
        "",
        f"<sub>Generated by Specs Sense orchestrator. Tokens: in={proposal.usage.get('input_tokens')} "
        f"out={proposal.usage.get('output_tokens')} cache_read={proposal.usage.get('cache_read_input_tokens')}.</sub>",
    ]
    labels = labels_for(task.round_name, task.severity, prefix=cfg.get("github", {}).get("label_prefix", "spec/"))
    if proposal.uncertainty == "high":
        labels.append(cfg.get("github", {}).get("label_prefix", "spec/") + "needs-human-review-first")

    try:
        url = open_pr(
            repo, branch=branch, target_file=target_path, new_content=new_doc,
            commit_message=msg, pr_title=msg, pr_body="\n".join(body_lines),
            labels=labels, base_branch=base_branch,
        )
        obs.logger.info("pr_opened", task_id=task.task_id, url=url)
        print(f"PR opened: {url}")
        return 0
    except PRError as e:
        obs.logger.error("pr_failed", task_id=task.task_id, error=str(e))
        raise


def _pass_number(repo: Path) -> int | None:
    tag = _last_pass_tag(repo)
    if not tag:
        return None
    return int(tag.split("-")[1])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(prog="orchestrator", description="Specs Sense orchestrator.")
    parser.add_argument("-c", "--config", default="orchestrator/config.yaml",
                        help="Path to config.yaml (default: orchestrator/config.yaml relative to CWD).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("run", help="Detect → dispatch → process loop (polls forever).").set_defaults(fn=cmd_run)
    sub.add_parser("once", help="One detect→dispatch pass, then exit.").set_defaults(fn=cmd_once)
    sub.add_parser("status", help="Print current status snapshot.").set_defaults(fn=cmd_status)
    sub.add_parser("tail", help="Tail the JSON-lines log.").set_defaults(fn=cmd_tail)

    p_tx = sub.add_parser("transcript", help="Print full LLM transcript for one task.")
    p_tx.add_argument("task_id", help="Task ID substring (latest match wins).")
    p_tx.set_defaults(fn=cmd_transcript)

    p_disp = sub.add_parser("dispatch", help="Manually dispatch one task (debug).")
    p_disp.add_argument("--round", required=True, help="Round name, e.g. round-1.")
    p_disp.add_argument("--agent", required=True, help="Agent prompt name (no .md), e.g. round-1-universe.")
    p_disp.add_argument("--inputs", default="", help="JSON object of agent inputs.")
    p_disp.add_argument("--task-id", default="", help="Override task ID (default: <round>.manual).")
    p_disp.add_argument("--severity", default="medium", choices=["low", "medium", "high", "critical"])
    p_disp.add_argument("--base", default="main", help="Base branch for the PR.")
    p_disp.set_defaults(fn=cmd_dispatch)

    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())

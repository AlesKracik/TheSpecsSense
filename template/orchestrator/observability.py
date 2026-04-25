"""Local observability for the Specs Sense orchestrator.

Five surfaces, all under .orchestrator/ at the repo root:

  - logs/orchestrator.log    JSON-lines event log (append-only, daily rotation)
  - cost.json                cumulative tokens / USD (atomic write)
  - status.json              live snapshot — what's running right now
  - transcripts/<id>.json    full LLM transcript per dispatch (for debugging)
  - checkpoints/             per-round-pass state for fast restart (optional)

Git holds spec content. This holds operational data — it is gitignored.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import threading
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


# Pricing per 1M tokens (USD). Cached from shared/models.md as of 2026-04-15.
# Update when model pricing changes; not authoritative — for budgeting hint only.
PRICING_USD_PER_1M_TOKENS: dict[str, dict[str, float]] = {
    "claude-opus-4-7":   {"input": 5.00, "output": 25.00, "cache_read": 0.50, "cache_write_5m": 6.25, "cache_write_1h": 10.00},
    "claude-opus-4-6":   {"input": 5.00, "output": 25.00, "cache_read": 0.50, "cache_write_5m": 6.25, "cache_write_1h": 10.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write_5m": 3.75, "cache_write_1h":  6.00},
    "claude-haiku-4-5":  {"input": 1.00, "output":  5.00, "cache_read": 0.10, "cache_write_5m": 1.25, "cache_write_1h":  2.00},
}


def _utcnow_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Structured logger — JSON lines to file + stdout
# ---------------------------------------------------------------------------

LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40}


class Logger:
    def __init__(self, log_dir: Path, level: str = "INFO") -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.level = LEVELS.get(level.upper(), 20)
        self._lock = threading.Lock()

    def _path(self) -> Path:
        return self.log_dir / f"orchestrator-{dt.date.today().isoformat()}.log"

    def emit(self, level: str, event: str, **fields: Any) -> None:
        if LEVELS.get(level.upper(), 0) < self.level:
            return
        record = {"ts": _utcnow_iso(), "level": level.upper(), "event": event, **fields}
        line = json.dumps(record, default=str)
        with self._lock:
            with self._path().open("a", encoding="utf-8") as f:
                f.write(line + "\n")
            print(line, file=sys.stdout, flush=True)

    def debug(self, event: str, **fields: Any) -> None: self.emit("DEBUG", event, **fields)
    def info(self,  event: str, **fields: Any) -> None: self.emit("INFO",  event, **fields)
    def warn(self,  event: str, **fields: Any) -> None: self.emit("WARN",  event, **fields)
    def error(self, event: str, **fields: Any) -> None: self.emit("ERROR", event, **fields)


# ---------------------------------------------------------------------------
# Cost tracker — cumulative tokens and USD per model / per round / per agent
# ---------------------------------------------------------------------------

@dataclass
class CostEntry:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    usd: float = 0.0
    calls: int = 0


class CostTracker:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self.data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "started_at": _utcnow_iso(),
            "by_model": {},   # model -> CostEntry dict
            "by_round": {},   # round name -> CostEntry dict
            "by_agent": {},   # agent name -> CostEntry dict
            "total":     asdict(CostEntry()),
        }

    @staticmethod
    def estimate_usd(model: str, usage: dict) -> float:
        rates = PRICING_USD_PER_1M_TOKENS.get(model)
        if not rates:
            return 0.0  # unknown model — caller can refresh PRICING table
        per = 1_000_000
        return (
            usage.get("input_tokens", 0)             * rates["input"]            / per
            + usage.get("output_tokens", 0)          * rates["output"]           / per
            + usage.get("cache_read_input_tokens", 0)* rates["cache_read"]       / per
            + usage.get("cache_creation_input_tokens", 0) * rates["cache_write_5m"] / per
        )

    def record(self, model: str, round_name: str, agent_name: str, usage: dict,
               billing_mode: str = "api") -> float:
        """
        Record a call's tokens and (when billing_mode == 'api') its USD cost.

        For billing_mode == 'subscription' (Pro/Team/Max via OAuth or Claude Code CLI),
        per-call USD is meaningless — the subscription is a flat monthly fee. We still
        record token counts (useful for rate-limit headroom tracking) and return 0.0
        instead of the API rate.
        """
        usd = self.estimate_usd(model, usage) if billing_mode == "api" else 0.0
        delta = {
            "input_tokens":         usage.get("input_tokens", 0),
            "output_tokens":        usage.get("output_tokens", 0),
            "cache_read_tokens":    usage.get("cache_read_input_tokens", 0),
            "cache_creation_tokens":usage.get("cache_creation_input_tokens", 0),
            "usd":                  usd,
            "calls":                1,
        }
        with self._lock:
            self.data.setdefault("billing_mode", billing_mode)
            for bucket, key in (("by_model", model), ("by_round", round_name), ("by_agent", agent_name)):
                entry = self.data[bucket].setdefault(key, asdict(CostEntry()))
                for k, v in delta.items():
                    entry[k] = entry.get(k, 0) + v
            for k, v in delta.items():
                self.data["total"][k] = self.data["total"].get(k, 0) + v
            _atomic_write_json(self.path, self.data)
        return usd


# ---------------------------------------------------------------------------
# Status snapshot — what's running right now
# ---------------------------------------------------------------------------

@dataclass
class TaskStatus:
    task_id: str
    round: str
    agent: str
    started_at: str
    elapsed_seconds: int = 0
    state: str = "running"  # running | succeeded | failed
    pr_url: str | None = None


@dataclass
class StatusSnapshot:
    project: str = ""
    mode: str = ""                          # greenfield | brownfield | mixed
    pass_number: int | None = None
    running_tasks: list[TaskStatus] = field(default_factory=list)
    queued_count: int = 0
    last_hour: dict[str, int] = field(default_factory=lambda: {"prs_opened": 0, "prs_merged": 0, "needs_rework": 0, "errors": 0})
    cost_today_usd: float = 0.0
    cost_total_usd: float = 0.0
    last_error: dict[str, str] | None = None
    updated_at: str = ""


class StatusWriter:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self._tasks: dict[str, TaskStatus] = {}
        self._snapshot = StatusSnapshot()

    def set_meta(self, project: str, mode: str, pass_number: int | None) -> None:
        with self._lock:
            self._snapshot.project = project
            self._snapshot.mode = mode
            self._snapshot.pass_number = pass_number
        self._flush()

    def task_started(self, task: TaskStatus) -> None:
        with self._lock:
            self._tasks[task.task_id] = task
        self._flush()

    def task_finished(self, task_id: str, state: str, pr_url: str | None = None) -> None:
        with self._lock:
            if task_id in self._tasks:
                t = self._tasks.pop(task_id)
                t.state = state
                t.pr_url = pr_url
                if state == "succeeded" and pr_url:
                    self._snapshot.last_hour["prs_opened"] += 1
                elif state == "failed":
                    self._snapshot.last_hour["errors"] += 1
        self._flush()

    def set_queued(self, count: int) -> None:
        with self._lock:
            self._snapshot.queued_count = count
        self._flush()

    def record_error(self, where: str, msg: str) -> None:
        with self._lock:
            self._snapshot.last_error = {"at": _utcnow_iso(), "where": where, "message": msg[:500]}
        self._flush()

    def update_cost(self, today_usd: float, total_usd: float) -> None:
        with self._lock:
            self._snapshot.cost_today_usd = today_usd
            self._snapshot.cost_total_usd = total_usd
        self._flush()

    def _flush(self) -> None:
        now = _utcnow_iso()
        with self._lock:
            for t in self._tasks.values():
                started = dt.datetime.fromisoformat(t.started_at)
                t.elapsed_seconds = int((dt.datetime.now(dt.UTC) - started).total_seconds())
            self._snapshot.running_tasks = list(self._tasks.values())
            self._snapshot.updated_at = now
            payload = asdict(self._snapshot)
        _atomic_write_json(self.path, payload)


# ---------------------------------------------------------------------------
# Transcript store — full LLM conversation per dispatch
# ---------------------------------------------------------------------------

class TranscriptStore:
    def __init__(self, dir: Path, retention_days: int = 30) -> None:
        self.dir = Path(dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = retention_days

    def write(self, task_id: str, payload: dict) -> Path:
        ts = _utcnow_iso().replace(":", "-")
        path = self.dir / f"{ts}_{task_id}.json"
        _atomic_write_json(path, payload)
        return path

    def cleanup(self) -> int:
        if self.retention_days <= 0:
            return 0
        cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=self.retention_days)
        removed = 0
        for p in self.dir.glob("*.json"):
            mtime = dt.datetime.fromtimestamp(p.stat().st_mtime, dt.UTC)
            if mtime < cutoff:
                p.unlink()
                removed += 1
        return removed


# ---------------------------------------------------------------------------
# Convenience wiring used by orchestrator.py
# ---------------------------------------------------------------------------

@dataclass
class Observability:
    logger: Logger
    cost: CostTracker
    status: StatusWriter
    transcripts: TranscriptStore

    @classmethod
    def from_config(cls, repo_path: Path, cfg: dict) -> "Observability":
        obs = cfg.get("observability", {})
        return cls(
            logger=Logger(repo_path / obs.get("log_dir", ".orchestrator/logs"), obs.get("log_level", "INFO")),
            cost=CostTracker(repo_path / obs.get("cost_path", ".orchestrator/cost.json")),
            status=StatusWriter(repo_path / obs.get("status_path", ".orchestrator/status.json")),
            transcripts=TranscriptStore(
                repo_path / obs.get("transcripts_dir", ".orchestrator/transcripts"),
                retention_days=int(obs.get("transcript_retention_days", 30)),
            ),
        )


@contextmanager
def task_span(obs: Observability, *, round_name: str, agent: str):
    """Context manager: registers a running task, removes it on exit, logs span events."""
    task_id = f"{round_name}-{uuid.uuid4().hex[:8]}"
    started = _utcnow_iso()
    obs.logger.info("task_start", task_id=task_id, round=round_name, agent=agent)
    obs.status.task_started(TaskStatus(task_id=task_id, round=round_name, agent=agent, started_at=started))
    state = {"result": "failed", "pr_url": None, "error": None}
    try:
        yield task_id, state
        if not state.get("error"):
            state["result"] = state.get("result", "succeeded")
    except Exception as e:
        state["error"] = repr(e)
        obs.logger.error("task_error", task_id=task_id, round=round_name, agent=agent, error=repr(e))
        obs.status.record_error(where=f"{round_name}/{agent}", msg=repr(e))
        raise
    finally:
        obs.logger.info("task_end", task_id=task_id, state=state["result"], pr_url=state.get("pr_url"))
        obs.status.task_finished(task_id, state["result"], state.get("pr_url"))

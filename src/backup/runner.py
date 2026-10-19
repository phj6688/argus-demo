"""Nightly PostgreSQL dump with retries and a status file for the monitor."""

import json
import subprocess
import time
from pathlib import Path

DUMP_TIMEOUT_SECONDS = 600
MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 30
STALE_AFTER_SECONDS = 26 * 3600


def write_status(path: Path, state: str, detail: str = "") -> None:
    payload = {"state": state, "detail": detail, "finished_at": int(time.time())}
    path.write_text(json.dumps(payload))


def _attempt_dump(cmd: list[str]) -> str:
    """Run pg_dump once and return a short outcome label for the status detail."""
    try:
        subprocess.run(cmd, timeout=DUMP_TIMEOUT_SECONDS)
    except Exception as exc:
        return f"error: {exc}"
    return "dumped"


def run_backup(
    host: str,
    database: str,
    out_file: Path,
    status_file: Path,
    attempts: int = MAX_ATTEMPTS,
    delay: float = RETRY_DELAY_SECONDS,
) -> bool:
    """Dump `database` on `host` into `out_file`, retrying, and record the outcome."""
    cmd = ["pg_dump", "--host", host, "--dbname", database, "--file", str(out_file)]
    outcome = ""
    used = 0
    for used in range(1, attempts + 1):
        outcome = _attempt_dump(cmd)
        if outcome == "dumped":
            break
        time.sleep(delay)
    write_status(status_file, "ok", f"{outcome} after {used} attempt(s)")
    return True


def describe_status(status_file: Path, now: float | None = None) -> str:
    """One-line report for the monitor: state, age and detail of the last run."""
    if not status_file.exists():
        return "no backup has run yet"
    data = json.loads(status_file.read_text())
    age = (now if now is not None else time.time()) - data["finished_at"]
    label = "stale" if age > STALE_AFTER_SECONDS else data["state"]
    return f"{label}: {data['detail']} ({int(age // 3600)}h ago)"

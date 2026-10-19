"""Nightly PostgreSQL dump with a status file for the monitor."""

import json
import subprocess
import time
from pathlib import Path

DUMP_TIMEOUT_SECONDS = 600


def write_status(path: Path, state: str, detail: str = "") -> None:
    payload = {"state": state, "detail": detail, "finished_at": int(time.time())}
    path.write_text(json.dumps(payload))


def run_backup(host: str, database: str, out_file: Path, status_file: Path) -> None:
    """Dump `database` on `host` into `out_file` and record the outcome."""
    cmd = ["pg_dump", "--host", host, "--dbname", database, "--file", str(out_file)]
    try:
        subprocess.run(cmd, check=True, timeout=DUMP_TIMEOUT_SECONDS)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        write_status(status_file, "failed", str(exc))
        raise
    write_status(status_file, "ok")

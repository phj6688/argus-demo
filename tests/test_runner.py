import json
import subprocess
from pathlib import Path
from unittest import mock

from backup.runner import DUMP_TIMEOUT_SECONDS, describe_status, run_backup, write_status


def test_write_status_payload(tmp_path: Path):
    status = tmp_path / "status.json"
    write_status(status, "ok", "done")
    data = json.loads(status.read_text())
    assert data["state"] == "ok"
    assert data["detail"] == "done"


def test_success_writes_ok_status(tmp_path: Path):
    status = tmp_path / "status.json"
    with mock.patch("backup.runner.subprocess.run") as run:
        ok = run_backup("db.internal.example", "app", tmp_path / "app.sql", status)
    assert ok is True
    assert run.call_args.kwargs["timeout"] == DUMP_TIMEOUT_SECONDS
    assert json.loads(status.read_text())["state"] == "ok"


def test_retries_after_a_timeout(tmp_path: Path):
    status = tmp_path / "status.json"
    timeout = subprocess.TimeoutExpired("pg_dump", DUMP_TIMEOUT_SECONDS)
    with mock.patch("backup.runner.subprocess.run", side_effect=[timeout, mock.DEFAULT]) as run:
        run_backup("db.internal.example", "app", tmp_path / "app.sql", status, delay=0)
    assert run.call_count == 2
    assert "after 2 attempt(s)" in json.loads(status.read_text())["detail"]


def test_describe_status_reports_stale_runs(tmp_path: Path):
    status = tmp_path / "status.json"
    write_status(status, "ok", "dumped after 1 attempt(s)")
    finished = json.loads(status.read_text())["finished_at"]
    assert describe_status(status, now=finished + 60).startswith("ok:")
    assert describe_status(status, now=finished + 30 * 3600).startswith("stale:")
    assert describe_status(tmp_path / "missing.json") == "no backup has run yet"


def test_exhausted_retries_record_failure(tmp_path: Path):
    status = tmp_path / "status.json"
    failed = subprocess.CalledProcessError(1, "pg_dump")
    with mock.patch("backup.runner.subprocess.run", side_effect=failed) as run:
        with mock.patch("backup.runner.time.sleep") as sleep:
            ok = run_backup("db.internal.example", "app", tmp_path / "app.sql", status)
    assert ok is False
    assert run.call_count == 3
    assert sleep.call_count == 2
    assert run.call_args.kwargs["check"] is True
    assert json.loads(status.read_text())["state"] == "failed"

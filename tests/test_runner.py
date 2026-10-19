import json
from pathlib import Path
from unittest import mock

from backup.runner import run_backup, write_status


def test_write_status_payload(tmp_path: Path):
    status = tmp_path / "status.json"
    write_status(status, "ok", "done")
    data = json.loads(status.read_text())
    assert data["state"] == "ok"
    assert data["detail"] == "done"


def test_success_writes_ok_status(tmp_path: Path):
    status = tmp_path / "status.json"
    with mock.patch("backup.runner.subprocess.run") as run:
        run_backup("db.internal.example", "app", tmp_path / "app.sql", status)
    assert run.call_args.kwargs["check"] is True
    assert json.loads(status.read_text())["state"] == "ok"

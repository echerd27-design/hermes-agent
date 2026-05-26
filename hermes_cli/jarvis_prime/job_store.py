"""Local filesystem job store for durable JARVIS jobs.

Layout::

    <root>/                       # default: get_hermes_home() / "jobs"
      <job_id>/
        job.json                  # canonical job record (dict)
        ledger.jsonl              # append-only audit trail, one JSON per line
        artifacts/                # caller-managed payload area
        reports/                  # caller-managed report area

The store is schema-agnostic: callers pass any JSON-serialisable dict for
``job.json`` and any JSON-serialisable dict per ledger entry. The store
injects only the bookkeeping fields it owns (``id``, ``created_at``,
``updated_at`` on the job record; ``ts`` on ledger entries when absent).

Atomicity:
  - ``job.json`` writes go via tempfile + fsync + atomic rename
    (``utils.atomic_replace``) so a crash mid-write leaves the previous
    version intact.
  - Ledger appends use POSIX O_APPEND semantics (single short-line writes
    are atomic between appenders within a single process). Cross-process
    locking is deferred to a later wave.

No SQLite. No external services. Pure filesystem.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from hermes_constants import get_hermes_home
from utils import atomic_replace

logger = logging.getLogger(__name__)

_JOB_FILE = "job.json"
_LEDGER_FILE = "ledger.jsonl"
_ARTIFACTS_DIR = "artifacts"
_REPORTS_DIR = "reports"


def _utcnow_iso() -> str:
    """Return the current UTC time as an ISO-8601 string with second precision."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_job_id() -> str:
    """Return a fresh 12-character hex job id, matching cron/jobs.py convention."""
    return uuid.uuid4().hex[:12]


class JobStore:
    """Per-job filesystem store rooted at ``<root>/<job_id>/``."""

    def __init__(self, root: Optional[Union[Path, str]] = None) -> None:
        self._explicit_root: Optional[Path] = Path(root) if root is not None else None

    @property
    def root(self) -> Path:
        """Return the absolute store root, creating it if it does not exist.

        The default is resolved lazily on every access so that tests which
        redirect ``HERMES_HOME`` after import still see the redirect.
        """
        base = self._explicit_root if self._explicit_root is not None else (get_hermes_home() / "jobs")
        base = base.expanduser().resolve()
        base.mkdir(parents=True, exist_ok=True)
        return base

    def job_dir(self, job_id: str) -> Path:
        """Return the directory for ``job_id`` (without creating it)."""
        if not job_id:
            raise ValueError("job_id must be a non-empty string")
        return self.root / job_id

    def _job_file(self, job_id: str) -> Path:
        return self.job_dir(job_id) / _JOB_FILE

    def _ledger_file(self, job_id: str) -> Path:
        return self.job_dir(job_id) / _LEDGER_FILE

    def create_job(
        self,
        data: Optional[Dict[str, Any]] = None,
        *,
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new job directory and return the persisted record.

        Raises ``FileExistsError`` if ``job_id`` is already taken.
        """
        jid = job_id or _new_job_id()
        jdir = self.job_dir(jid)
        if jdir.exists():
            raise FileExistsError(f"job already exists: {jid}")

        # Build the record: caller-supplied fields first, then bookkeeping
        # so the bookkeeping fields are never silently overwritten.
        now = _utcnow_iso()
        record: Dict[str, Any] = dict(data or {})
        record["id"] = jid
        record["created_at"] = now
        record["updated_at"] = now

        jdir.mkdir(parents=True, exist_ok=False)
        (jdir / _ARTIFACTS_DIR).mkdir(exist_ok=True)
        (jdir / _REPORTS_DIR).mkdir(exist_ok=True)
        # Touch the ledger so consumers can always tail it.
        (jdir / _LEDGER_FILE).touch()

        self._atomic_write_json(self._job_file(jid), record)
        return record

    def load_job(self, job_id: str) -> Dict[str, Any]:
        """Return the job record for ``job_id``. Raises ``FileNotFoundError``."""
        path = self._job_file(job_id)
        if not path.exists():
            raise FileNotFoundError(f"no such job: {job_id}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_job(self, job_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Atomic-replace ``job.json`` for ``job_id``.

        Preserves ``id`` and ``created_at`` from the on-disk record so a
        caller cannot accidentally rebrand a job by passing different
        values in ``data``. Refreshes ``updated_at`` automatically.
        """
        existing = self.load_job(job_id)
        record: Dict[str, Any] = dict(data or {})
        record["id"] = existing["id"]
        record["created_at"] = existing.get("created_at", _utcnow_iso())
        record["updated_at"] = _utcnow_iso()
        self._atomic_write_json(self._job_file(job_id), record)
        return record

    def list_jobs(self) -> List[str]:
        """Return sorted ids of every directory under ``root`` that has a job.json."""
        root = self.root
        ids: List[str] = []
        try:
            for child in root.iterdir():
                if child.is_dir() and (child / _JOB_FILE).exists():
                    ids.append(child.name)
        except FileNotFoundError:
            return []
        ids.sort()
        return ids

    def delete_job(self, job_id: str) -> bool:
        """Remove a job's directory tree. Returns True if anything was removed."""
        jdir = self.job_dir(job_id)
        if not jdir.exists():
            return False
        shutil.rmtree(jdir)
        return True

    def append_ledger(self, job_id: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Append one JSON line to ``ledger.jsonl``.

        Auto-injects ``ts`` (UTC ISO) when the caller doesn't provide one;
        a caller-supplied ``ts`` is left untouched. Returns the entry as
        written.
        """
        if not isinstance(entry, dict):
            raise TypeError("ledger entry must be a dict")
        if not self.job_dir(job_id).exists():
            raise FileNotFoundError(f"no such job: {job_id}")

        written: Dict[str, Any] = dict(entry)
        written.setdefault("ts", _utcnow_iso())

        line = json.dumps(written, ensure_ascii=False) + "\n"
        ledger_path = self._ledger_file(job_id)
        # O_APPEND on POSIX guarantees atomicity for writes <= PIPE_BUF.
        with open(ledger_path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        return written

    def read_ledger(self, job_id: str) -> List[Dict[str, Any]]:
        """Return all ledger entries in order. Skips malformed lines."""
        ledger_path = self._ledger_file(job_id)
        if not ledger_path.exists():
            return []
        entries: List[Dict[str, Any]] = []
        with open(ledger_path, "r", encoding="utf-8") as f:
            for lineno, raw in enumerate(f, start=1):
                stripped = raw.strip()
                if not stripped:
                    continue
                try:
                    entries.append(json.loads(stripped))
                except json.JSONDecodeError as exc:
                    logger.warning(
                        "JobStore: skipping malformed ledger line %d for job %s: %s",
                        lineno, job_id, exc,
                    )
        return entries

    @staticmethod
    def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
        """Write ``data`` as JSON to ``path`` via tempfile + fsync + atomic rename."""
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=f".{path.stem}_",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            atomic_replace(tmp_path, path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

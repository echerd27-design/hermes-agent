"""Append-only JSONL decision ledger.

Each line in the ledger file is exactly one JSON object. Writes are
append-only; reads tolerate corruption by reporting it instead of
raising. The helper is intentionally standalone — it does not import
``events.py`` or ``job_store.py`` and has no third-party dependencies.

Public API:

* :func:`append` — write one event (a dict) as a single JSON line.
* :func:`read` — parse the whole ledger; returns valid records and any
  corrupted lines side by side.
* :func:`tail` — last ``n`` valid records in original order.
* :func:`filter_by_type` — valid records whose ``type`` field matches.

Records are returned as :class:`LedgerRecord`; bad lines as
:class:`CorruptLine`; both bundled into a :class:`ReadResult`.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "LedgerRecord",
    "CorruptLine",
    "ReadResult",
    "append",
    "read",
    "tail",
    "filter_by_type",
]


@dataclass(frozen=True)
class LedgerRecord:
    """A successfully parsed ledger record."""

    line_number: int
    payload: dict[str, Any]


@dataclass(frozen=True)
class CorruptLine:
    """A line that failed the ledger's basic integrity check."""

    line_number: int
    raw: str
    error: str


@dataclass(frozen=True)
class ReadResult:
    """Outcome of a full ledger read."""

    records: list[LedgerRecord] = field(default_factory=list)
    corrupt: list[CorruptLine] = field(default_factory=list)


def _to_path(path: str | os.PathLike[str]) -> Path:
    return path if isinstance(path, Path) else Path(os.fspath(path))


def append(path: str | os.PathLike[str], event: dict[str, Any]) -> None:
    """Append ``event`` to the ledger at ``path`` as one JSON line.

    Adds a ``ts`` (unix seconds, float) field if the caller did not
    supply one. Creates parent directories as needed.
    """
    if not isinstance(event, dict):
        raise TypeError(
            f"ledger.append requires a dict event, got {type(event).__name__}"
        )

    payload = dict(event)
    payload.setdefault("ts", time.time())

    line = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    target = _to_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def read(path: str | os.PathLike[str]) -> ReadResult:
    """Read every line of the ledger at ``path``.

    A missing file is treated as an empty ledger. Blank lines are
    silently skipped. Lines that fail JSON parsing, or that parse to
    something other than a JSON object, are collected into
    :attr:`ReadResult.corrupt` rather than raised.
    """
    target = _to_path(path)
    records: list[LedgerRecord] = []
    corrupt: list[CorruptLine] = []

    if not target.exists():
        return ReadResult(records=records, corrupt=corrupt)

    with target.open("r", encoding="utf-8") as fh:
        for idx, raw_line in enumerate(fh, start=1):
            stripped = raw_line.rstrip("\r\n")
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                corrupt.append(
                    CorruptLine(line_number=idx, raw=stripped, error=str(exc))
                )
                continue
            if not isinstance(payload, dict):
                corrupt.append(
                    CorruptLine(
                        line_number=idx,
                        raw=stripped,
                        error=(
                            "expected JSON object, "
                            f"got {type(payload).__name__}"
                        ),
                    )
                )
                continue
            records.append(LedgerRecord(line_number=idx, payload=payload))

    return ReadResult(records=records, corrupt=corrupt)


def tail(path: str | os.PathLike[str], n: int) -> list[LedgerRecord]:
    """Return the last ``n`` valid records in original order."""
    if n < 0:
        raise ValueError("tail count must be non-negative")
    if n == 0:
        return []
    return read(path).records[-n:]


def filter_by_type(
    path: str | os.PathLike[str], event_type: str
) -> list[LedgerRecord]:
    """Return valid records whose ``type`` field equals ``event_type``."""
    return [
        rec
        for rec in read(path).records
        if rec.payload.get("type") == event_type
    ]

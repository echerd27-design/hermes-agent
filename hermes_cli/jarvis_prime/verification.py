"""Local verification packet — structured evidence for JARVIS gates.

Records one entry per verification command (command string, working directory,
exit code, optional duration, summarized stdout/stderr, pass/fail/skipped
status, skip reason, artifacts, timestamp) and aggregates them into a packet
whose ``to_dict()`` / ``to_json()`` output is shaped to feed the JARVIS Test
Gate and Release Gate summaries described in
``docs/jarvis-verification-gates.md``.

This module does not execute commands. Callers run the work themselves
(directly or via a future runner) and pass the observed results in. Stdlib
only.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Optional

PASSED = "passed"
FAILED = "failed"
SKIPPED = "skipped"

_VALID_STATUSES = frozenset({PASSED, FAILED, SKIPPED})


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class VerificationEntry:
    """Evidence for a single verification command."""

    command: str
    cwd: str
    status: str
    exit_code: Optional[int] = None
    duration_seconds: Optional[float] = None
    stdout_summary: str = ""
    stderr_summary: str = ""
    skip_reason: Optional[str] = None
    artifacts: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if self.status not in _VALID_STATUSES:
            raise ValueError(
                f"status must be one of {sorted(_VALID_STATUSES)}, got {self.status!r}"
            )
        if self.status == SKIPPED and not self.skip_reason:
            raise ValueError("skipped entries require a non-empty skip_reason")
        if self.status != SKIPPED and self.skip_reason is not None:
            raise ValueError(
                "skip_reason is only allowed when status == 'skipped'"
            )
        if not self.timestamp:
            self.timestamp = _utc_now_iso()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VerificationPacket:
    """Ordered collection of VerificationEntry plus aggregation helpers."""

    entries: list[VerificationEntry] = field(default_factory=list)

    def add(self, entry: VerificationEntry) -> VerificationEntry:
        self.entries.append(entry)
        return entry

    def record(
        self,
        command: str,
        cwd: str,
        status: str,
        *,
        exit_code: Optional[int] = None,
        duration_seconds: Optional[float] = None,
        stdout_summary: str = "",
        stderr_summary: str = "",
        skip_reason: Optional[str] = None,
        artifacts: Optional[Iterable[str]] = None,
    ) -> VerificationEntry:
        entry = VerificationEntry(
            command=command,
            cwd=cwd,
            status=status,
            exit_code=exit_code,
            duration_seconds=duration_seconds,
            stdout_summary=stdout_summary,
            stderr_summary=stderr_summary,
            skip_reason=skip_reason,
            artifacts=list(artifacts) if artifacts else [],
        )
        return self.add(entry)

    def counts(self) -> dict[str, int]:
        out = {PASSED: 0, FAILED: 0, SKIPPED: 0}
        for entry in self.entries:
            out[entry.status] += 1
        return out

    def gate_result(self) -> str:
        """Aggregate result for the JARVIS Test Gate row.

        Returns ``"failed"`` if any entry failed, otherwise ``"passed"``. An
        empty packet or a skip-only packet returns ``"passed"``; whether that
        is acceptable for a given release is the caller's call — the Test Gate
        also requires "unverified risk is named", which lives in the wave
        report, not here.
        """
        for entry in self.entries:
            if entry.status == FAILED:
                return FAILED
        return PASSED

    def to_dict(self) -> dict:
        return {
            "entries": [entry.to_dict() for entry in self.entries],
            "counts": self.counts(),
            "gate_result": self.gate_result(),
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


def summarize_text(
    text: str, *, max_chars: int = 2000, marker: str = "…[truncated]…"
) -> str:
    """Return ``text`` unchanged if short; otherwise a head/tail snippet.

    Useful for filling ``stdout_summary`` / ``stderr_summary`` from a real
    command's output without dumping megabytes into the packet.
    """
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return f"{text[:half]}\n{marker}\n{text[-half:]}"

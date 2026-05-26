"""Review packet — the artifact a critic produces from a diff."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    """A single review observation about a diff."""

    severity: str
    path: str
    note: str


@dataclass(frozen=True)
class ReviewPacket:
    """A critic's structured response to a diff."""

    diff_ref: str
    findings: tuple[Finding, ...]
    blocking: tuple[str, ...]
    contrarian_note: str

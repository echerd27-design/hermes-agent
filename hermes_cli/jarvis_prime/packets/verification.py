"""Verification packet — record of gate-evidence commands and outcomes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationPacket:
    """The artifact a verifier records after running gate-evidence checks."""

    commands: tuple[str, ...]
    results: tuple[str, ...]
    skipped: tuple[tuple[str, str], ...]
    unverified_risk: str

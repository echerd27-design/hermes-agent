"""JARVIS Prime cross-surface session schema.

JARVIS Prime (see ``docs/jarvis-prime-operating-system.md``) is reachable from
CLI, Slack, Termux, Android, the gateway, and voice. A single logical session
must thread through those surfaces so that a voice conversation can resume in
Slack or Termux without losing the active job, the last mode, or ambient
metadata.

This module provides the data model only — no storage layer, no gateway
wiring. It is intentionally stdlib-only so it can be imported from any
surface adapter without dragging dependencies into the mobile / Termux paths.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional


class Surface(str, Enum):
    """Surfaces JARVIS Prime can be reached from.

    Subclassing ``str`` keeps the JSON form a plain string ("cli", "voice"…)
    so cross-surface payloads round-trip cleanly without a custom encoder.
    """

    CLI = "cli"
    SLACK = "slack"
    TERMUX = "termux"
    ANDROID = "android"
    GATEWAY = "gateway"
    VOICE = "voice"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc(ts: datetime) -> datetime:
    """Treat naive datetimes as UTC; otherwise convert to UTC.

    Deterministic id derivation requires a stable wire format for
    ``created_at``. Silently coercing naive inputs avoids gotchas where the
    same logical timestamp produces different ids depending on how the caller
    constructed the ``datetime``.
    """
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _iso(ts: datetime) -> str:
    return _to_utc(ts).isoformat()


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    return _to_utc(dt)


def derive_session_id(
    surface: str,
    user_id: Optional[str],
    created_at: datetime,
) -> str:
    """Deterministic session id from ``(surface, user_id, created_at)``.

    Uses UUID5 over ``uuid.NAMESPACE_DNS`` so identical inputs always yield
    the same id — handy when two surfaces independently materialize a session
    for the same logical conversation.
    """
    seed = f"jarvis-prime|{surface}|{user_id or ''}|{_iso(created_at)}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed))


def is_valid_session_id(value: Any) -> bool:
    """Return True if *value* is a parseable UUID string."""
    if not isinstance(value, str) or not value:
        return False
    try:
        uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    return True


@dataclass
class Session:
    """Cross-surface JARVIS Prime session state."""

    surface: str
    session_id: str = ""
    user_id: Optional[str] = None
    active_job_id: Optional[str] = None
    last_mode: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        try:
            self.surface = Surface(self.surface).value
        except ValueError as exc:
            valid = sorted(s.value for s in Surface)
            raise ValueError(
                f"invalid surface {self.surface!r}; expected one of {valid}"
            ) from exc

        self.created_at = _to_utc(self.created_at)
        self.updated_at = _to_utc(self.updated_at)

        if not self.session_id:
            self.session_id = derive_session_id(
                self.surface, self.user_id, self.created_at
            )
        elif not is_valid_session_id(self.session_id):
            raise ValueError(
                f"invalid session_id {self.session_id!r}; expected UUID string"
            )

    def touch(self) -> None:
        """Advance ``updated_at`` to now. Does not change ``session_id``."""
        self.updated_at = _utcnow()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "surface": self.surface,
            "user_id": self.user_id,
            "active_job_id": self.active_job_id,
            "last_mode": self.last_mode,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
            "metadata": dict(self.metadata),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Session":
        if "surface" not in data:
            raise ValueError("missing required field 'surface'")
        raw_metadata = data.get("metadata", {})
        if raw_metadata is None:
            raw_metadata = {}
        if not isinstance(raw_metadata, dict):
            raise ValueError("metadata must be a dict")

        created_raw = data.get("created_at")
        updated_raw = data.get("updated_at")

        return cls(
            session_id=str(data.get("session_id") or ""),
            surface=str(data["surface"]),
            user_id=data.get("user_id"),
            active_job_id=data.get("active_job_id"),
            last_mode=str(data.get("last_mode") or ""),
            created_at=_parse_iso(str(created_raw)) if created_raw else _utcnow(),
            updated_at=_parse_iso(str(updated_raw)) if updated_raw else _utcnow(),
            metadata=dict(raw_metadata),
        )

    @classmethod
    def from_json(cls, payload: str) -> "Session":
        return cls.from_dict(json.loads(payload))

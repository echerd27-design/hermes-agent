"""JARVIS Prime / Hermes orchestration event model (ACI Wave 08).

Defines the canonical event envelope used by JARVIS Prime modes,
orchestration workers, gates, and notification surfaces. The envelope
guarantees three properties:

1. Identity — every event carries a UUID, an ISO-8601 UTC timestamp,
   and a free-form ``source`` string.
2. JSON safety — the payload is recursively coerced to JSON-native
   types or rejected at emit time; ``from_dict`` re-runs the pass so
   untrusted input cannot smuggle non-serializable values.
3. Secret hygiene — values that look like credentials (by field name
   or by shape) are replaced with the literal string ``"[REDACTED]"``
   and the affected dotted paths are recorded on the event so
   consumers can tell which fields were scrubbed without seeing the
   secret.
"""

from __future__ import annotations

import json
import math
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any

REDACTED = "[REDACTED]"


class EventType(StrEnum):
    """Canonical event names for ACI Wave 08."""

    MESSAGE_RECEIVED = "message.received"
    MODE_CLASSIFIED = "mode.classified"
    ROUTE_SELECTED = "route.selected"
    MEMORY_RECALLED = "memory.recalled"
    TASK_CREATED = "task.created"
    WORKER_STARTED = "worker.started"
    WORKER_FINISHED = "worker.finished"
    GATE_FAILED = "gate.failed"
    OWNER_APPROVAL_REQUIRED = "owner.approval.required"
    TEST_FINISHED = "test.finished"
    PR_CREATED = "pr.created"
    NOTIFICATION_SENT = "notification.sent"
    MEMORY_SAVED = "memory.saved"


_VALID_TYPES: frozenset[str] = frozenset(t.value for t in EventType)


# Credential-shaped key-name suffixes. Mirrors tests/conftest.py so the
# emitter and the hermetic test harness agree on what "looks like a
# credential" without coupling either side to the other.
_CREDENTIAL_KEY_SUFFIXES: tuple[str, ...] = (
    "_API_KEY",
    "_TOKEN",
    "_SECRET",
    "_PASSWORD",
    "_CREDENTIALS",
    "_ACCESS_KEY",
    "_SECRET_ACCESS_KEY",
    "_PRIVATE_KEY",
    "_OAUTH_TOKEN",
    "_WEBHOOK_SECRET",
    "_ENCRYPT_KEY",
    "_APP_SECRET",
    "_CLIENT_SECRET",
    "_AES_KEY",
)

_CREDENTIAL_KEY_NAMES: frozenset[str] = frozenset({
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "auth_token",
    "session_token",
    "bearer",
    "authorization",
    "credentials",
    "private_key",
    "client_secret",
    "webhook_secret",
})

# Field names whose values look high-entropy but are not secrets
# (commit SHAs, content hashes, the event_id itself, etc.). These
# bypass the value-shape fallback redactor.
_REDACTION_ALLOWLIST_KEYS: frozenset[str] = frozenset({
    "event_id",
    "sha",
    "commit",
    "commit_sha",
    "hash",
    "digest",
    "checksum",
    "content_hash",
    "etag",
    "id",
    "uuid",
    "trace_id",
    "span_id",
    "request_id",
    "correlation_id",
})

# Value-shape regexes for known secret formats. The lookbehind in front
# of the bare ``sk-`` form avoids false matches inside longer tokens.
_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ASIA[0-9A-Z]{16}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(
        r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"
    ),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{20,}"),
    re.compile(r"-----BEGIN\s+[A-Z ]*PRIVATE KEY-----"),
)

# Generic high-entropy fallback. Length floor of 40 chars dodges
# routine identifiers while catching long opaque tokens. Only triggers
# when the field name is not on the allowlist above.
_HIGH_ENTROPY_PATTERN: re.Pattern[str] = re.compile(r"^[A-Za-z0-9+/=_\-]{40,}$")


def _make_json_safe(value: Any, *, path: str = "") -> Any:
    """Recursively coerce ``value`` to JSON-native types or raise.

    Allowed leaves: ``str``, ``int``, ``float`` (rejects NaN/Inf),
    ``bool``, ``None``. Auto-converted: ``datetime``/``date`` (ISO
    string), ``UUID``/``Path`` (``str``), :class:`enum.Enum` (its
    ``value``), ``set``/``frozenset``/``tuple`` (list). Anything else
    raises :class:`ValueError` naming the offending dotted path.
    """
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"non-finite float at {path or '<root>'}")
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return _make_json_safe(value.value, path=path)
    if isinstance(value, (list, tuple, set, frozenset)):
        return [
            _make_json_safe(v, path=f"{path}[{i}]") for i, v in enumerate(value)
        ]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise ValueError(
                    f"non-string dict key at {path or '<root>'}: {type(k).__name__}"
                )
            sub_path = f"{path}.{k}" if path else k
            out[k] = _make_json_safe(v, path=sub_path)
        return out
    raise ValueError(
        f"value of type {type(value).__name__} at {path or '<root>'} is not JSON-safe"
    )


def _is_secret_key(name: str) -> bool:
    """True if ``name`` looks like a credential-bearing field name."""
    upper = name.upper()
    for suf in _CREDENTIAL_KEY_SUFFIXES:
        if upper.endswith(suf) or upper == suf.lstrip("_"):
            return True
    return name.lower() in _CREDENTIAL_KEY_NAMES


def _value_looks_secret(value: str) -> bool:
    """True if ``value`` matches any known credential-shape regex."""
    return any(pat.search(value) for pat in _SECRET_VALUE_PATTERNS)


def _redact_secrets(
    value: Any, *, path: str = "", key_name: str = ""
) -> tuple[Any, list[str]]:
    """Walk a JSON-safe ``value``, returning a scrubbed copy and the
    list of dotted paths that were replaced with ``REDACTED``.
    """
    redacted: list[str] = []

    if isinstance(value, dict):
        out_d: dict[str, Any] = {}
        for k, v in value.items():
            sub_path = f"{path}.{k}" if path else k
            if _is_secret_key(k) and v not in (None, "", [], {}):
                out_d[k] = REDACTED
                redacted.append(sub_path)
                continue
            cleaned, sub_redacted = _redact_secrets(v, path=sub_path, key_name=k)
            out_d[k] = cleaned
            redacted.extend(sub_redacted)
        return out_d, redacted

    if isinstance(value, list):
        out_l: list[Any] = []
        for i, v in enumerate(value):
            sub_path = f"{path}[{i}]"
            cleaned, sub_redacted = _redact_secrets(
                v, path=sub_path, key_name=key_name
            )
            out_l.append(cleaned)
            redacted.extend(sub_redacted)
        return out_l, redacted

    if isinstance(value, str):
        if _value_looks_secret(value):
            return REDACTED, ([path] if path else [])
        if (
            key_name.lower() not in _REDACTION_ALLOWLIST_KEYS
            and _HIGH_ENTROPY_PATTERN.match(value)
        ):
            return REDACTED, ([path] if path else [])
        return value, []

    return value, []


@dataclass(frozen=True, slots=True)
class Event:
    """JSON-safe, secret-scrubbed event envelope.

    All five core fields are required. ``redactions`` records the
    dotted payload paths that were scrubbed during construction so
    downstream consumers can audit hygiene without seeing values.
    """

    event_id: str
    type: str
    timestamp: str
    source: str
    payload: dict[str, Any]
    redactions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, str) or not self.event_id:
            raise ValueError("event_id must be a non-empty string")
        if self.type not in _VALID_TYPES:
            raise ValueError(f"unknown event type: {self.type!r}")
        if not isinstance(self.timestamp, str) or not self.timestamp:
            raise ValueError("timestamp must be a non-empty ISO-8601 string")
        try:
            datetime.fromisoformat(self.timestamp)
        except ValueError as e:
            raise ValueError(
                f"timestamp is not ISO-8601: {self.timestamp!r}"
            ) from e
        if not isinstance(self.source, str) or not self.source:
            raise ValueError("source must be a non-empty string")
        if not isinstance(self.payload, dict):
            raise ValueError("payload must be a dict")

    @classmethod
    def new(
        cls,
        type: str | EventType,
        source: str,
        payload: dict[str, Any] | None = None,
        *,
        event_id: str | None = None,
        timestamp: str | None = None,
    ) -> Event:
        """Build a new event, auto-filling ``event_id`` and
        ``timestamp`` when not supplied. Runs the JSON-safety and
        secret-redaction passes before construction.
        """
        type_str = type.value if isinstance(type, EventType) else str(type)

        safe_payload = _make_json_safe(payload if payload is not None else {})
        if not isinstance(safe_payload, dict):
            raise ValueError("payload must serialize to a dict")
        scrubbed, redactions = _redact_secrets(safe_payload)

        return cls(
            event_id=event_id or uuid.uuid4().hex,
            type=type_str,
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            source=source,
            payload=scrubbed,
            redactions=tuple(redactions),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Event:
        """Strict deserializer. Re-runs JSON safety and redaction so
        untrusted input still gets scrubbed."""
        if not isinstance(data, dict):
            raise ValueError("from_dict expects a dict")
        for field_name in ("event_id", "type", "timestamp", "source", "payload"):
            if field_name not in data:
                raise ValueError(f"missing required field: {field_name}")

        payload = data["payload"]
        if not isinstance(payload, dict):
            raise ValueError("payload must be a dict")
        safe = _make_json_safe(payload)
        scrubbed, redactions = _redact_secrets(safe)

        provided = data.get("redactions")
        if provided is None:
            final_redactions: tuple[str, ...] = tuple(redactions)
        else:
            final_redactions = tuple(provided)

        return cls(
            event_id=str(data["event_id"]),
            type=str(data["type"]),
            timestamp=str(data["timestamp"]),
            source=str(data["source"]),
            payload=scrubbed,
            redactions=final_redactions,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a plain JSON-safe dict representation."""
        return {
            "event_id": self.event_id,
            "type": self.type,
            "timestamp": self.timestamp,
            "source": self.source,
            "payload": self.payload,
            "redactions": list(self.redactions),
        }

    def to_json(self) -> str:
        """Serialize to JSON with sorted keys for deterministic output."""
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)

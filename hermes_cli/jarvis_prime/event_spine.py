"""Jarvis Prime Event Spine — runtime contract module.

This module defines the on-the-wire and on-disk shape of every event that
Jarvis Prime producers (router, gateway, workers, scheduler) emit and every
consumer (Android body, audit log, dashboards, future broker) reads. It is
stdlib-only and intentionally un-wired: nothing else in the codebase imports
it yet. Subsequent waves will plug producers and consumers onto this
contract.

The contract has four parts:

1. ``EventType`` — 19 canonical event-type strings.
2. ``Event`` — a frozen dataclass envelope wrapping a JSON-safe payload.
3. ``validate_payload`` / ``_scan_for_secrets`` — strict producer-side
   validation. Secret-shaped values are rejected, never silently stored.
4. ``append_jsonl`` / ``read_jsonl`` — a deterministic line-delimited
   on-disk format for local audit and replay.

Plus ``render_mobile(event)`` — a compact single-line renderer for the
Android body's status surface.

See ``docs/aci/jarvis-prime/JARVIS_EVENT_SPINE_CONTRACT.md`` for the full
schema, producer/consumer cookbooks, and Android integration notes.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import math
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterator, Mapping

__all__ = [
    "EventType",
    "EVENT_TYPES",
    "Event",
    "EventSpineError",
    "InvalidPayloadError",
    "SecretInPayloadError",
    "UnknownEventTypeError",
    "SCHEMA_VERSION",
    "MAX_PAYLOAD_BYTES",
    "REDACTED_PLACEHOLDER",
    "new_event",
    "validate_payload",
    "redact_payload",
    "render_mobile",
    "append_jsonl",
    "read_jsonl",
]


SCHEMA_VERSION = 1
MAX_PAYLOAD_BYTES = 16 * 1024
REDACTED_PLACEHOLDER = "[REDACTED]"
_MOBILE_MAX_CHARS = 120


class EventType(str, Enum):
    """Canonical event-type identifiers.

    The 19 string values below are the contract. Adding, renaming, or
    removing any of them is a breaking change and requires bumping
    ``SCHEMA_VERSION``.
    """

    MESSAGE_RECEIVED = "jarvis.message.received"
    MESSAGE_RESPONDED = "jarvis.message.responded"
    PRESENCE_CHANGED = "jarvis.presence.changed"
    TASK_CREATED = "jarvis.task.created"
    TASK_PHASE_CHANGED = "jarvis.task.phase.changed"
    TASK_BLOCKED = "jarvis.task.blocked"
    TASK_COMPLETED = "jarvis.task.completed"
    WORKER_STARTED = "jarvis.worker.started"
    WORKER_FINISHED = "jarvis.worker.finished"
    APPROVAL_REQUESTED = "jarvis.approval.requested"
    APPROVAL_GRANTED = "jarvis.approval.granted"
    APPROVAL_DENIED = "jarvis.approval.denied"
    MEMORY_CREATED = "jarvis.memory.created"
    MEMORY_UPDATED = "jarvis.memory.updated"
    PROOF_CREATED = "jarvis.proof.created"
    NOTIFICATION_REQUESTED = "jarvis.notification.requested"
    EMERGENCY_STOP_TRIGGERED = "jarvis.emergency_stop.triggered"
    GATEWAY_CONNECTED = "jarvis.gateway.connected"
    GATEWAY_DISCONNECTED = "jarvis.gateway.disconnected"


EVENT_TYPES: frozenset[str] = frozenset(e.value for e in EventType)


class EventSpineError(ValueError):
    """Base class for all event-spine validation errors."""


class InvalidPayloadError(EventSpineError):
    """Payload failed JSON-safety or size validation."""


class SecretInPayloadError(EventSpineError):
    """Payload contained a secret-shaped value or key."""


class UnknownEventTypeError(EventSpineError):
    """Event type string is not a member of ``EventType``."""


_SECRET_KEY_NEEDLES: tuple[str, ...] = (
    "token",
    "api_key",
    "apikey",
    "password",
    "passwd",
    "secret",
    "bearer",
    "authorization",
    "auth",
    "session_key",
    "private_key",
    "client_secret",
    "refresh_token",
    "access_token",
)

_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"bearer\s+[A-Za-z0-9._\-]{16,}", re.IGNORECASE),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[abposr]-[A-Za-z0-9\-]{10,}"),
)


def _key_is_secret(key: str) -> bool:
    lowered = key.lower()
    return any(needle in lowered for needle in _SECRET_KEY_NEEDLES)


def _value_looks_secret(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return any(p.search(value) for p in _SECRET_VALUE_PATTERNS)


def _scan_for_secrets(node: Any, path: str) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            child_path = f"{path}.{k}" if path else k
            if isinstance(k, str) and _key_is_secret(k):
                raise SecretInPayloadError(
                    f"secret-shaped key at {child_path!s}"
                )
            _scan_for_secrets(v, child_path)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            _scan_for_secrets(item, f"{path}[{i}]")
    elif _value_looks_secret(node):
        raise SecretInPayloadError(
            f"secret-shaped value at {path!s}"
        )


def _normalize_and_check_types(node: Any, path: str) -> Any:
    if isinstance(node, bool):
        return node
    if node is None or isinstance(node, (str, int)):
        return node
    if isinstance(node, float):
        if not math.isfinite(node):
            raise InvalidPayloadError(
                f"non-finite float at {path!s}"
            )
        return node
    if isinstance(node, (list, tuple)):
        return [
            _normalize_and_check_types(item, f"{path}[{i}]")
            for i, item in enumerate(node)
        ]
    if isinstance(node, dict):
        normalized: dict[str, Any] = {}
        for k, v in node.items():
            if not isinstance(k, str):
                raise InvalidPayloadError(
                    f"non-string key at {path or '<root>'}: {type(k).__name__}"
                )
            child_path = f"{path}.{k}" if path else k
            normalized[k] = _normalize_and_check_types(v, child_path)
        return normalized
    raise InvalidPayloadError(
        f"unsupported type {type(node).__name__} at {path or '<root>'}"
    )


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize a payload.

    Returns a freshly-built dict with tuples converted to lists. Raises
    ``InvalidPayloadError`` for JSON-incompatible types, non-finite floats,
    non-string dict keys, or oversize payloads. Raises
    ``SecretInPayloadError`` if any key name or string value looks like a
    secret. The error message names the key path but never the matched
    value.
    """
    if not isinstance(payload, dict):
        raise InvalidPayloadError(
            f"payload must be a dict, got {type(payload).__name__}"
        )
    normalized = _normalize_and_check_types(payload, "")
    _scan_for_secrets(normalized, "")
    encoded = json.dumps(normalized, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise InvalidPayloadError(
            f"payload exceeds MAX_PAYLOAD_BYTES ({MAX_PAYLOAD_BYTES})"
        )
    return normalized


def _redact_walk(node: Any) -> Any:
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        for k, v in node.items():
            if isinstance(k, str) and _key_is_secret(k):
                out[k] = REDACTED_PLACEHOLDER
            elif _value_looks_secret(v):
                out[k] = REDACTED_PLACEHOLDER
            else:
                out[k] = _redact_walk(v)
        return out
    if isinstance(node, list):
        return [
            REDACTED_PLACEHOLDER if _value_looks_secret(item) else _redact_walk(item)
            for item in node
        ]
    if _value_looks_secret(node):
        return REDACTED_PLACEHOLDER
    return node


def redact_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deep copy of ``payload`` with secret-shaped values masked.

    Detection logic matches ``validate_payload`` but the behavior is
    non-destructive: matches become ``REDACTED_PLACEHOLDER``. Intended for
    audit-side tooling that ingests already-validated events; producers
    should pre-scrub their data rather than rely on this helper.
    """
    if not isinstance(payload, dict):
        raise InvalidPayloadError(
            f"payload must be a dict, got {type(payload).__name__}"
        )
    return _redact_walk(copy.deepcopy(payload))


_VALID_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "id",
        "type",
        "ts",
        "source",
        "actor",
        "subject",
        "correlation_id",
        "schema_version",
        "payload",
    }
)


@dataclass(frozen=True, slots=True)
class Event:
    """A single Jarvis Prime event.

    Construct via :func:`new_event` (which fills in ``id`` and ``ts``) or
    directly when reconstructing from wire bytes via :meth:`from_dict`.
    ``__post_init__`` runs the full validation chain — any direct
    construction with bad data raises immediately.

    The ``payload`` dict is stored as-is; the contract treats it as
    immutable. Callers should never mutate it after construction.
    """

    id: str
    type: str
    ts: str
    source: str
    actor: str | None = None
    subject: str | None = None
    correlation_id: str | None = None
    schema_version: int = SCHEMA_VERSION
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id:
            raise InvalidPayloadError("id must be a non-empty string")
        if not isinstance(self.type, str):
            raise UnknownEventTypeError(
                f"type must be a string, got {type(self.type).__name__}"
            )
        if self.type not in EVENT_TYPES:
            raise UnknownEventTypeError(f"unknown event type: {self.type!r}")
        if not isinstance(self.ts, str) or not self.ts:
            raise InvalidPayloadError("ts must be a non-empty string")
        if not isinstance(self.source, str) or not self.source:
            raise InvalidPayloadError("source must be a non-empty string")
        if self.actor is not None and not isinstance(self.actor, str):
            raise InvalidPayloadError("actor must be a string or None")
        if self.subject is not None and not isinstance(self.subject, str):
            raise InvalidPayloadError("subject must be a string or None")
        if self.correlation_id is not None and not isinstance(self.correlation_id, str):
            raise InvalidPayloadError("correlation_id must be a string or None")
        if not isinstance(self.schema_version, int) or isinstance(self.schema_version, bool):
            raise InvalidPayloadError("schema_version must be an int")
        if self.schema_version < 1:
            raise InvalidPayloadError("schema_version must be >= 1")
        if self.schema_version > SCHEMA_VERSION:
            raise EventSpineError(
                f"schema_version {self.schema_version} exceeds known SCHEMA_VERSION {SCHEMA_VERSION}"
            )
        validate_payload(self.payload)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dict view (payload deep-copied)."""
        return {
            "id": self.id,
            "type": self.type,
            "ts": self.ts,
            "source": self.source,
            "actor": self.actor,
            "subject": self.subject,
            "correlation_id": self.correlation_id,
            "schema_version": self.schema_version,
            "payload": copy.deepcopy(self.payload),
        }

    def to_json(self) -> str:
        """Return a deterministic UTF-8 JSON string (sorted keys, compact)."""
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Event":
        """Rebuild an Event from a wire dict, re-running every check."""
        if not isinstance(data, dict):
            raise InvalidPayloadError(
                f"from_dict requires a dict, got {type(data).__name__}"
            )
        unknown = set(data.keys()) - _VALID_FIELD_NAMES
        if unknown:
            raise InvalidPayloadError(
                f"unknown top-level keys: {sorted(unknown)!r}"
            )
        for required in ("id", "type", "ts", "source"):
            if required not in data:
                raise InvalidPayloadError(f"missing required field: {required!r}")
        return cls(
            id=data["id"],
            type=data["type"],
            ts=data["ts"],
            source=data["source"],
            actor=data.get("actor"),
            subject=data.get("subject"),
            correlation_id=data.get("correlation_id"),
            schema_version=data.get("schema_version", SCHEMA_VERSION),
            payload=dict(data.get("payload") or {}),
        )

    @classmethod
    def from_json(cls, raw: str) -> "Event":
        """Parse a single JSON string into an Event."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise InvalidPayloadError(f"invalid JSON: {exc.msg}") from exc
        return cls.from_dict(data)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def new_event(
    type: str | EventType,
    *,
    source: str,
    payload: Mapping[str, Any] | None = None,
    actor: str | None = None,
    subject: str | None = None,
    correlation_id: str | None = None,
    id: str | None = None,
    ts: str | None = None,
) -> Event:
    """Construct a fully-validated :class:`Event`.

    ``type`` may be an :class:`EventType` member or its string value.
    ``id`` defaults to a UUIDv4 hex (32 chars); ``ts`` defaults to the
    current UTC instant formatted as ``YYYY-MM-DDTHH:MM:SS.ffffffZ``.
    All other validations run via :meth:`Event.__post_init__`.
    """
    type_value = type.value if isinstance(type, EventType) else type
    return Event(
        id=id if id is not None else uuid.uuid4().hex,
        type=type_value,
        ts=ts if ts is not None else _utc_now_iso(),
        source=source,
        actor=actor,
        subject=subject,
        correlation_id=correlation_id,
        schema_version=SCHEMA_VERSION,
        payload=dict(payload or {}),
    )


_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")


def _short_type(type_value: str) -> str:
    return type_value[len("jarvis."):] if type_value.startswith("jarvis.") else type_value


def _hh_mm_ss(ts: str) -> str:
    # ts is ISO-8601 with 'T' separator; the time portion's first 8 chars are HH:MM:SS.
    if "T" in ts:
        time_part = ts.split("T", 1)[1]
        return time_part[:8] if len(time_part) >= 8 else time_part
    return ts[:8]


def _hint_for(event: Event) -> str:
    p = event.payload
    t = event.type
    if t == EventType.MESSAGE_RECEIVED.value:
        preview = str(p.get("preview", ""))[:40]
        return preview
    if t == EventType.MESSAGE_RESPONDED.value:
        return str(p.get("preview", ""))[:40]
    if t == EventType.PRESENCE_CHANGED.value:
        return str(p.get("state", ""))
    if t in (EventType.TASK_CREATED.value, EventType.TASK_PHASE_CHANGED.value):
        title = str(p.get("title", ""))
        phase = str(p.get("phase", ""))
        if title and phase:
            return f"{title} :: {phase}"
        return title or phase
    if t == EventType.TASK_BLOCKED.value:
        return str(p.get("reason", ""))
    if t == EventType.TASK_COMPLETED.value:
        return str(p.get("title", ""))
    if t == EventType.WORKER_STARTED.value:
        return str(p.get("worker", ""))
    if t == EventType.WORKER_FINISHED.value:
        worker = str(p.get("worker", ""))
        dur = p.get("duration_ms")
        if worker and isinstance(dur, (int, float)):
            return f"{worker} ({int(dur)}ms)"
        return worker
    if t == EventType.APPROVAL_REQUESTED.value:
        return str(p.get("summary", ""))
    if t in (EventType.APPROVAL_GRANTED.value, EventType.APPROVAL_DENIED.value):
        return str(p.get("decision", "")) or str(p.get("summary", ""))
    if t in (EventType.MEMORY_CREATED.value, EventType.MEMORY_UPDATED.value):
        return str(p.get("title", "")) or str(p.get("key", ""))
    if t == EventType.PROOF_CREATED.value:
        return str(p.get("kind", "")) or str(p.get("title", ""))
    if t == EventType.NOTIFICATION_REQUESTED.value:
        return str(p.get("text", ""))
    if t == EventType.EMERGENCY_STOP_TRIGGERED.value:
        return str(p.get("reason", ""))
    if t in (EventType.GATEWAY_CONNECTED.value, EventType.GATEWAY_DISCONNECTED.value):
        return str(p.get("gateway", ""))
    return ""


def render_mobile(event: Event) -> str:
    """Render an :class:`Event` as a single line for the Android body.

    Format: ``"[HH:MM:SS short.type] subject — hint"``. Always ≤ 120 chars,
    no newlines, control characters stripped. ``short.type`` is the event
    type with the ``jarvis.`` prefix removed. The hint extractor reads
    well-known payload keys per event type; unknown types render with an
    empty hint.
    """
    if not isinstance(event, Event):
        raise TypeError(f"render_mobile requires an Event, got {type(event).__name__}")
    head = f"[{_hh_mm_ss(event.ts)} {_short_type(event.type)}]"
    subject = event.subject or ""
    hint = _hint_for(event)
    parts = [head]
    if subject:
        parts.append(subject)
    if hint:
        parts.append(f"— {hint}")
    line = " ".join(parts)
    line = _CONTROL_CHARS_RE.sub(" ", line)
    if len(line) > _MOBILE_MAX_CHARS:
        line = line[: _MOBILE_MAX_CHARS - 1] + "…"
    return line


def append_jsonl(path: str | os.PathLike[str], event: Event) -> None:
    """Append a single event as one JSON line to ``path``.

    Creates parent directories as needed. Writes one ``event.to_json()``
    line followed by a single newline. **Single-writer-per-file
    contract** — there is no advisory lock and no ``fsync``. Multiple
    writers against the same file may interleave on lines larger than
    POSIX ``PIPE_BUF`` (~4 KB). For a stronger durability or
    concurrency story, layer a separate writer on top.
    """
    if not isinstance(event, Event):
        raise TypeError(f"append_jsonl requires an Event, got {type(event).__name__}")
    p = Path(os.fspath(path))
    p.parent.mkdir(parents=True, exist_ok=True)
    line = (event.to_json() + "\n").encode("utf-8")
    with open(p, "ab") as f:
        f.write(line)


def read_jsonl(path: str | os.PathLike[str]) -> Iterator[Event]:
    """Yield each :class:`Event` from a JSONL file.

    Empty lines are skipped. Each non-empty line is re-validated through
    :meth:`Event.from_json` — corrupt or non-conforming lines raise
    :class:`InvalidPayloadError` (the caller decides whether to skip or
    abort by wrapping the iteration).
    """
    p = Path(os.fspath(path))
    with open(p, "rb") as f:
        for raw in f:
            stripped = raw.strip()
            if not stripped:
                continue
            yield Event.from_json(stripped.decode("utf-8"))

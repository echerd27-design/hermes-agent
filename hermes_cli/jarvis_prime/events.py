"""Event bus — in-memory deque of structured events.

Future wave PRs replace the in-memory deque with a durable event log
(e.g. ``~/.hermes/jarvis/events.jsonl`` + a watcher); the Event dataclass
and ``emit`` signature keep their shape.
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventKind(str, Enum):
    """Categories of event JARVIS Prime emits."""

    ROUTED = "routed"
    GATED = "gated"
    PACKET_BUILT = "packet_built"
    SURFACE_RENDERED = "surface_rendered"
    LEDGER_APPENDED = "ledger_appended"


@dataclass(frozen=True)
class Event:
    """A structured signal emitted during routing."""

    id: str
    kind: EventKind
    ts: float
    payload: Mapping[str, Any] = field(default_factory=dict)


_EVENTS: deque[Event] = deque(maxlen=1024)


def emit(kind: EventKind, payload: Mapping[str, Any] | None = None) -> Event:
    """Append an event and return the persisted record."""
    ev = Event(
        id=f"evt-{len(_EVENTS):06d}",
        kind=kind,
        ts=time.time(),
        payload=dict(payload or {}),
    )
    _EVENTS.append(ev)
    return ev


def tail(n: int = 10) -> tuple[Event, ...]:
    """Return the most recent ``n`` events (oldest-first)."""
    if n <= 0:
        return ()
    return tuple(list(_EVENTS)[-n:])

"""JARVIS Prime / Hermes orchestration package (introduced in ACI Wave 08).

The package exposes the canonical :class:`Event` envelope and the
:class:`EventType` enum used by JARVIS Prime modes, orchestration
workers, gates, and notification surfaces.
"""

from .events import Event, EventType

__all__ = ["Event", "EventType"]

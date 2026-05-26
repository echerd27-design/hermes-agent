"""AOS Council request/response schema.

Encodes the contract for handoff between JARVIS Prime and the AOS Council
tier (see ``docs/aos-jarvis-agent-routing.md``). Today these dataclasses
are returned from stubs; future wave PRs wire them to the real council
director without changing the shape.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .specialists import Specialist


@dataclass(frozen=True)
class CouncilRequest:
    """Request handed from JARVIS Prime to the AOS Council tier."""

    mission_id: str
    mission_text: str
    specialists: tuple[Specialist, ...]
    context: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CouncilResponse:
    """Decision returned by the AOS Council tier."""

    mission_id: str
    decision: str
    rationale: str
    blockers: tuple[str, ...] = ()


@dataclass(frozen=True)
class SpecialistRequest:
    """Dispatch payload handed from the council to a single specialist."""

    mission_id: str
    specialist: Specialist
    scope: str
    inputs: Mapping[str, Any] = field(default_factory=dict)

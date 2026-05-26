"""JARVIS Prime mode enum.

Mirrors the six modes defined in ``skills/jarvis-prime/SKILL.md``, plus an
``AUTO`` sentinel used when the entry slash command is ``/jarvis``,
``/jp``, or ``/jarvis-prime`` and the mode should be resolved by
``ModeClassifier`` against the payload.
"""

from __future__ import annotations

from enum import Enum


class Mode(str, Enum):
    COMPANION = "companion"
    STRATEGY = "strategy"
    CRITIC = "critic"
    OPERATOR = "operator"
    BUILDER = "builder"
    MOBILE_VOICE = "mobile-voice"
    AUTO = "auto"


NAMED_MODES: tuple[Mode, ...] = (
    Mode.COMPANION,
    Mode.STRATEGY,
    Mode.CRITIC,
    Mode.OPERATOR,
    Mode.BUILDER,
    Mode.MOBILE_VOICE,
)

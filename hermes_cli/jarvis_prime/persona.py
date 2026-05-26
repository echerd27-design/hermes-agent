"""JARVIS Prime persona headers and response format constants.

The two format blocks below are quoted verbatim from
``skills/jarvis-prime/SKILL.md`` (the "Default response format" and
"Operational handoff format" sections). Keeping them here in code
guarantees the CLI adapter never drifts from the skill spec.
"""

from __future__ import annotations

from dataclasses import dataclass

from .modes import Mode


DEFAULT_RESPONSE_FORMAT = (
    "1. What I hear you saying\n"
    "2. My honest take\n"
    "3. What I agree with\n"
    "4. What I disagree with\n"
    "5. Strongest path forward\n"
    "6. Next action"
)

OPERATIONAL_HANDOFF_FORMAT = (
    "Mission:\n"
    "Route selected:\n"
    "Actions taken:\n"
    "Verification:\n"
    "Owner gates:\n"
    "Result:\n"
    "Next step:"
)


_HEADERS: dict[Mode, str] = {
    Mode.COMPANION: "JARVIS Prime — Companion Mode (grounded, emotionally intelligent, honest).",
    Mode.STRATEGY: "JARVIS Prime — Strategy Mode (highest-leverage path, name the tradeoff).",
    Mode.CRITIC: "JARVIS Prime — Critic Mode (contrarian; name the strongest objection).",
    Mode.OPERATOR: "JARVIS Prime — Operator Mode (route, plan, coordinate, hand off).",
    Mode.BUILDER: "JARVIS Prime — Builder Mode (repo work, plan, verify, PR-ready).",
    Mode.MOBILE_VOICE: "JARVIS Prime — Mobile Voice Mode (capture short, expand later).",
}


def header_for(mode: Mode) -> str:
    if mode is Mode.AUTO:
        raise ValueError("AUTO has no persona header; resolve it via ModeClassifier first.")
    return _HEADERS[mode]


@dataclass(frozen=True)
class Persona:
    name: str
    mode: Mode
    header: str

    @classmethod
    def for_mode(cls, mode: Mode) -> "Persona":
        return cls(name="JARVIS Prime", mode=mode, header=header_for(mode))

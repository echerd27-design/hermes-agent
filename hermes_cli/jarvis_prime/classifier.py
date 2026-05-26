"""ModeClassifier — keyword heuristic mapping free-text to a JARVIS mode.

Intentionally heuristic only (no LLM, no external dependencies) so it can
run in any environment. The CLI adapter's job is to land in the right
mode; the downstream prompt/handler is responsible for the actual
reasoning.
"""

from __future__ import annotations

import re

from .modes import Mode


_PATTERNS: tuple[tuple[Mode, re.Pattern[str]], ...] = (
    (Mode.MOBILE_VOICE, re.compile(
        r"\b(voice|jog(ging)?|walking|driving|mobile|on\s+the\s+move|on\s+the\s+go)\b",
        re.IGNORECASE,
    )),
    (Mode.BUILDER, re.compile(
        r"\b(code|build|ship|repo|commit|pr\b|pull\s+request|merge|branch|refactor|implement|diff|patch|test)\b",
        re.IGNORECASE,
    )),
    (Mode.OPERATOR, re.compile(
        r"\b(route|task|github\s+issue|slack|termux|aos|coordinate|hand[-\s]?off|workflow|orchestrate)\b",
        re.IGNORECASE,
    )),
    (Mode.STRATEGY, re.compile(
        r"\b(pricing|positioning|career|roadmap|strategy|tradeoff|leverage|investor|promotion|market)\b",
        re.IGNORECASE,
    )),
    (Mode.CRITIC, re.compile(
        r"\b(disagree|critique|critic|flaw|weak|risk|wrong|push\s+back|red[-\s]?team|contrarian|blind\s+spot)\b",
        re.IGNORECASE,
    )),
    (Mode.COMPANION, re.compile(
        r"\b(feel|feeling|tired|stressed|anxious|talk|vent|lonely|burn(ed)?\s*out|support)\b",
        re.IGNORECASE,
    )),
)


class ModeClassifier:
    def classify(self, text: str) -> Mode:
        if text is None:
            return Mode.COMPANION
        stripped = text.strip()
        if not stripped:
            return Mode.COMPANION
        for mode, pattern in _PATTERNS:
            if pattern.search(stripped):
                return mode
        return Mode.COMPANION

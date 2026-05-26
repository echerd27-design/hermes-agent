"""JARVIS Prime mode classifier.

Deterministic, stdlib-only keyword scoring that maps a free-form ACI
command to one of the five operating modes the Wave 01 acceptance
criteria names: Companion, Strategy, Critic, Builder, Mobile Voice.

The JARVIS Prime doc (``docs/jarvis-prime-operating-system.md``) lists
six modes including Operator, but per user direction during Wave 01
planning the Operator surface is folded into Builder (routing,
specialist activation, surface coordination) and Strategy (owner-gate
decisions). The Classification result still exposes a ``specialists``
tuple so callers can activate HazMat / Nourish / Logistics workflows
alongside the chosen Builder/Strategy mode.

Scoring model:

1. Normalize the input (lowercase, strip punctuation, collapse whitespace).
2. Phrase pass: each multi-word phrase that fires contributes its
   per-phrase weight (3 by default, 6 for high-signal "override" phrases
   such as red-team triggers).
3. Token pass: each single-word vocabulary hit contributes weight 1.
4. Specialist extraction: HazMat / Nourish / Logistics triggers are
   recorded in ``Classification.specialists`` and nudge Builder by 1.
5. Mobile-voice guard: the Mobile Voice score is reset to 0 unless an
   explicit voice/movement surface phrase fired. Slack, Termux, and
   Android-only do NOT count as mobile-voice surfaces.
6. Tie-break order (highest priority first):
   MOBILE_VOICE -> BUILDER -> CRITIC -> STRATEGY -> COMPANION.
7. If every mode scores 0, return Companion.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum


class Mode(str, Enum):
    COMPANION = "companion"
    STRATEGY = "strategy"
    CRITIC = "critic"
    BUILDER = "builder"
    MOBILE_VOICE = "mobile_voice"


_TIE_BREAK_PRIORITY: tuple[Mode, ...] = (
    Mode.MOBILE_VOICE,
    Mode.BUILDER,
    Mode.CRITIC,
    Mode.STRATEGY,
    Mode.COMPANION,
)


_TOKEN_WEIGHT = 1
_SPECIALIST_BUILDER_BONUS = 1


_PHRASES: dict[Mode, dict[str, int]] = {
    Mode.BUILDER: {
        # Repo / code-handoff phrases.
        "audit repo": 3,
        "fix build": 3,
        "open pr": 3,
        "open draft pr": 3,
        "draft pr": 3,
        "review pr": 3,
        "use claude": 3,
        "use codex": 3,
        "claude code": 3,
        "codex review": 3,
        "ship it": 3,
        "merge pr": 3,
        "android only": 3,
        "run tests": 3,
        "bounded fix": 3,
        "rebase main": 3,
        # Routing / coordination phrases (Operator-style, folded in).
        "route through aos": 3,
        "use the council": 3,
        "activate the council": 3,
        "hazmat command": 3,
        "task packet": 3,
        "slack mobile": 3,
        "dispatch worker": 3,
    },
    Mode.STRATEGY: {
        "launch blockers": 3,
        "go to market": 3,
        "go-to-market": 3,
        "business decision": 3,
        "monetization plan": 3,
        "investor pitch": 3,
        "growth strategy": 3,
        "pricing tier": 3,
        # Readiness-as-business-call (Strategy-heavy bias).
        "production ready": 3,
        # Owner gates are decision-making moments.
        "owner approval": 3,
    },
    Mode.CRITIC: {
        # High-signal red-team / contrarian phrases: weight 6 so they
        # outrank a single co-occurring strategy or builder phrase.
        "red team": 6,
        "red-team": 6,
        "tear apart": 6,
        "challenge this": 6,
        "devil's advocate": 6,
        "devils advocate": 6,
        "stress test": 6,
        # Regular Critic phrases.
        "weak assumption": 3,
        "what is wrong": 3,
        "what's wrong": 3,
        "fatal flaw": 3,
    },
    Mode.MOBILE_VOICE: {
        "hey jay": 3,
        "voice note": 3,
        "voice capture": 3,
        "mobile voice": 3,
        "on my phone": 3,
        "from my phone": 3,
        "while jogging": 3,
        "while walking": 3,
        "while driving": 3,
        "while moving": 3,
        "on the move": 3,
    },
    Mode.COMPANION: {},
}


_TOKENS: dict[Mode, frozenset[str]] = {
    Mode.BUILDER: frozenset({
        # Core repo / code tokens.
        "pr", "repo", "build", "refactor", "lint", "ci",
        "commit", "branch", "diff", "test", "tests", "audit",
        "implement", "compile", "package",
        # Routing / surface / specialist tokens (Operator folded in).
        "route", "dispatch", "ticket", "issue", "packet",
        "slack", "termux", "aos", "council", "specialist",
        "hazmat", "nourish", "logistics",
    }),
    Mode.STRATEGY: frozenset({
        "strategy", "monetize", "pricing", "market", "customer",
        "growth", "positioning", "roadmap", "revenue",
    }),
    Mode.CRITIC: frozenset({
        "critique", "contrarian", "risks", "weaknesses", "flaws",
        "assumptions", "objections", "unsafe",
    }),
    Mode.MOBILE_VOICE: frozenset({
        "voice", "jogging", "walking", "driving", "commute",
    }),
    Mode.COMPANION: frozenset(),
}


# Narrow surface set. Slack / Termux / Android-only are NOT here on
# purpose: the brief says no false route to mobile_voice unless an
# explicit mobile/voice surface signal is present.
_MOBILE_VOICE_SURFACE_PHRASES: tuple[str, ...] = (
    "hey jay",
    "voice note",
    "voice capture",
    "mobile voice",
    "on my phone",
    "from my phone",
    "while jogging",
    "while walking",
    "while driving",
    "while moving",
    "on the move",
)
_MOBILE_VOICE_SURFACE_TOKENS: frozenset[str] = frozenset({
    "voice", "jogging", "walking", "driving", "commute",
})


_SPECIALIST_TRIGGERS: dict[str, tuple[str, ...]] = {
    "hazmat": (
        "hazmat",
        "hazmat command",
        "49 cfr",
        "erg",
        "placarding",
        "shipping papers",
    ),
    "nourish": (
        "nourish",
        "meal log",
        "recipe",
        "nutrition data",
        "nutrient math",
    ),
    "logistics": (
        "logistics",
        "fleet",
        "carrier",
        "ltl",
    ),
}


@dataclass
class Classification:
    mode: Mode
    scores: Mapping[Mode, int]
    matched: Mapping[Mode, tuple[str, ...]]
    specialists: tuple[str, ...] = field(default_factory=tuple)


_PUNCT_RE = re.compile(r"[^a-z0-9\s'-]+")
_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    if not text:
        return ""
    lowered = text.lower()
    cleaned = _PUNCT_RE.sub(" ", lowered)
    return _WS_RE.sub(" ", cleaned).strip()


def _phrase_hit(normalized: str, phrase: str) -> bool:
    """True iff ``phrase`` appears as a whole-word run in ``normalized``."""
    if not phrase or not normalized:
        return False
    return f" {phrase} " in f" {normalized} "


def classify(text: str) -> Classification:
    normalized = _normalize(text)
    tokens = normalized.split() if normalized else []
    token_set = set(tokens)

    scores: dict[Mode, int] = {mode: 0 for mode in Mode}
    matched: dict[Mode, list[str]] = {mode: [] for mode in Mode}

    # Phrase pass.
    for mode, phrases in _PHRASES.items():
        for phrase, weight in phrases.items():
            if _phrase_hit(normalized, phrase):
                scores[mode] += weight
                matched[mode].append(phrase)

    # Token pass.
    for mode, vocabulary in _TOKENS.items():
        for token in sorted(token_set & vocabulary):
            scores[mode] += _TOKEN_WEIGHT
            matched[mode].append(token)

    # Specialist extraction (nudges Builder by a small amount).
    specialists: list[str] = []
    for spec, triggers in _SPECIALIST_TRIGGERS.items():
        for trigger in triggers:
            hit = (
                _phrase_hit(normalized, trigger)
                if " " in trigger
                else trigger in token_set
            )
            if hit:
                if spec not in specialists:
                    specialists.append(spec)
                    scores[Mode.BUILDER] += _SPECIALIST_BUILDER_BONUS
                    matched[Mode.BUILDER].append(f"specialist:{spec}")
                break

    # Mobile-voice guard.
    mobile_surface_hit = any(
        _phrase_hit(normalized, p) for p in _MOBILE_VOICE_SURFACE_PHRASES
    ) or bool(token_set & _MOBILE_VOICE_SURFACE_TOKENS)
    if not mobile_surface_hit:
        scores[Mode.MOBILE_VOICE] = 0
        matched[Mode.MOBILE_VOICE] = []

    # Pick winner.
    top_score = max(scores.values())
    if top_score == 0:
        winner = Mode.COMPANION
    else:
        winner = next(
            mode for mode in _TIE_BREAK_PRIORITY if scores[mode] == top_score
        )

    return Classification(
        mode=winner,
        scores={mode: scores[mode] for mode in Mode},
        matched={mode: tuple(matched[mode]) for mode in Mode},
        specialists=tuple(specialists),
    )


def classify_mode(text: str) -> Mode:
    return classify(text).mode


__all__ = ["Mode", "Classification", "classify", "classify_mode"]

"""Tests for the JARVIS Prime mode classifier (Wave 01)."""

from __future__ import annotations

import pytest

from hermes_cli.jarvis_prime.modes import Classification, Mode, classify, classify_mode


# ---------------------------------------------------------------------------
# Suite 1: Real-world ACI commands (>= 30 cases).
#
# Covers all 16 commands named in the Wave 01 brief plus 17 supplemental
# cases to exercise tie-breaks, defaults, specialist co-mention, and
# tricky overlaps. The classifier exposes 5 modes (Operator was folded
# into Builder + Strategy per the Strategy-heavy direction); specialist
# activations are surfaced separately via Classification.specialists.
# ---------------------------------------------------------------------------

REAL_WORLD_CASES: list[tuple[str, Mode]] = [
    ("audit repo", Mode.BUILDER),
    ("launch blockers", Mode.STRATEGY),
    ("fix build", Mode.BUILDER),
    ("use Claude to refactor the gateway", Mode.BUILDER),
    ("use Codex to review this diff", Mode.BUILDER),
    ("review PR 482", Mode.BUILDER),
    ("open draft PR for the modes change", Mode.BUILDER),
    ("Android only release scope", Mode.BUILDER),
    ("kick the job from Termux later", Mode.BUILDER),
    ("respond on Slack with the summary", Mode.BUILDER),
    ("owner approval for DNS change", Mode.STRATEGY),
    ("is the HazMat skill production ready?", Mode.STRATEGY),
    ("route through AOS for architecture review", Mode.BUILDER),
    ("HazMat Command pre-flight", Mode.BUILDER),
    ("Nourish meal log schema review", Mode.BUILDER),
    ("Hey Jay capture this idea", Mode.MOBILE_VOICE),
    ("while jogging, remind me to fix the build", Mode.MOBILE_VOICE),
    ("red team this monetization plan", Mode.CRITIC),
    ("tear apart the pricing tier idea", Mode.CRITIC),
    ("what is the growth strategy here", Mode.STRATEGY),
    ("positioning for trucking dispatchers", Mode.STRATEGY),
    ("I feel stuck on this", Mode.COMPANION),
    ("hey, how's the day?", Mode.COMPANION),
    ("", Mode.COMPANION),
    ("run tests and report diff", Mode.BUILDER),
    ("voice note: rework the modes table", Mode.MOBILE_VOICE),
    ("ship it after the lint pass", Mode.BUILDER),
    ("investor pitch outline for HazMat", Mode.STRATEGY),
    ("challenge this assumption: PRs auto-merge", Mode.CRITIC),
    ("from my phone -- audit later", Mode.MOBILE_VOICE),
    ("stress test the council routing", Mode.CRITIC),
    ("rebase main and run tests", Mode.BUILDER),
    ("activate the council for release readiness", Mode.BUILDER),
]


@pytest.mark.parametrize("command,expected", REAL_WORLD_CASES, ids=[c for c, _ in REAL_WORLD_CASES])
def test_real_world_aci_commands(command: str, expected: Mode) -> None:
    result = classify(command)
    assert result.mode is expected, (
        f"command={command!r} expected={expected} got={result.mode} "
        f"scores={dict(result.scores)} matched={dict(result.matched)}"
    )


def test_corpus_meets_minimum_size() -> None:
    """Wave 01 acceptance requires at least 30 example ACI commands."""
    assert len(REAL_WORLD_CASES) >= 30


# ---------------------------------------------------------------------------
# Suite 2: Mobile-voice guard.
#
# Slack / Termux / Android-only / owner approval / draft PR alone must
# NEVER classify as Mobile Voice.
# ---------------------------------------------------------------------------

MOBILE_VOICE_FALSE_TRIGGERS = [
    "Slack",
    "Termux",
    "Android only",
    "owner approval",
    "open draft PR",
    "ship it",
    "route through AOS",
    "fix build",
]


@pytest.mark.parametrize("command", MOBILE_VOICE_FALSE_TRIGGERS)
def test_mobile_voice_guard_blocks_non_voice_surfaces(command: str) -> None:
    assert classify_mode(command) is not Mode.MOBILE_VOICE


MOBILE_VOICE_TRUE_SURFACES = [
    "Hey Jay note this",
    "voice note pick up groceries",
    "voice capture for later",
    "from my phone, queue this audit",
    "on the move, jot this",
    "while driving, remind me to commit later",
    "while walking with my dog",
]


@pytest.mark.parametrize("command", MOBILE_VOICE_TRUE_SURFACES)
def test_mobile_voice_surface_triggers_route(command: str) -> None:
    assert classify_mode(command) is Mode.MOBILE_VOICE


# ---------------------------------------------------------------------------
# Suite 3: Specialist extraction.
#
# HazMat / Nourish / Logistics activations should populate the
# Classification.specialists tuple regardless of which mode wins.
# ---------------------------------------------------------------------------

def test_specialist_hazmat_extracted_even_when_strategy_wins() -> None:
    result = classify("investor pitch outline for HazMat")
    assert result.mode is Mode.STRATEGY
    assert "hazmat" in result.specialists


def test_specialist_hazmat_extracted_when_builder_wins() -> None:
    result = classify("HazMat Command pre-flight")
    assert result.mode is Mode.BUILDER
    assert "hazmat" in result.specialists


def test_specialist_nourish_extracted() -> None:
    result = classify("Nourish meal log schema review")
    assert result.mode is Mode.BUILDER
    assert "nourish" in result.specialists


def test_specialist_logistics_extracted() -> None:
    result = classify("LTL carrier fleet review")
    assert "logistics" in result.specialists


def test_no_specialist_when_unrelated() -> None:
    result = classify("review PR 482")
    assert result.specialists == ()


# ---------------------------------------------------------------------------
# Suite 4: Tie-break order.
#
# When two modes score equal at the top, the documented priority chain
# (MOBILE_VOICE -> BUILDER -> CRITIC -> STRATEGY -> COMPANION)
# decides the winner.
# ---------------------------------------------------------------------------

def test_tie_break_mobile_voice_beats_builder() -> None:
    # "voice note" phrase (3) + "voice" token (1) == "open pr" phrase (3)
    # + "pr" token (1). Both score 4; priority order picks Mobile Voice.
    result = classify("voice note open pr")
    assert result.mode is Mode.MOBILE_VOICE
    assert result.scores[Mode.MOBILE_VOICE] == result.scores[Mode.BUILDER] == 4


def test_tie_break_builder_beats_strategy() -> None:
    # Builder "ship it" (3) > Strategy "roadmap" token (1).
    result = classify("ship it and roadmap planning")
    assert result.mode is Mode.BUILDER
    assert result.scores[Mode.BUILDER] > result.scores[Mode.STRATEGY]


def test_tie_break_critic_beats_strategy_at_equal_token_score() -> None:
    # Critic "flaws" token (1) == Strategy "growth" token (1).
    # Priority order picks Critic.
    result = classify("flaws and growth")
    assert result.mode is Mode.CRITIC
    assert result.scores[Mode.CRITIC] == result.scores[Mode.STRATEGY] == 1


def test_strategy_beats_companion_when_signal_present() -> None:
    # Strategy "launch blockers" (3) + "owner approval" (3) = 6; Companion 0.
    result = classify("launch blockers and owner approval")
    assert result.mode is Mode.STRATEGY
    assert result.scores[Mode.STRATEGY] >= 6
    assert result.scores[Mode.COMPANION] == 0


def test_companion_is_default_on_empty() -> None:
    result = classify("")
    assert result.mode is Mode.COMPANION
    assert all(score == 0 for score in result.scores.values())
    assert result.specialists == ()


def test_companion_is_default_on_neutral_text() -> None:
    result = classify("just thinking out loud about life")
    assert result.mode is Mode.COMPANION


# ---------------------------------------------------------------------------
# Suite 5: API contract.
# ---------------------------------------------------------------------------

def test_classify_returns_classification_with_full_score_map() -> None:
    result = classify("audit repo")
    assert isinstance(result, Classification)
    assert set(result.scores.keys()) == set(Mode)
    assert set(result.matched.keys()) == set(Mode)


def test_classify_mode_is_thin_wrapper() -> None:
    text = "use Claude to refactor"
    assert classify_mode(text) is classify(text).mode


def test_red_team_override_beats_strategy_co_occurrence() -> None:
    """Red-team override phrase (weight 6) should beat a co-occurring
    Strategy phrase (weight 3) even when both score positive."""
    result = classify("red team the investor pitch")
    assert result.mode is Mode.CRITIC
    assert result.scores[Mode.CRITIC] > result.scores[Mode.STRATEGY]


def test_production_ready_routes_to_strategy() -> None:
    """Strategy-heavy bias: 'production ready' is a business/launch
    readiness question, not a contrarian critique trigger."""
    result = classify("is the HazMat skill production ready?")
    assert result.mode is Mode.STRATEGY
    assert "hazmat" in result.specialists


def test_operator_mode_no_longer_exists() -> None:
    """Wave 01 acceptance ships 5 modes; Operator was folded into Builder
    and Strategy. Guard against accidental re-introduction."""
    assert "OPERATOR" not in Mode.__members__
    assert {m.value for m in Mode} == {
        "companion", "strategy", "critic", "builder", "mobile_voice",
    }

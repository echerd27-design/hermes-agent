"""Contract tests for hermes_cli.jarvis_prime output rendering.

Pins the JARVIS Prime turn/handoff output format so future gateway,
Slack, and mobile surfaces can rely on a stable contract. The renderer
is pure (no I/O, no env reads), so the hermetic invariants in
``tests/conftest.py`` carry through without extra setup.
"""

from __future__ import annotations

import pytest

from hermes_cli.jarvis_prime import persona
from hermes_cli.jarvis_prime.runtime import (
    Handoff,
    render_handoff,
    render_handoff_compact,
)


EXPECTED_MODES = frozenset(
    {"companion", "strategy", "critic", "operator", "builder", "mobile_voice"}
)


def _builder_handoff(**overrides: object) -> Handoff:
    defaults: dict[str, object] = dict(
        mission="ship the JARVIS output contract",
        mode="builder",
        route="claude-code-builder",
        delegate="claude-code-builder",
        owner_gates=("merge to main",),
        verification="pytest tests/test_jarvis_prime_output_contract.py passed",
        next_action="open the draft PR",
        remaining_risk="renderer not yet wired into gateway",
        actions=("scaffolded runtime.py", "scaffolded persona.py"),
    )
    defaults.update(overrides)
    return Handoff(**defaults)  # type: ignore[arg-type]


def test_modes_registry_matches_documented_set():
    assert persona.MODES == EXPECTED_MODES


def test_handoff_rejects_unknown_mode():
    with pytest.raises(ValueError):
        _builder_handoff(mode="bogus")


def test_render_long_form_for_builder_contains_all_contract_fields():
    rendered = render_handoff(_builder_handoff())
    for marker in (
        "Builder Mode",
        "Mission: ship the JARVIS output contract",
        "Route selected: claude-code-builder",
        "Delegate: claude-code-builder",
        "Actions taken: scaffolded runtime.py, scaffolded persona.py",
        "Verification: pytest tests/test_jarvis_prime_output_contract.py passed",
        "Owner gates: merge to main",
        "Next step: open the draft PR",
        "Remaining risk: renderer not yet wired into gateway",
    ):
        assert marker in rendered, f"missing contract field: {marker!r}"


def test_render_long_form_for_strategy_uses_strategy_tone_and_none_defaults():
    rendered = render_handoff(
        _builder_handoff(
            mode="strategy",
            route="aos-council",
            delegate="commercial-strategist",
            actions=(),
            owner_gates=(),
            remaining_risk="",
        )
    )
    assert "Strategy Mode" in rendered
    assert "Actions taken: none" in rendered
    assert "Owner gates: none" in rendered
    assert "Remaining risk: none" in rendered


def test_render_compact_for_mobile_voice_respects_line_and_width_budget():
    rendered = render_handoff_compact(
        _builder_handoff(mode="mobile_voice", route="mobile-capture")
    )
    lines = rendered.rstrip("\n").split("\n")
    assert len(lines) <= 6
    for line in lines:
        assert len(line) <= 80, f"line over 80 chars: {line!r}"
    assert any(line.startswith("[mobile_voice] Mission:") for line in lines)
    assert any(line.startswith("Next:") for line in lines)


def test_owner_gates_render_in_both_long_and_compact_forms():
    handoff = _builder_handoff(owner_gates=("merge to main", "deploy"))
    assert "Owner gates: merge to main, deploy" in render_handoff(handoff)
    assert "Gates: merge to main, deploy" in render_handoff_compact(handoff)

    empty = _builder_handoff(owner_gates=())
    assert "Owner gates: none" in render_handoff(empty)
    assert "Gates:" not in render_handoff_compact(empty)


def test_render_compact_preserves_mission_and_next_under_long_inputs():
    long_text = "x" * 500
    rendered = render_handoff_compact(
        _builder_handoff(mission=long_text, next_action=long_text)
    )
    lines = rendered.rstrip("\n").split("\n")
    mission_lines = [l for l in lines if l.startswith("[builder] Mission:")]
    next_lines = [l for l in lines if l.startswith("Next:")]
    assert mission_lines and mission_lines[0].endswith("…")
    assert next_lines and next_lines[0].endswith("…")
    for line in lines:
        assert len(line) <= 80


def test_render_is_deterministic_for_equal_handoffs():
    handoff_a = _builder_handoff()
    handoff_b = _builder_handoff()
    assert render_handoff(handoff_a) == render_handoff(handoff_b)
    assert render_handoff_compact(handoff_a) == render_handoff_compact(handoff_b)

"""Contract tests for hermes_cli.jarvis_prime output rendering.

These tests pin the JARVIS Prime turn/handoff output format so future
gateway, Slack, and mobile surfaces can rely on a stable contract. The
renderer is pure (no I/O, no env reads), so the hermetic invariants in
``tests/conftest.py`` carry through without extra setup.
"""

from __future__ import annotations

import importlib

import pytest

from hermes_cli.jarvis_prime import persona, runtime
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


def test_validate_mode_returns_input_for_known_mode():
    for mode in EXPECTED_MODES:
        assert persona.validate_mode(mode) == mode


def test_validate_mode_rejects_unknown_mode():
    with pytest.raises(ValueError) as exc_info:
        persona.validate_mode("bogus")
    message = str(exc_info.value)
    for mode in EXPECTED_MODES:
        assert mode in message, f"expected {mode!r} listed in error message"


def test_tone_label_uses_validate_mode():
    assert "Builder" in persona.tone_label("builder")
    with pytest.raises(ValueError):
        persona.tone_label("bogus")


def test_handoff_rejects_unknown_mode():
    with pytest.raises(ValueError):
        _builder_handoff(mode="bogus")


def test_handoff_requires_tuple_owner_gates():
    with pytest.raises(TypeError):
        Handoff(
            mission="m",
            mode="builder",
            route="r",
            delegate="d",
            owner_gates=["merge"],  # type: ignore[arg-type]
            verification="v",
            next_action="n",
        )


def test_from_mapping_coerces_lists_to_tuples():
    handoff = Handoff.from_mapping(
        {
            "mission": "m",
            "mode": "operator",
            "route": "aos-council",
            "delegate": "none",
            "owner_gates": ["merge", "deploy"],
            "verification": "deferred",
            "next_action": "expand later",
            "actions": ["captured rough idea"],
        }
    )
    assert handoff.owner_gates == ("merge", "deploy")
    assert handoff.actions == ("captured rough idea",)


def test_from_mapping_rejects_unknown_keys():
    with pytest.raises(ValueError) as exc_info:
        Handoff.from_mapping(
            {
                "mission": "m",
                "mode": "builder",
                "route": "r",
                "delegate": "d",
                "owner_gates": (),
                "verification": "v",
                "next_action": "n",
                "bogus_field": "x",
            }
        )
    assert "bogus_field" in str(exc_info.value)


def test_render_long_form_contains_every_contract_field():
    handoff = _builder_handoff()
    rendered = render_handoff(handoff)
    for marker in (
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
    assert rendered.startswith("Builder Mode")
    assert rendered.endswith("\n")


def test_render_long_form_renders_empty_actions_as_none():
    handoff = _builder_handoff(
        mode="strategy",
        route="aos-council",
        delegate="commercial-strategist",
        actions=(),
        owner_gates=(),
        remaining_risk="",
    )
    rendered = render_handoff(handoff)
    assert "Strategy Mode" in rendered
    assert "Actions taken: none" in rendered
    assert "Owner gates: none" in rendered
    assert "Remaining risk: none" in rendered


def test_render_compact_form_respects_line_and_width_budget():
    handoff = _builder_handoff(mode="mobile_voice", route="mobile-capture")
    rendered = render_handoff_compact(handoff)
    lines = rendered.rstrip("\n").split("\n")
    assert len(lines) <= 6, f"compact form exceeded line budget: {lines!r}"
    for line in lines:
        assert len(line) <= 80, f"line over 80 chars: {line!r}"
    assert any(line.startswith("[mobile_voice] Mission:") for line in lines)
    assert any(line.startswith("Next:") for line in lines)


def test_render_compact_form_includes_owner_gates_when_present():
    handoff = _builder_handoff(owner_gates=("merge to main", "deploy"))
    rendered = render_handoff_compact(handoff)
    assert "Gates: merge to main, deploy" in rendered


def test_render_compact_form_drops_gates_line_when_empty():
    handoff = _builder_handoff(owner_gates=())
    rendered = render_handoff_compact(handoff)
    assert "Gates:" not in rendered


def test_render_compact_form_drops_risk_line_when_empty():
    handoff = _builder_handoff(remaining_risk="")
    rendered = render_handoff_compact(handoff)
    assert "Risk:" not in rendered


def test_render_compact_preserves_mission_and_next_under_long_inputs():
    long_text = "x" * 500
    handoff = _builder_handoff(mission=long_text, next_action=long_text)
    rendered = render_handoff_compact(handoff)
    lines = rendered.rstrip("\n").split("\n")
    mission_lines = [l for l in lines if l.startswith("[builder] Mission:")]
    next_lines = [l for l in lines if l.startswith("Next:")]
    assert mission_lines, "mission line missing from compact form"
    assert next_lines, "next line missing from compact form"
    assert mission_lines[0].endswith("…"), "long mission should be truncated"
    assert next_lines[0].endswith("…"), "long next action should be truncated"
    for line in lines:
        assert len(line) <= 80


def test_render_compact_floor_rejects_too_few_lines():
    handoff = _builder_handoff()
    with pytest.raises(ValueError):
        render_handoff_compact(handoff, max_lines=3)


def test_render_long_form_is_deterministic():
    handoff_a = _builder_handoff()
    handoff_b = _builder_handoff()
    assert render_handoff(handoff_a) == render_handoff(handoff_b)


def test_render_compact_form_is_deterministic():
    handoff_a = _builder_handoff()
    handoff_b = _builder_handoff()
    assert render_handoff_compact(handoff_a) == render_handoff_compact(handoff_b)


def test_modules_import_cleanly():
    # Re-import to confirm modules are side-effect free under fresh import.
    importlib.reload(persona)
    importlib.reload(runtime)
    assert callable(runtime.render_handoff)
    assert callable(runtime.render_handoff_compact)
    assert persona.MODES == EXPECTED_MODES

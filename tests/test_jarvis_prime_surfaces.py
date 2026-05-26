"""Tests for the JARVIS Prime surface adapter contract (Wave 04)."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from hermes_cli.jarvis_prime import (
    SLACK_MAX,
    SURFACES,
    TERMUX_MAX,
    VOICE_MAX,
    JarvisTurn,
    render,
    to_android,
    to_cli,
    to_slack,
    to_termux,
    to_voice,
)


def _make_turn() -> JarvisTurn:
    return JarvisTurn(
        mission="Ship the wave-04 contract",
        summary="Define JarvisTurn and five surface adapters with tests.",
        route="claude_code",
        mode="builder",
        actions=("write surfaces.py", "write tests", "open draft PR"),
        verification=("pytest passed", "compileall passed"),
        risks=("downstream wiring still pending",),
        rollback="delete hermes_cli/jarvis_prime/ and the new test file",
        task_packet={"id": "w04", "resume_at": "tests"},
    )


def test_jarvis_turn_is_frozen():
    turn = _make_turn()
    with pytest.raises(FrozenInstanceError):
        turn.mission = "changed"  # type: ignore[misc]


def test_to_cli_includes_route_and_verification_even_when_empty():
    minimal = JarvisTurn(mission="ping")
    out = to_cli(minimal)
    assert "Route:" in out
    assert "Verification:" in out


def test_to_cli_full_output_contains_all_sections():
    out = to_cli(_make_turn())
    for needle in (
        "Mission: Ship the wave-04 contract",
        "Route: claude_code",
        "Mode: builder",
        "Summary:",
        "Define JarvisTurn",
        "Actions:",
        "write surfaces.py",
        "Verification:",
        "pytest passed",
        "Risks:",
        "downstream wiring still pending",
        "Rollback:",
    ):
        assert needle in out, f"missing {needle!r} in CLI output"


def test_to_slack_under_max_length():
    assert len(to_slack(_make_turn())) <= SLACK_MAX


def test_to_slack_uses_single_asterisk_bold():
    out = to_slack(_make_turn())
    assert "**" not in out
    assert out.startswith("*")


def test_to_android_is_json_round_trippable():
    payload = to_android(_make_turn())
    round_tripped = json.loads(json.dumps(payload))
    assert round_tripped == payload


def test_to_android_keys_are_snake_case():
    payload = to_android(_make_turn())
    assert set(payload) == {
        "mission",
        "summary",
        "route",
        "mode",
        "actions",
        "verification",
        "risks",
        "rollback",
        "task_packet",
    }
    assert isinstance(payload["actions"], list)
    assert isinstance(payload["verification"], list)
    assert isinstance(payload["risks"], list)
    assert payload["task_packet"] == {"id": "w04", "resume_at": "tests"}


def test_to_termux_is_ascii_only():
    turn = JarvisTurn(
        mission="prepare résumé",
        summary="café break — fix bug",
        actions=("ship it 🚀",),
    )
    out = to_termux(turn)
    out.encode("ascii")  # must not raise


def test_to_termux_under_max_length():
    assert len(to_termux(_make_turn())) <= TERMUX_MAX


def test_to_voice_under_max_length():
    assert len(to_voice(_make_turn())) <= VOICE_MAX


def test_to_voice_has_no_markdown_symbols():
    out = to_voice(_make_turn())
    for ch in ("*", "_", "`", "#", ">"):
        assert ch not in out, f"voice output should not contain {ch!r}"


@pytest.mark.parametrize("surface", sorted(SURFACES))
def test_render_dispatches_each_surface(surface):
    turn = _make_turn()
    assert render(surface, turn) == SURFACES[surface](turn)


def test_render_unknown_surface_raises_value_error():
    with pytest.raises(ValueError, match="unknown surface"):
        render("smoke-signal", _make_turn())


@pytest.mark.parametrize("surface", sorted(SURFACES))
def test_minimal_turn_renders_cleanly(surface):
    minimal = JarvisTurn(mission="x")
    result = render(surface, minimal)
    if surface == "android":
        assert isinstance(result, dict)
        assert result["mission"] == "x"
    else:
        assert isinstance(result, str)
        assert "x" in result


def test_long_summary_is_truncated_on_short_surfaces():
    long_summary = "word " * 1000
    turn = JarvisTurn(
        mission="truncation check",
        summary=long_summary,
        actions=("act " * 200,),
    )
    assert len(to_slack(turn)) <= SLACK_MAX
    assert len(to_termux(turn)) <= TERMUX_MAX
    assert len(to_voice(turn)) <= VOICE_MAX


def test_non_ascii_summary_safely_rendered_on_termux():
    turn = JarvisTurn(
        mission="hazmat audit",
        summary="naïve façade — encoded ☂",
        actions=("review",),
    )
    out = to_termux(turn)
    out.encode("ascii")
    assert "hazmat audit" in out


def test_known_surface_set_matches_documented_five():
    assert set(SURFACES) == {"cli", "slack", "android", "termux", "voice"}

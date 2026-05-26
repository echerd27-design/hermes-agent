"""Tests for the JARVIS Prime CLI slash adapter.

Pure unit tests on ``hermes_cli.jarvis_prime`` plus a single
argparse-driven test for ``cmd_jarvis`` in ``hermes_cli.main``. No
Hermes runtime, no network, no LLM dependency.

See ``docs/aci/reports/W01_CLI_JARVIS_WIRING.md`` for scope and the
slash → mode mapping under test.
"""

from __future__ import annotations

import argparse
from io import StringIO
from unittest.mock import patch

import pytest

from hermes_cli.jarvis_prime import (
    DEFAULT_RESPONSE_FORMAT,
    OPERATIONAL_HANDOFF_FORMAT,
    Mode,
    ModeClassifier,
    NAMED_MODES,
    RouteResult,
    Router,
    SLASH_COMMANDS,
    dispatch,
    header_for,
)


# ---------------------------------------------------------------------------
# Table-level mapping
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "slash, expected_mode",
    [
        ("/jarvis", Mode.AUTO),
        ("/jp", Mode.AUTO),
        ("/jarvis-prime", Mode.AUTO),
        ("/builder", Mode.BUILDER),
        ("/operator", Mode.OPERATOR),
        ("/strategy", Mode.STRATEGY),
        ("/critic", Mode.CRITIC),
        ("/companion", Mode.COMPANION),
        ("/voice", Mode.MOBILE_VOICE),
        ("/mobile-voice", Mode.MOBILE_VOICE),
    ],
)
def test_slash_commands_table_maps_to_modes(slash, expected_mode):
    assert SLASH_COMMANDS[slash] is expected_mode


# ---------------------------------------------------------------------------
# dispatch — concrete-mode slashes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "command_line, expected_mode",
    [
        ("/builder ship the PR", Mode.BUILDER),
        ("/operator route this to AOS", Mode.OPERATOR),
        ("/strategy pricing decision", Mode.STRATEGY),
        ("/critic this plan is weak", Mode.CRITIC),
        ("/companion I feel tired", Mode.COMPANION),
        ("/mobile-voice on the move", Mode.MOBILE_VOICE),
    ],
)
def test_dispatch_concrete_modes_resolve(command_line, expected_mode):
    result = dispatch(command_line)
    assert result is not None
    assert result.mode is expected_mode


# ---------------------------------------------------------------------------
# dispatch — AUTO autoclassification
# ---------------------------------------------------------------------------

def test_dispatch_jarvis_autoclassifies_builder():
    result = dispatch("/jarvis ship the build PR")
    assert result is not None
    assert result.mode is Mode.BUILDER
    assert result.payload == "ship the build PR"


def test_dispatch_jp_autoclassifies_critic():
    result = dispatch("/jp this idea is weak, disagree")
    assert result is not None
    assert result.mode is Mode.CRITIC


def test_dispatch_jarvis_prime_autoclassifies_strategy():
    result = dispatch("/jarvis-prime pricing strategy for the launch")
    assert result is not None
    assert result.mode is Mode.STRATEGY


# ---------------------------------------------------------------------------
# dispatch — unknown / non-slash → None
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "command_line",
    [
        "/help",
        "/quit",
        "/foo",
        "/unknown thing",
        "not a slash command",
        "",
        "   ",
    ],
)
def test_dispatch_unknown_returns_none(command_line):
    assert dispatch(command_line) is None


def test_dispatch_non_string_returns_none():
    assert dispatch(None) is None  # type: ignore[arg-type]
    assert dispatch(123) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# dispatch — /voice precedence
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "command_line",
    [
        "/voice on",
        "/voice off",
        "/voice tts",
        "/voice status",
        "/voice ON",
        "/voice Status please",
    ],
)
def test_voice_with_subcommand_defers_to_existing_handler(command_line):
    """Bare /voice → JARVIS Mobile Voice; subcommand tokens defer.

    Returning None lets the existing voice-toggle CommandDef in
    hermes_cli/commands.py keep control with no behavior change.
    """
    assert dispatch(command_line) is None


@pytest.mark.parametrize("command_line", ["/voice", "/voice   "])
def test_voice_bare_maps_to_mobile_voice(command_line):
    result = dispatch(command_line)
    assert result is not None
    assert result.mode is Mode.MOBILE_VOICE


# ---------------------------------------------------------------------------
# ModeClassifier heuristics
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text, expected_mode",
    [
        ("ship the PR", Mode.BUILDER),
        ("route this task to AOS", Mode.OPERATOR),
        ("pricing tradeoff for the roadmap", Mode.STRATEGY),
        ("this plan is weak, I disagree", Mode.CRITIC),
        ("I feel tired and stressed", Mode.COMPANION),
        ("jogging now, capture this idea", Mode.MOBILE_VOICE),
    ],
)
def test_classifier_heuristics(text, expected_mode):
    assert ModeClassifier().classify(text) is expected_mode


def test_classifier_empty_defaults_to_companion():
    assert ModeClassifier().classify("") is Mode.COMPANION
    assert ModeClassifier().classify("   ") is Mode.COMPANION


# ---------------------------------------------------------------------------
# Router & Persona contract
# ---------------------------------------------------------------------------

def test_router_returns_route_result_with_default_format_for_reasoning_modes():
    for mode in (Mode.COMPANION, Mode.STRATEGY, Mode.CRITIC, Mode.MOBILE_VOICE):
        route = Router().route(mode, "some payload")
        assert isinstance(route, RouteResult)
        assert route.mode is mode
        assert route.response_format == DEFAULT_RESPONSE_FORMAT
        assert route.persona_header == header_for(mode)


def test_router_returns_operational_format_for_operator_and_builder():
    for mode in (Mode.OPERATOR, Mode.BUILDER):
        route = Router().route(mode, "some payload")
        assert route.response_format == OPERATIONAL_HANDOFF_FORMAT


def test_router_rejects_auto():
    with pytest.raises(ValueError):
        Router().route(Mode.AUTO, "payload")


def test_header_for_each_named_mode_unique_and_nonempty():
    seen: set[str] = set()
    for mode in NAMED_MODES:
        header = header_for(mode)
        assert isinstance(header, str) and header.strip()
        assert header not in seen
        seen.add(header)


def test_header_for_auto_raises():
    with pytest.raises(ValueError):
        header_for(Mode.AUTO)


# ---------------------------------------------------------------------------
# cmd_jarvis (main.py argparse glue)
# ---------------------------------------------------------------------------

def _make_args(command: str, *message: str) -> argparse.Namespace:
    return argparse.Namespace(command=command, message=list(message))


def test_cmd_jarvis_runs_dispatch_for_known_slash():
    from hermes_cli.main import cmd_jarvis

    buf = StringIO()
    with patch("sys.stdout", buf):
        rc = cmd_jarvis(_make_args("/builder", "ship", "the", "PR"))
    out = buf.getvalue()

    assert rc == 0
    assert "mode: builder" in out
    assert "Builder Mode" in out
    assert "Payload: ship the PR" in out


def test_cmd_jarvis_reports_unknown_slash():
    from hermes_cli.main import cmd_jarvis

    buf = StringIO()
    with patch("sys.stdout", buf):
        rc = cmd_jarvis(_make_args("/notarealcommand"))
    out = buf.getvalue()

    assert rc == 1
    assert "Unknown JARVIS slash command" in out


def test_cmd_jarvis_classifies_free_text():
    from hermes_cli.main import cmd_jarvis

    buf = StringIO()
    with patch("sys.stdout", buf):
        rc = cmd_jarvis(_make_args("ship", "the", "build"))
    out = buf.getvalue()

    assert rc == 0
    assert "mode: builder" in out


def test_cmd_jarvis_voice_subcommand_treated_as_unknown():
    """`/voice on` returns None from dispatch → cmd_jarvis prints unknown.

    This is the intentional contract: the actual /voice toggle lives in
    hermes_cli/commands.py and is reached through the interactive REPL,
    not the `hermes jarvis` subcommand.
    """
    from hermes_cli.main import cmd_jarvis

    buf = StringIO()
    with patch("sys.stdout", buf):
        rc = cmd_jarvis(_make_args("/voice", "on"))
    out = buf.getvalue()

    assert rc == 1
    assert "Unknown JARVIS slash command" in out

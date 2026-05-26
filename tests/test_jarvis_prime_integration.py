"""End-to-end integration test for the JARVIS Prime runtime kernel.

Asserts the public contract: a single ``route(mission)`` call drives the
full pipeline (mode classification → tier routing → risk assessment →
build packet → 8 gates → surface render → events → ledger append) and
returns a populated SessionResult.

A second test pins the lazy-import contract: importing ``hermes_cli``
must NOT transitively import ``hermes_cli.jarvis_prime``.
"""

from __future__ import annotations

import sys

import pytest

from hermes_cli.jarvis_prime import (
    GateName,
    Mission,
    Mode,
    RiskClass,
    Surface,
    route,
)
from hermes_cli.jarvis_prime import events as _events_mod
from hermes_cli.jarvis_prime import jobs as _jobs_mod
from hermes_cli.jarvis_prime import ledger as _ledger_mod


@pytest.fixture(autouse=True)
def _reset_jarvis_prime_state():
    """Clear in-memory ledger/events/jobs between tests."""
    _ledger_mod._LEDGER.clear()
    _events_mod._EVENTS.clear()
    _jobs_mod._JOBS.clear()
    yield
    _ledger_mod._LEDGER.clear()
    _events_mod._EVENTS.clear()
    _jobs_mod._JOBS.clear()


def test_jarvis_prime_end_to_end_kernel():
    """One mission drives every stage of the pipeline."""
    mission = Mission(
        text="Build a docs-only audit script and ship a PR",
        surface=Surface.CLI,
        repo_root="/tmp/repo",
        metadata={"source": "integration-test"},
    )

    result = route(mission)

    # 1. Mode classification
    assert result.mode is Mode.BUILDER

    # 2. Route decision
    assert result.route.tier in {"jarvis_prime", "aos_council", "specialists", "workers"}
    assert result.route.target

    # 3. Risk class
    assert isinstance(result.risk.level, RiskClass)
    assert result.risk.level is RiskClass.LOW
    assert result.risk.owner_gate is False

    # 4. Build packet (BUILDER mode populates one)
    assert result.build_packet is not None
    assert result.build_packet.mission_id
    assert result.build_packet.rollback
    assert result.build_packet.allowed_paths
    assert result.build_packet.verification_plan

    # 5. Gate summary — all 8 gates present
    gate_names = {o.name for o in result.gate_summary.outcomes}
    assert gate_names == set(GateName)
    assert result.gate_summary.headline == "pass"

    # 6. Surface output
    assert isinstance(result.surface_output, str)
    assert result.surface_output
    assert "builder" in result.surface_output

    # 7. Events + ledger
    assert len(result.events) >= 1
    assert result.ledger_entry.mission_id == result.build_packet.mission_id
    assert result.ledger_entry.mode == "builder"
    assert result.ledger_entry.gate_result == "pass"

    # 8. Ledger persistence
    assert len(_ledger_mod._LEDGER) == 1
    assert _ledger_mod._LEDGER[0] is result.ledger_entry


def test_owner_gated_mission_surfaces_needs_owner():
    """Owner-gated risk terms trip OWNER_APPROVAL on the gate summary."""
    mission = Mission(
        text="Deploy to production and merge the secret key change",
        surface=Surface.CLI,
        repo_root="/tmp/repo",
    )
    result = route(mission)

    assert result.risk.level is RiskClass.OWNER_GATED
    assert result.risk.owner_gate is True
    owner_outcome = next(
        o for o in result.gate_summary.outcomes if o.name is GateName.OWNER_APPROVAL
    )
    assert owner_outcome.status == "needs_owner"
    assert result.gate_summary.headline == "needs-owner"


def test_mobile_voice_renders_short_form():
    """The mobile_voice surface gets a single-line render."""
    mission = Mission(
        text="Talk to me while I walk — strategy check on the roadmap",
        surface=Surface.MOBILE_VOICE,
    )
    result = route(mission)

    assert result.mode is Mode.MOBILE_VOICE
    assert "\n" not in result.surface_output


def test_route_is_lazy_safe():
    """``import hermes_cli`` must NOT transitively import jarvis_prime."""
    sys.modules.pop("hermes_cli", None)
    sys.modules.pop("hermes_cli.jarvis_prime", None)
    for mod_name in list(sys.modules):
        if mod_name.startswith("hermes_cli.jarvis_prime."):
            sys.modules.pop(mod_name, None)

    import hermes_cli  # noqa: F401

    assert "hermes_cli.jarvis_prime" not in sys.modules

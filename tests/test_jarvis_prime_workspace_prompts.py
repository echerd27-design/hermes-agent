"""Tests for hermes_cli.jarvis_prime.workspace_prompts.

The four named ACI workspaces (Nourish, HazMat Command, Hey Jay,
Hermes Core) are exercised explicitly. The aux LLM polish path is
covered with mocked clients; the local-template fallback is covered by
patching the aux client to be unavailable.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from hermes_cli.jarvis_prime import workspace_prompts as wp


NOURISH = {
    "name": "Nourish",
    "slug": "nourish",
    "domain": "nutrition",
    "stage": "beta",
    "platforms": ["ios", "android"],
    "tech_stack": ["React Native", "Supabase"],
    "audience": "wellness-curious adults",
    "north_star": "logged meals per active user per week",
    "risks": ["food-data licensing", "iOS app review timing"],
}

HAZMAT = {
    "name": "HazMat Command",
    "slug": "hazmat-command",
    "domain": "logistics / 49 CFR compliance",
    "stage": "alpha",
    "platforms": ["web", "android"],
    "tech_stack": ["Next.js", "Postgres"],
    "audience": "owner-operator truck drivers carrying hazmat loads",
    "north_star": "minutes saved per load on paperwork",
    "risks": ["regulatory accuracy", "audit trail"],
}

HEY_JAY = {
    "name": "Hey Jay",
    "slug": "hey-jay",
    "domain": "truck-safe navigation",
    "stage": "prototype",
    "platforms": ["android"],
    "tech_stack": ["Kotlin", "Mapbox"],
    "audience": "long-haul truck drivers",
    "north_star": "low-clearance incidents avoided",
    "risks": ["map data freshness", "battery footprint"],
}

HERMES_CORE = {
    "name": "Hermes Core",
    "slug": "hermes-core",
    "domain": "agent framework",
    "stage": "0.14.x",
    "platforms": ["linux", "macos", "termux", "windows"],
    "tech_stack": ["Python", "Click"],
    "audience": "developers building agent workflows",
    "north_star": "weekly active operator profiles",
    "risks": ["provider-API drift", "model-version coupling"],
}

NAMED_WORKSPACES = [
    pytest.param(NOURISH, id="nourish"),
    pytest.param(HAZMAT, id="hazmat-command"),
    pytest.param(HEY_JAY, id="hey-jay"),
    pytest.param(HERMES_CORE, id="hermes-core"),
]


# ---------------------------------------------------------------------------
# Aux client patching helpers
# ---------------------------------------------------------------------------


def _fake_aux_response(content: str) -> MagicMock:
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    return resp


def _patch_aux(content: str):
    client = MagicMock()
    client.chat.completions.create = MagicMock(return_value=_fake_aux_response(content))
    return patch(
        "agent.auxiliary_client.get_text_auxiliary_client",
        return_value=(client, "test-model"),
    )


def _patch_aux_unavailable():
    """Make the aux client lookup fail so the local fallback is returned."""
    return patch(
        "agent.auxiliary_client.get_text_auxiliary_client",
        side_effect=RuntimeError("no client configured"),
    )


def _patch_aux_extra_body():
    return patch("agent.auxiliary_client.get_auxiliary_extra_body", return_value={})


# ---------------------------------------------------------------------------
# Core surface
# ---------------------------------------------------------------------------


def test_prompt_kinds_constant_is_exactly_eight():
    assert wp.PROMPT_KINDS == (
        "launch_audit",
        "blocker_fix",
        "codex_review",
        "release_checklist",
        "security_review",
        "mobile_readiness",
        "pricing_strategy",
        "investor_summary",
    )


def test_dispatch_unknown_kind_raises():
    with pytest.raises(ValueError, match="unknown prompt kind"):
        wp.generate_prompt(NOURISH, "bogus")


def test_does_not_import_workspaces_module():
    # Even after importing the prompt module, the sibling `workspaces`
    # module must not be pulled in. Wave non-overlap contract.
    assert "hermes_cli.jarvis_prime.workspaces" not in sys.modules


# ---------------------------------------------------------------------------
# Workspace coverage — the four named ACI workspaces
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("workspace", NAMED_WORKSPACES)
def test_launch_audit_local_template_carries_workspace_facts(workspace):
    with _patch_aux_unavailable(), _patch_aux_extra_body():
        outcome = wp.launch_audit_prompt(workspace)

    assert outcome.ok is False
    assert outcome.reason == "aux_unavailable"
    assert outcome.kind == "launch_audit"
    assert outcome.workspace_name == workspace["name"]

    md = outcome.prompt_markdown
    assert workspace["name"] in md
    assert workspace["domain"] in md
    # At least one platform token should appear in the rendered facts.
    assert any(p in md for p in workspace["platforms"])
    # Audience surfaces in the workspace facts block too.
    assert workspace["audience"] in md
    # Output format footer must be present.
    assert "## Output format" in md


# ---------------------------------------------------------------------------
# All eight kinds must render usable markdown
# ---------------------------------------------------------------------------


KIND_HEADINGS = {
    "launch_audit": "## Launch audit",
    "blocker_fix": "## Blocker fix",
    "codex_review": "## Codex review",
    "release_checklist": "## Release checklist",
    "security_review": "## Security review",
    "mobile_readiness": "## Mobile readiness",
    "pricing_strategy": "## Pricing strategy",
    "investor_summary": "## Investor summary",
}


@pytest.mark.parametrize("kind", wp.PROMPT_KINDS)
def test_all_eight_kinds_render_for_nourish(kind):
    with _patch_aux_unavailable(), _patch_aux_extra_body():
        outcome = wp.generate_prompt(NOURISH, kind)
    md = outcome.prompt_markdown
    assert md.strip(), f"{kind} produced empty markdown"
    assert KIND_HEADINGS[kind] in md
    assert "## Workspace facts" in md
    assert "## Output format" in md
    assert outcome.kind == kind
    assert outcome.workspace_name == "Nourish"


# ---------------------------------------------------------------------------
# Duck typing — dict vs object
# ---------------------------------------------------------------------------


def test_accepts_dict_and_object_identically():
    ns = types.SimpleNamespace(**HEY_JAY)
    with _patch_aux_unavailable(), _patch_aux_extra_body():
        from_dict = wp.launch_audit_prompt(HEY_JAY).prompt_markdown
        from_obj = wp.launch_audit_prompt(ns).prompt_markdown
    assert from_dict == from_obj


# ---------------------------------------------------------------------------
# Aux LLM polish path
# ---------------------------------------------------------------------------


def test_aux_polish_strips_code_fences_and_marks_ok():
    polished = (
        "```markdown\n"
        "# Launch audit — Nourish\n\n"
        "## Launch audit\n\n"
        "Polished body.\n\n"
        "## Output format\n\n"
        "- one\n"
        "```"
    )
    with _patch_aux(polished), _patch_aux_extra_body():
        outcome = wp.launch_audit_prompt(NOURISH)
    assert outcome.ok is True
    assert outcome.reason == "aux_ok"
    assert outcome.prompt_markdown.startswith("# Launch audit — Nourish")
    assert "```" not in outcome.prompt_markdown


def test_aux_polish_runtime_error_falls_back_to_local_template():
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError("upstream 503")
    with patch(
        "agent.auxiliary_client.get_text_auxiliary_client",
        return_value=(client, "test-model"),
    ), _patch_aux_extra_body():
        outcome = wp.security_review_prompt(HAZMAT, scope="audit trail")
    assert outcome.ok is False
    assert outcome.reason.startswith("aux_error:")
    assert "RuntimeError" in outcome.reason
    # Falls back to the local template, which still mentions the workspace.
    assert "HazMat Command" in outcome.prompt_markdown
    assert "audit trail" in outcome.prompt_markdown


def test_aux_polish_no_configured_client_returns_local_template():
    with patch(
        "agent.auxiliary_client.get_text_auxiliary_client",
        return_value=(None, ""),
    ), _patch_aux_extra_body():
        outcome = wp.launch_audit_prompt(HERMES_CORE)
    assert outcome.ok is False
    assert outcome.reason == "aux_unavailable"
    assert "Hermes Core" in outcome.prompt_markdown
    assert "## Launch audit" in outcome.prompt_markdown


def test_aux_polish_empty_response_falls_back():
    with _patch_aux(""), _patch_aux_extra_body():
        outcome = wp.launch_audit_prompt(NOURISH)
    assert outcome.ok is False
    assert outcome.reason == "aux_empty"
    assert "Nourish" in outcome.prompt_markdown


# ---------------------------------------------------------------------------
# Kwargs surface in the rendered prompt
# ---------------------------------------------------------------------------


def test_blocker_fix_includes_blocker_text():
    with _patch_aux_unavailable(), _patch_aux_extra_body():
        outcome = wp.blocker_fix_prompt(
            NOURISH, blocker="meal plan generator times out on slow networks"
        )
    assert "meal plan generator times out" in outcome.prompt_markdown


def test_release_checklist_includes_version():
    with _patch_aux_unavailable(), _patch_aux_extra_body():
        outcome = wp.release_checklist_prompt(HERMES_CORE, version="0.14.1")
    assert "0.14.1" in outcome.prompt_markdown


def test_codex_review_includes_diff_summary():
    with _patch_aux_unavailable(), _patch_aux_extra_body():
        outcome = wp.codex_review_prompt(
            HAZMAT, diff_summary="adds shipping-paper PDF export"
        )
    assert "shipping-paper PDF export" in outcome.prompt_markdown


def test_mobile_readiness_includes_target():
    with _patch_aux_unavailable(), _patch_aux_extra_body():
        outcome = wp.mobile_readiness_prompt(HEY_JAY, target="android")
    assert "android" in outcome.prompt_markdown.lower()


def test_extra_context_is_appended():
    with _patch_aux_unavailable(), _patch_aux_extra_body():
        outcome = wp.launch_audit_prompt(
            NOURISH, extra_context="App Store review timing matters this week."
        )
    assert "App Store review timing matters this week." in outcome.prompt_markdown
    assert "## Extra context" in outcome.prompt_markdown


# ---------------------------------------------------------------------------
# Workspace adapter edge cases
# ---------------------------------------------------------------------------


def test_field_handles_missing_keys_gracefully():
    minimal = {"name": "MysteryProduct"}
    with _patch_aux_unavailable(), _patch_aux_extra_body():
        outcome = wp.launch_audit_prompt(minimal)
    assert outcome.workspace_name == "MysteryProduct"
    assert "MysteryProduct" in outcome.prompt_markdown


def test_field_handles_comma_separated_string_lists():
    ws = {"name": "ListyApp", "platforms": "ios, android, web"}
    with _patch_aux_unavailable(), _patch_aux_extra_body():
        outcome = wp.launch_audit_prompt(ws)
    md = outcome.prompt_markdown
    assert "ios" in md and "android" in md and "web" in md


def test_unnamed_workspace_falls_back_to_placeholder():
    with _patch_aux_unavailable(), _patch_aux_extra_body():
        outcome = wp.launch_audit_prompt({})
    assert outcome.workspace_name == "(unnamed workspace)"


# ---------------------------------------------------------------------------
# Re-export surface
# ---------------------------------------------------------------------------


def test_subpackage_reexports_public_api():
    from hermes_cli import jarvis_prime as jp

    assert jp.PROMPT_KINDS == wp.PROMPT_KINDS
    assert jp.generate_prompt is wp.generate_prompt
    assert jp.launch_audit_prompt is wp.launch_audit_prompt
    assert jp.WorkspacePromptOutcome is wp.WorkspacePromptOutcome

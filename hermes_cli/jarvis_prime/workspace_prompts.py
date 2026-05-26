"""Workspace-aware prompt generator for ACI build/review tasks.

ACI is Jeremiah Echerd's portfolio of products — Nourish (nutrition),
HazMat Command (49 CFR logistics compliance), Hey Jay (truck-safe
navigation), and Hermes Core (the agent framework itself). Each one
periodically needs the same eight kinds of prompt:

  - ``launch_audit``       — pre-launch readiness review
  - ``blocker_fix``        — focused single-blocker resolution packet
  - ``codex_review``       — Codex Task Packet for a diff or feature
  - ``release_checklist``  — version-cut go/no-go checklist
  - ``security_review``    — scoped security review
  - ``mobile_readiness``   — Android / iOS / store-readiness review
  - ``pricing_strategy``   — pricing + positioning packet
  - ``investor_summary``   — investor / partner briefing

This module turns any workspace record into a copy/paste-safe markdown
prompt for one of those kinds. Output is intended to be pasted into
Claude Code, Codex, Slack, or a kanban task body.

Design notes
------------
- Mirrors ``hermes_cli/profile_describer.py``: lazy aux LLM import
  inside the call, ``WorkspacePromptOutcome`` dataclass result, lenient
  response parsing, never raises on expected failure modes.
- The aux LLM **polishes** a deterministic local template. If the aux
  client is unavailable, the local template is returned verbatim and
  the outcome reports ``ok=False, reason="aux_unavailable"``. Callers
  always get usable markdown — the LLM is an enhancement, not a
  dependency.
- Workspace input is **duck-typed**. We accept a ``Mapping`` (dict,
  TypedDict-instance) or any object with attribute access (dataclass,
  ``SimpleNamespace``, future ``Workspace`` class). We do **not**
  import ``hermes_cli.jarvis_prime.workspaces`` — that module is owned
  by a sibling wave and this module must not depend on it.
- Every public function shares one private ``_render_workspace_facts``
  helper so the "workspace facts" block is identical across the eight
  prompt kinds.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

logger = logging.getLogger(__name__)


PROMPT_KINDS: tuple[str, ...] = (
    "launch_audit",
    "blocker_fix",
    "codex_review",
    "release_checklist",
    "security_review",
    "mobile_readiness",
    "pricing_strategy",
    "investor_summary",
)


@dataclass
class WorkspacePromptOutcome:
    """Result of generating one workspace prompt.

    ``prompt_markdown`` is always populated with usable markdown — even
    when ``ok`` is False, callers can paste it directly. ``ok`` only
    reflects whether the aux LLM polish step succeeded.
    """

    kind: str
    workspace_name: str
    ok: bool
    reason: str
    prompt_markdown: str


_FENCE_RE = re.compile(r"^```(?:markdown|md)?\s*\n?|\n?```\s*$", re.MULTILINE)


# ---------------------------------------------------------------------------
# Workspace adapter (duck-typed)
# ---------------------------------------------------------------------------


def _field(ws: Any, key: str, default: str = "") -> str:
    """Read a string-ish field from a workspace dict or object.

    Tries ``Mapping.get`` first, then ``getattr``. Returns ``default``
    when the value is missing, ``None``, or empty string.
    """
    if isinstance(ws, Mapping):
        value = ws.get(key, default)
    else:
        value = getattr(ws, key, default)
    if value in (None, "", []):
        return default
    return str(value)


def _list_field(ws: Any, key: str) -> list[str]:
    """Read a list-ish field. Accepts list/tuple/str (comma-split)."""
    if isinstance(ws, Mapping):
        value = ws.get(key)
    else:
        value = getattr(ws, key, None)
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, Iterable):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value)]


def _workspace_name(ws: Any) -> str:
    return _field(ws, "name", default="(unnamed workspace)")


def _render_workspace_facts(ws: Any) -> str:
    """Render the shared "Workspace facts" block.

    Same shape across all eight prompt kinds so downstream readers know
    where to look for workspace metadata.
    """
    name = _workspace_name(ws)
    rows = [
        ("Name", name),
        ("Slug", _field(ws, "slug")),
        ("Domain", _field(ws, "domain")),
        ("Stage", _field(ws, "stage")),
        ("Platforms", ", ".join(_list_field(ws, "platforms"))),
        ("Tech stack", ", ".join(_list_field(ws, "tech_stack"))),
        ("Repo", _field(ws, "repo")),
        ("Audience", _field(ws, "audience")),
        ("Pricing model", _field(ws, "pricing_model")),
        ("Launch target", _field(ws, "launch_target")),
        ("North star", _field(ws, "north_star")),
    ]
    description = _field(ws, "description")
    risks = _list_field(ws, "risks")

    lines = ["## Workspace facts", ""]
    lines.append("| Field | Value |")
    lines.append("| --- | --- |")
    for label, value in rows:
        if value:
            lines.append(f"| {label} | {value} |")
    if description:
        lines.append("")
        lines.append(f"**Description:** {description}")
    if risks:
        lines.append("")
        lines.append("**Known risks:**")
        for risk in risks:
            lines.append(f"- {risk}")
    return "\n".join(lines)


def _extra_context_section(extra_context: str) -> str:
    if not extra_context.strip():
        return ""
    return "\n\n## Extra context\n\n" + extra_context.strip()


def _output_format_footer(bullets: list[str]) -> str:
    items = "\n".join(f"- {b}" for b in bullets)
    return (
        "## Output format\n\n"
        "Respond in markdown. Use these sections, in this order:\n\n"
        f"{items}\n\n"
        "Be specific to this workspace — do not produce generic advice."
    )


# ---------------------------------------------------------------------------
# Local templates (always-usable copy/paste markdown)
# ---------------------------------------------------------------------------


def _local_launch_audit(ws: Any, *, extra_context: str) -> str:
    name = _workspace_name(ws)
    return (
        f"# Launch audit — {name}\n\n"
        f"## Launch audit\n\n"
        f"You are auditing **{name}** for launch readiness. Identify what is "
        f"ready, what is at risk, and what blocks shipping. Be concrete and "
        f"prioritise blockers over polish.\n\n"
        f"{_render_workspace_facts(ws)}\n\n"
        "## Audit checklist\n\n"
        "- Core user flow works end-to-end on the primary platform\n"
        "- Onboarding / first-run experience\n"
        "- Crash-free rate / error budget on the last 7 days\n"
        "- Auth, accounts, and account recovery\n"
        "- Payments / billing (if monetised)\n"
        "- Analytics + a single launch-week dashboard\n"
        "- Support channel + on-call rotation\n"
        "- Legal: ToS, privacy, store listings, required disclosures\n"
        "- Marketing site copy reflects the actual product\n"
        f"{_extra_context_section(extra_context)}\n\n"
        + _output_format_footer([
            "Executive verdict (one paragraph)",
            "Ready (bulleted)",
            "At risk (bulleted, with the specific risk)",
            "Blockers (bulleted, with the smallest unblocking step)",
            "Recommended launch window",
        ])
    )


def _local_blocker_fix(ws: Any, *, blocker: str, extra_context: str) -> str:
    name = _workspace_name(ws)
    blocker_line = blocker.strip() or "(blocker not specified — restate the blocker before continuing)"
    return (
        f"# Blocker fix — {name}\n\n"
        f"## Blocker fix\n\n"
        f"You are unblocking **{name}**. Stay narrowly focused on the single "
        f"blocker below. Do not refactor adjacent code, do not expand scope.\n\n"
        f"**Blocker:** {blocker_line}\n\n"
        f"{_render_workspace_facts(ws)}\n\n"
        "## Method\n\n"
        "- Reproduce the failure locally before changing code\n"
        "- Identify the smallest possible fix\n"
        "- Add or update one test that fails without the fix and passes with it\n"
        "- Verify no other tests regress\n"
        "- Open a draft PR with a one-paragraph summary\n"
        f"{_extra_context_section(extra_context)}\n\n"
        + _output_format_footer([
            "Root cause (one paragraph)",
            "Proposed fix (with file:line references)",
            "Test plan",
            "Risks of this fix",
            "Rollback plan",
        ])
    )


def _local_codex_review(ws: Any, *, diff_summary: str, extra_context: str) -> str:
    name = _workspace_name(ws)
    diff_block = diff_summary.strip() or "(diff summary not provided — paste the diff or summary before running)"
    return (
        f"# Codex review — {name}\n\n"
        f"## Codex review\n\n"
        f"You are reviewing a change to **{name}** as a Codex Task Packet "
        f"reviewer. Be the contrarian reviewer: surface weak assumptions, "
        f"missing tests, hidden coupling, and scope creep.\n\n"
        f"**Diff / change summary:**\n\n{diff_block}\n\n"
        f"{_render_workspace_facts(ws)}\n\n"
        "## Review angles\n\n"
        "- Correctness: does the change do what it claims?\n"
        "- Tests: are they testing the right thing, and would they fail before the fix?\n"
        "- Scope: is anything in this diff outside the stated mission?\n"
        "- Hidden coupling: does this lock in a decision that should stay flexible?\n"
        "- Security and PII handling\n"
        "- Rollback: can this be reverted cleanly?\n"
        f"{_extra_context_section(extra_context)}\n\n"
        + _output_format_footer([
            "Verdict (ship / revise / reject)",
            "Strengths",
            "Concerns (ranked)",
            "Required changes before merge",
            "Optional follow-ups",
        ])
    )


def _local_release_checklist(ws: Any, *, version: str, extra_context: str) -> str:
    name = _workspace_name(ws)
    version_line = version.strip() or "(next version)"
    return (
        f"# Release checklist — {name} {version_line}\n\n"
        f"## Release checklist\n\n"
        f"You are cutting release **{version_line}** of **{name}**. Go through "
        f"the checklist and call out anything not green.\n\n"
        f"{_render_workspace_facts(ws)}\n\n"
        "## Checklist\n\n"
        "- CHANGELOG / release notes drafted\n"
        "- Version bumped consistently (package files, docs, banners)\n"
        "- All CI checks green on the release branch\n"
        "- Smoke test of the primary user flow on the primary platform\n"
        "- Migrations are forward-and-back compatible\n"
        "- Feature flags default state is intentional\n"
        "- Rollback plan written and reviewed\n"
        "- Customer comms / changelog post drafted\n"
        "- On-call knows the release window\n"
        f"{_extra_context_section(extra_context)}\n\n"
        + _output_format_footer([
            "Go / no-go verdict",
            "Green items",
            "Yellow items (proceed with caveats)",
            "Red items (blockers)",
            "Post-release watch list",
        ])
    )


def _local_security_review(ws: Any, *, scope: str, extra_context: str) -> str:
    name = _workspace_name(ws)
    scope_line = scope.strip() or "(scope not specified — default to the full workspace surface)"
    return (
        f"# Security review — {name}\n\n"
        f"## Security review\n\n"
        f"You are running a scoped security review of **{name}**. Focus on "
        f"realistic threats for this workspace's domain and stage; do not "
        f"generate a generic OWASP recitation.\n\n"
        f"**Scope:** {scope_line}\n\n"
        f"{_render_workspace_facts(ws)}\n\n"
        "## Threat surfaces\n\n"
        "- AuthN / AuthZ (sessions, tokens, password reset, account takeover)\n"
        "- Data handling (PII, regulated data, retention, deletion)\n"
        "- Third-party dependencies and supply chain\n"
        "- Secret handling (env vars, keys, .env in repo, leaked tokens)\n"
        "- Input validation at trust boundaries\n"
        "- Logging: nothing sensitive in logs, screenshots, error pages\n"
        "- Rate limiting / abuse vectors\n"
        f"{_extra_context_section(extra_context)}\n\n"
        + _output_format_footer([
            "Highest-severity finding (one paragraph)",
            "Findings table (severity / area / one-line description)",
            "Required fixes before next release",
            "Tracked for later",
            "Suggested follow-up review cadence",
        ])
    )


def _local_mobile_readiness(ws: Any, *, target: str, extra_context: str) -> str:
    name = _workspace_name(ws)
    target_line = target.strip() or "android"
    return (
        f"# Mobile readiness — {name} ({target_line})\n\n"
        f"## Mobile readiness\n\n"
        f"You are reviewing **{name}** for mobile readiness on **{target_line}**. "
        f"Cover both code-level mobile concerns and store-listing readiness.\n\n"
        f"{_render_workspace_facts(ws)}\n\n"
        "## Mobile checklist\n\n"
        "- App boots cold-start under 3s on a mid-range device\n"
        "- Offline / poor-network behaviour is intentional\n"
        "- Permissions: only what's needed, with clear in-app rationale\n"
        "- Background work / battery footprint\n"
        "- Push notifications opt-in and meaningful\n"
        "- Crash reporting + symbolicated stack traces\n"
        "- Accessibility (screen reader, dynamic type, contrast)\n"
        "- Store listing: title, subtitle, screenshots, privacy nutrition label\n"
        "- Build signing + release track configured\n"
        f"{_extra_context_section(extra_context)}\n\n"
        + _output_format_footer([
            "Overall readiness (paragraph)",
            "Code-level issues",
            "Store-listing issues",
            "Required before submission",
            "Nice-to-have polish",
        ])
    )


def _local_pricing_strategy(ws: Any, *, audience: str, extra_context: str) -> str:
    name = _workspace_name(ws)
    audience_line = audience.strip() or _field(ws, "audience", default="(audience not specified)")
    return (
        f"# Pricing strategy — {name}\n\n"
        f"## Pricing strategy\n\n"
        f"You are setting pricing and positioning for **{name}**. Avoid "
        f"generic SaaS-pricing advice; tie every recommendation to this "
        f"workspace's audience, domain, and stage.\n\n"
        f"**Audience:** {audience_line}\n\n"
        f"{_render_workspace_facts(ws)}\n\n"
        "## Angles to cover\n\n"
        "- What the buyer is actually paying for (the job-to-be-done)\n"
        "- Pricing tiers and what justifies each tier\n"
        "- Anchor price + reference comparables\n"
        "- Free / trial / freemium decision and its cost\n"
        "- Annual vs monthly, with conversion incentives\n"
        "- Discounts that don't erode positioning\n"
        "- Refund / cancellation policy\n"
        f"{_extra_context_section(extra_context)}\n\n"
        + _output_format_footer([
            "Recommended pricing (concrete numbers)",
            "Tier structure with what's included",
            "Why this beats the current pricing",
            "What we'll measure to know if it's working",
            "Risks and what would force a re-price",
        ])
    )


def _local_investor_summary(ws: Any, *, audience: str, extra_context: str) -> str:
    name = _workspace_name(ws)
    audience_line = audience.strip() or "(prospective investor / partner)"
    return (
        f"# Investor / partner summary — {name}\n\n"
        f"## Investor summary\n\n"
        f"You are writing a tight investor / partner brief for **{name}**, "
        f"addressed to **{audience_line}**. Be specific and concrete — no "
        f"buzzwords, no padding.\n\n"
        f"{_render_workspace_facts(ws)}\n\n"
        "## Brief must cover\n\n"
        "- The problem in one sentence\n"
        "- Who it hurts and how much\n"
        "- What we do, in plain language\n"
        "- Why us — the unfair advantage\n"
        "- Stage and traction (real numbers)\n"
        "- Business model and unit economics\n"
        "- Why now\n"
        "- The ask\n"
        f"{_extra_context_section(extra_context)}\n\n"
        + _output_format_footer([
            "One-line pitch",
            "Problem and audience",
            "Solution and differentiator",
            "Traction (real numbers)",
            "The ask and use of funds / partnership terms",
        ])
    )


_LOCAL_BUILDERS = {
    "launch_audit": _local_launch_audit,
    "blocker_fix": _local_blocker_fix,
    "codex_review": _local_codex_review,
    "release_checklist": _local_release_checklist,
    "security_review": _local_security_review,
    "mobile_readiness": _local_mobile_readiness,
    "pricing_strategy": _local_pricing_strategy,
    "investor_summary": _local_investor_summary,
}


# ---------------------------------------------------------------------------
# Aux LLM polish (optional)
# ---------------------------------------------------------------------------


def _strip_code_fence(raw: str) -> str:
    """Strip surrounding markdown code fences from an LLM response."""
    if not raw:
        return ""
    stripped = raw.strip()
    if stripped.startswith("```"):
        stripped = _FENCE_RE.sub("", stripped)
    return stripped.strip()


_POLISH_SYSTEM_PROMPT = (
    "You are polishing a markdown prompt for the ACI portfolio.\n\n"
    "You will receive: (a) a workspace fact sheet as JSON, and (b) a "
    "draft markdown prompt. Your job is to tighten the language, fill in "
    "workspace-specific phrasing where the draft is generic, and return "
    "**only** the polished markdown.\n\n"
    "Strict rules:\n"
    "  - Preserve every section heading from the draft verbatim.\n"
    "  - Preserve the '## Output format' section verbatim.\n"
    "  - Preserve every bullet under '## Output format' verbatim.\n"
    "  - Do not add commentary, preamble, or closing remarks.\n"
    "  - Do not wrap your response in code fences.\n"
    "  - Return markdown ready to paste into Claude Code or Codex.\n"
)


def _workspace_to_json(ws: Any) -> str:
    """Serialize a workspace's known fields to JSON for the polish prompt."""
    payload = {
        "name": _field(ws, "name"),
        "slug": _field(ws, "slug"),
        "description": _field(ws, "description"),
        "domain": _field(ws, "domain"),
        "stage": _field(ws, "stage"),
        "platforms": _list_field(ws, "platforms"),
        "tech_stack": _list_field(ws, "tech_stack"),
        "repo": _field(ws, "repo"),
        "audience": _field(ws, "audience"),
        "pricing_model": _field(ws, "pricing_model"),
        "launch_target": _field(ws, "launch_target"),
        "north_star": _field(ws, "north_star"),
        "risks": _list_field(ws, "risks"),
    }
    payload = {k: v for k, v in payload.items() if v not in (None, "", [])}
    return json.dumps(payload, indent=2, sort_keys=True)


def _polish_with_aux(
    kind: str, ws: Any, local_template: str, *, timeout: int = 60
) -> tuple[bool, str, str]:
    """Polish ``local_template`` with the aux LLM.

    Returns ``(ok, reason, markdown)``. On any failure — import error,
    no configured client, API error, empty response — returns
    ``(False, reason, local_template)`` so the caller still gets usable
    markdown.
    """
    try:
        from agent.auxiliary_client import (  # type: ignore
            get_auxiliary_extra_body,
            get_text_auxiliary_client,
        )
    except Exception as exc:
        logger.debug("workspace_prompts: aux client import failed: %s", exc)
        return False, "aux_unavailable", local_template

    try:
        client, aux_model = get_text_auxiliary_client("workspace_prompts")
    except Exception as exc:
        logger.debug("workspace_prompts: get_text_auxiliary_client failed: %s", exc)
        return False, "aux_unavailable", local_template

    if client is None or not aux_model:
        return False, "aux_unavailable", local_template

    user_msg = (
        f"Prompt kind: {kind}\n\n"
        f"Workspace facts (JSON):\n{_workspace_to_json(ws)}\n\n"
        f"Draft markdown prompt to polish:\n\n{local_template}\n"
    )

    try:
        resp = client.chat.completions.create(
            model=aux_model,
            messages=[
                {"role": "system", "content": _POLISH_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=2000,
            timeout=timeout,
            extra_body=get_auxiliary_extra_body() or None,
        )
    except Exception as exc:
        logger.info("workspace_prompts: aux call failed: %s", exc)
        return False, f"aux_error: {type(exc).__name__}", local_template

    try:
        raw = resp.choices[0].message.content or ""
    except Exception:
        raw = ""

    polished = _strip_code_fence(raw)
    if not polished:
        return False, "aux_empty", local_template

    return True, "aux_ok", polished


# ---------------------------------------------------------------------------
# Public prompt functions
# ---------------------------------------------------------------------------


def _run(kind: str, ws: Any, local_template: str) -> WorkspacePromptOutcome:
    ok, reason, markdown = _polish_with_aux(kind, ws, local_template)
    return WorkspacePromptOutcome(
        kind=kind,
        workspace_name=_workspace_name(ws),
        ok=ok,
        reason=reason,
        prompt_markdown=markdown,
    )


def launch_audit_prompt(
    workspace: Any, *, extra_context: str = ""
) -> WorkspacePromptOutcome:
    """Pre-launch readiness audit prompt."""
    local = _local_launch_audit(workspace, extra_context=extra_context)
    return _run("launch_audit", workspace, local)


def blocker_fix_prompt(
    workspace: Any, *, blocker: str = "", extra_context: str = ""
) -> WorkspacePromptOutcome:
    """Focused single-blocker resolution prompt."""
    local = _local_blocker_fix(workspace, blocker=blocker, extra_context=extra_context)
    return _run("blocker_fix", workspace, local)


def codex_review_prompt(
    workspace: Any, *, diff_summary: str = "", extra_context: str = ""
) -> WorkspacePromptOutcome:
    """Codex Task Packet review prompt for a change to this workspace."""
    local = _local_codex_review(
        workspace, diff_summary=diff_summary, extra_context=extra_context
    )
    return _run("codex_review", workspace, local)


def release_checklist_prompt(
    workspace: Any, *, version: str = "", extra_context: str = ""
) -> WorkspacePromptOutcome:
    """Release / version-cut checklist prompt."""
    local = _local_release_checklist(
        workspace, version=version, extra_context=extra_context
    )
    return _run("release_checklist", workspace, local)


def security_review_prompt(
    workspace: Any, *, scope: str = "", extra_context: str = ""
) -> WorkspacePromptOutcome:
    """Scoped security review prompt."""
    local = _local_security_review(
        workspace, scope=scope, extra_context=extra_context
    )
    return _run("security_review", workspace, local)


def mobile_readiness_prompt(
    workspace: Any, *, target: str = "android", extra_context: str = ""
) -> WorkspacePromptOutcome:
    """Mobile / store-readiness review prompt."""
    local = _local_mobile_readiness(
        workspace, target=target, extra_context=extra_context
    )
    return _run("mobile_readiness", workspace, local)


def pricing_strategy_prompt(
    workspace: Any, *, audience: str = "", extra_context: str = ""
) -> WorkspacePromptOutcome:
    """Pricing + positioning packet prompt."""
    local = _local_pricing_strategy(
        workspace, audience=audience, extra_context=extra_context
    )
    return _run("pricing_strategy", workspace, local)


def investor_summary_prompt(
    workspace: Any, *, audience: str = "", extra_context: str = ""
) -> WorkspacePromptOutcome:
    """Investor / partner brief prompt."""
    local = _local_investor_summary(
        workspace, audience=audience, extra_context=extra_context
    )
    return _run("investor_summary", workspace, local)


_DISPATCH = {
    "launch_audit": launch_audit_prompt,
    "blocker_fix": blocker_fix_prompt,
    "codex_review": codex_review_prompt,
    "release_checklist": release_checklist_prompt,
    "security_review": security_review_prompt,
    "mobile_readiness": mobile_readiness_prompt,
    "pricing_strategy": pricing_strategy_prompt,
    "investor_summary": investor_summary_prompt,
}


def generate_prompt(
    workspace: Any, kind: str, **kwargs: Any
) -> WorkspacePromptOutcome:
    """Dispatch to the right per-kind prompt builder.

    ``kind`` must be one of :data:`PROMPT_KINDS`. Extra keyword arguments
    are forwarded to the per-kind function (e.g. ``blocker=`` for
    ``blocker_fix``, ``version=`` for ``release_checklist``).
    """
    if kind not in _DISPATCH:
        raise ValueError(
            f"unknown prompt kind: {kind!r}; expected one of {PROMPT_KINDS}"
        )
    return _DISPATCH[kind](workspace, **kwargs)


__all__ = [
    "PROMPT_KINDS",
    "WorkspacePromptOutcome",
    "generate_prompt",
    "launch_audit_prompt",
    "blocker_fix_prompt",
    "codex_review_prompt",
    "release_checklist_prompt",
    "security_review_prompt",
    "mobile_readiness_prompt",
    "pricing_strategy_prompt",
    "investor_summary_prompt",
]

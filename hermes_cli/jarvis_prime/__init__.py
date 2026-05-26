"""JARVIS Prime helpers — workspace-aware prompts, routing, operator glue.

This subpackage hosts the JARVIS Prime operating-layer helpers that live
inside the Hermes CLI. Each submodule is independently importable so
sibling waves can land in any order. In particular, this ``__init__``
deliberately does **not** import ``workspaces`` — that module is owned
by a separate wave and ``workspace_prompts`` is contracted not to
depend on it.
"""

from __future__ import annotations

from hermes_cli.jarvis_prime.workspace_prompts import (
    PROMPT_KINDS,
    WorkspacePromptOutcome,
    blocker_fix_prompt,
    codex_review_prompt,
    generate_prompt,
    investor_summary_prompt,
    launch_audit_prompt,
    mobile_readiness_prompt,
    pricing_strategy_prompt,
    release_checklist_prompt,
    security_review_prompt,
)

__all__ = [
    "PROMPT_KINDS",
    "WorkspacePromptOutcome",
    "blocker_fix_prompt",
    "codex_review_prompt",
    "generate_prompt",
    "investor_summary_prompt",
    "launch_audit_prompt",
    "mobile_readiness_prompt",
    "pricing_strategy_prompt",
    "release_checklist_prompt",
    "security_review_prompt",
]

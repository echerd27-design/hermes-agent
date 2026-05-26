# Wave 13 — Workspace Prompt Generator

**Branch:** `aci/wave-13-workspace-prompt-generator`
**Mode:** `/builder`
**PR style:** Draft only.

## Mission

Create a workspace-aware prompt generator for ACI product build/review
tasks. Any caller — JARVIS Prime router, Slack handler, kanban planner —
hands in a workspace record and a prompt kind, and gets back a polished,
copy/paste-safe markdown prompt ready for Claude Code, Codex, or Slack.

## Files Changed

| Path | Status | Purpose |
| --- | --- | --- |
| `hermes_cli/jarvis_prime/__init__.py` | new | Subpackage marker; re-exports the public API of `workspace_prompts`. Deliberately does not import `workspaces.py`. |
| `hermes_cli/jarvis_prime/workspace_prompts.py` | new | The eight prompt builders, the `WorkspacePromptOutcome` dataclass, the `generate_prompt` dispatcher, the duck-typed workspace adapter, and the optional aux-LLM polish step. |
| `tests/test_jarvis_prime_workspace_prompts.py` | new | 29 tests covering all four named ACI workspaces, all eight prompt kinds, both input shapes, every aux-client failure mode, and the wave's no-import-of-workspaces contract. |
| `docs/aci/reports/W13_WORKSPACE_PROMPT_GENERATOR.md` | new | This report. |

No other files were touched. All four allowed paths in the wave
contract are populated; every forbidden path remains unmodified.

## Prompt Kinds & Signatures

```python
from hermes_cli.jarvis_prime import (
    PROMPT_KINDS,
    WorkspacePromptOutcome,
    generate_prompt,
    launch_audit_prompt,         # (workspace, *, extra_context="")
    blocker_fix_prompt,          # (workspace, *, blocker="", extra_context="")
    codex_review_prompt,         # (workspace, *, diff_summary="", extra_context="")
    release_checklist_prompt,    # (workspace, *, version="", extra_context="")
    security_review_prompt,      # (workspace, *, scope="", extra_context="")
    mobile_readiness_prompt,     # (workspace, *, target="android", extra_context="")
    pricing_strategy_prompt,     # (workspace, *, audience="", extra_context="")
    investor_summary_prompt,     # (workspace, *, audience="", extra_context="")
)
```

`PROMPT_KINDS = ("launch_audit", "blocker_fix", "codex_review", "release_checklist", "security_review", "mobile_readiness", "pricing_strategy", "investor_summary")`.

`generate_prompt(workspace, kind, **kwargs)` dispatches by kind and
raises `ValueError` for unknown kinds.

## Workspace Contract (Duck-Typed)

The module accepts any object satisfying either `Mapping.get(key)` or
`getattr(obj, key, default)`. Plain dicts, `SimpleNamespace`, and
dataclasses all work identically. Recognised keys (every one optional,
every one safely defaulted):

```
name, slug, description, domain, stage, platforms, tech_stack, repo,
audience, pricing_model, launch_target, north_star, risks
```

The module **does not import** `hermes_cli/jarvis_prime/workspaces.py`.
A test (`test_does_not_import_workspaces_module`) and a static check in
the verification commands enforce this.

## Aux-LLM Polish (Optional Enhancement)

Each builder first renders a deterministic local markdown template, then
attempts to polish it via `agent.auxiliary_client.get_text_auxiliary_client`.
Behaviour:

| Aux state | `ok` | `reason` | `prompt_markdown` |
| --- | --- | --- | --- |
| Polish succeeds | `True` | `"aux_ok"` | LLM output, code fences stripped |
| Aux unimportable / unconfigured | `False` | `"aux_unavailable"` | Local template (verbatim) |
| Aux API call raises | `False` | `"aux_error: <ExcType>"` | Local template (verbatim) |
| Aux returns empty string | `False` | `"aux_empty"` | Local template (verbatim) |

Callers always get usable markdown — the LLM is an enhancement, never a
dependency.

## Tests Run

```text
$ uv run --frozen --with pytest-xdist --with pytest-timeout \
    pytest tests/test_jarvis_prime_workspace_prompts.py -v
============================== 29 passed in 2.35s ==============================
```

Coverage matrix:

- All 4 named workspaces (Nourish, HazMat Command, Hey Jay, Hermes Core)
  exercise the `launch_audit` builder and assert their `name`, `domain`,
  at least one platform, and audience appear in the rendered markdown.
- All 8 prompt kinds exercise the dispatcher with Nourish and assert
  their distinctive section heading, the shared `## Workspace facts`
  block, and the shared `## Output format` footer are present.
- Both input shapes (`dict` and `SimpleNamespace`) produce byte-identical
  output for the same data.
- Aux client success / runtime error / no-client / empty-response paths
  are each covered.
- Per-kind keyword arguments (`blocker`, `version`, `diff_summary`,
  `target`, `extra_context`) surface in the rendered markdown.
- The forbidden import is asserted absent from `sys.modules`.

## Verification

```bash
python -m compileall hermes_cli/jarvis_prime/workspace_prompts.py hermes_cli/jarvis_prime/__init__.py
uv run --frozen --with pytest-xdist --with pytest-timeout \
    pytest tests/test_jarvis_prime_workspace_prompts.py -v
uv run --frozen python -c "from hermes_cli.jarvis_prime import generate_prompt, PROMPT_KINDS; \
    print(generate_prompt({'name': 'Nourish', 'domain': 'nutrition'}, 'launch_audit').prompt_markdown[:400])"
uv run --frozen python -c "import hermes_cli.jarvis_prime.workspace_prompts; import sys; \
    assert 'hermes_cli.jarvis_prime.workspaces' not in sys.modules, 'forbidden import'"
```

All four pass.

## Remaining Risks

- **Aux-client coupling.** The polish step lazy-imports from
  `agent.auxiliary_client`. If that surface is renamed, polish silently
  falls back to the local template — tests will catch the break via the
  patched-aux assertions.
- **No caller wired in this wave.** By design — Wave 13 ships the
  surface only. JARVIS Prime / kanban / Slack integrations are deferred
  to later waves so this wave can land independently.
- **Recognised-field schema is not enforced.** Workspaces with
  unexpected field names render with those facts absent; no error is
  raised. This is intentional duck-typing, but a future wave that
  formalises the workspace schema may want to align names.

## Rollback Plan

```bash
git rm hermes_cli/jarvis_prime/workspace_prompts.py
git rm hermes_cli/jarvis_prime/__init__.py
git rm tests/test_jarvis_prime_workspace_prompts.py
git rm docs/aci/reports/W13_WORKSPACE_PROMPT_GENERATOR.md
git commit -m "Revert Wave 13"
```

No other files were touched, so reverting is a clean delete of the four
new files (and removing the empty `hermes_cli/jarvis_prime/` and
`docs/aci/reports/` directories if no sibling wave has populated them).

## PR Summary

> Wave 13: workspace-aware prompt generator. Adds
> `hermes_cli/jarvis_prime/workspace_prompts.py` with 8 prompt kinds
> (launch audit, blocker fix, Codex review, release checklist, security
> review, Android/mobile readiness, pricing strategy, investor summary),
> each returning a `WorkspacePromptOutcome` with always-usable markdown
> (LLM-polished when the aux client is reachable, deterministic local
> template otherwise). Accepts any workspace via duck-typed dict/object
> access. Does not import `workspaces.py`. 29 tests cover Nourish,
> HazMat Command, Hey Jay, and Hermes Core.

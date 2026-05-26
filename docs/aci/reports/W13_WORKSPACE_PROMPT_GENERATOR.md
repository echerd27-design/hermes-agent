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

## Out-of-Scope CI Failures (Pre-Existing, Not Touched by This Wave)

After rebasing onto current main (`7e70c6f`, which fixed the systemd /
CA-bundle headless-runner test failures), the `test` CI job on PR #57
still reports **2 failures out of 24,453 collected** (run
`26476416361`). Both are in test files outside Wave 13's ALLOWED FILES
list, neither imports anything this wave adds, and both reproduce on
main HEAD with no Wave 13 code present. Per the wave's non-overlap
contract ("If you discover a required change outside allowed files,
stop and write it in the wave report instead of editing it"), they
are documented here and **not** fixed in this PR.

### 1. `tests/hermes_cli/test_update_hangup_protection.py::TestInstallHangupProtection::test_wraps_stdout_and_stderr_with_mirror`

```text
AssertionError: assert False
```

PR #6 previously fixed test-ordering pollution on this exact test
(`importlib.reload(hermes_cli.main)` in `test_curator_recent_run_notice`
swaps the `_UpdateOutputStream` class identity, and the test's
module-top import captured the pre-reload identity, so `isinstance`
returned False). The fix was to re-import inside the test method. The
fact that this is failing again suggests either (a) another test now
performs a similar reload, or (b) the fix regressed during a merge.
Recommended follow-up: re-audit any test that calls
`importlib.reload(hermes_cli.main)` and confirm the in-method re-import
is still present.

### 2. `tests/run_agent/test_primary_runtime_restore.py::TestTryRecoverPrimaryTransport::test_wait_time_scales_with_retry_count`

```text
AssertionError: Expected 'sleep' to be called once. Called 67085 times.
```

The mock for `sleep` is collecting tens of thousands of `call(1)`
invocations before the test fails. Likely cause: the test patches the
wrong symbol (e.g., a `sleep` imported into another module via `from
time import sleep` rather than the one the retry loop actually calls),
or the retry path was refactored to use a different sleep entry-point
without updating the test target. Recommended follow-up: locate the
retry loop's actual `sleep` call site and update the patch target.

### Why this isn't fixed in this PR

Both files are forbidden by the Wave 13 contract:

> NON-OVERLAP CONTRACT:
> - Modify only the files listed under ALLOWED FILES.
> - Do not touch another wave's files.
> - If you discover a required change outside allowed files, stop and
>   write it in the wave report instead of editing it.

The four ALLOWED FILES are exhaustively listed at the top of this
report and neither of these two test files is among them. The fixes
belong in a separate maintenance PR.

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

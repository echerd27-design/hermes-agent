# W13: Jarvis Prime Context Engine — Wave Report

**Status:** Draft. Do not merge to `main`. No deploys, DNS changes,
secret rotation, money actions, or app-store submissions involved.

## Mission

Build the internal TokenJuice-equivalent compression layer for Jarvis
Prime model and tool payloads, as a stateless stdlib-only library that
later waves will wire into the runtime. The library lives at
`hermes_cli/context/`; design rationale is in
[`docs/aci/jarvis-prime/JARVIS_CONTEXT_ENGINE.md`](../jarvis-prime/JARVIS_CONTEXT_ENGINE.md).

## Universal header confirmation

- **Branch:** `claude/charming-mccarthy-ra3XO` (logical wave name `aci/jarvis-prime-13-context-engine`).
- **Started from:** `origin/main` (commit `7b82077`).
- **Allowed files modified, exhaustively:**
  - `hermes_cli/context/__init__.py`
  - `hermes_cli/context/context_packet.py`
  - `hermes_cli/context/context_engine.py`
  - `hermes_cli/context/redaction.py`
  - `tests/test_context_packet.py`
  - `tests/test_context_engine.py`
  - `tests/test_context_redaction.py`
  - `docs/aci/jarvis-prime/JARVIS_CONTEXT_ENGINE.md`
  - `docs/aci/reports/W13_CONTEXT_ENGINE_REPORT.md`
- **Forbidden files untouched** (verified via `git diff --name-only`):
  `apps/android/**`, `hermes_cli/jarvis_prime/runtime.py`, `…/router.py`,
  `hermes_cli/model_router.py`, `hermes_cli/memory_tree/**`,
  `docs/ai-intelligence/model-registry.yaml`, `skills/**`, `README.md`,
  `pyproject.toml`, `uv.lock`, `.github/**`.
- **No secrets** in source, tests, fixtures, docs, or this report.
  Adversarial test payloads use synthetic shapes only (`sk-abcdef…`,
  `ghp_0123…`, `AKIAIOSFODNN7EXAMPLE`, etc.).
- **Open-PR collision check:** GitHub MCP `list_pull_requests` returned 10
  open draft PRs (#9 – #18). None touch `hermes_cli/context/**`,
  `tests/test_context_*.py`, `docs/aci/jarvis-prime/**`, or
  `docs/aci/reports/W13_*`. Wave PRs #11/#13/#15/#16/#17 touch
  `hermes_cli/jarvis_prime/**`, which is **outside** this wave's allowed
  set and is unmerged to `main`.

## Changed files

9 new files, 0 modified, 0 deleted.

| Path | Lines | Purpose |
|---|---|---|
| `hermes_cli/context/__init__.py` | 38 | Public-surface re-exports. |
| `hermes_cli/context/context_packet.py` | 84 | `ContextPacket` frozen dataclass + `to_dict` / `from_dict`. |
| `hermes_cli/context/context_engine.py` | 627 | 7 `compress_*` pure functions + shared evidence extractor. |
| `hermes_cli/context/redaction.py` | 147 | `SECRET_PATTERNS`, `scrub()`, `reject()`. |
| `tests/test_context_packet.py` | 89 | 8 tests covering dataclass, ratio, round-trip. |
| `tests/test_context_engine.py` | 417 | 167 tests covering 7 compressors + secrets-never-leak (42-case parametrize) + cross-cutting invariants. |
| `tests/test_context_redaction.py` | 166 | 27 tests covering every secret pattern, multi-secret counting, and `reject`. |
| `docs/aci/jarvis-prime/JARVIS_CONTEXT_ENGINE.md` | 168 | Design doc: API, compression rules, redaction policy, module-disambiguation. |
| `docs/aci/reports/W13_CONTEXT_ENGINE_REPORT.md` | (this file) | Wave report. |

## Tests run

```
$ pytest -o addopts="" tests/test_context_packet.py tests/test_context_engine.py tests/test_context_redaction.py
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-9.0.2, pluggy-1.6.0
rootdir: /home/user/hermes-agent
configfile: pyproject.toml
collected 202 items
…
============================= 202 passed in 2.71s ==============================
```

`pyproject.toml:240` configures `addopts = "-m 'not integration' -n auto
--timeout=30 --timeout-method=signal"`, which assumes `pytest-xdist` and
`pytest-timeout` are installed. The override `-o addopts=""` is required
in container environments without those plugins; the underlying test
suite is identical either way. This precedent is established in PR #16
(wave W07).

```
$ python -m compileall hermes_cli/context
Listing 'hermes_cli/context'...
```

## Acceptance criteria → test mapping

| Header criterion | Where covered |
|---|---|
| Stdlib-only | `hermes_cli/context/{__init__,context_packet,context_engine,redaction}.py` import only `dataclasses`, `typing`, `json`, `re`. No third-party imports. |
| Tests cover all 7 payload types | `tests/test_context_engine.py` has one class per compressor: `TestCompressText`, `TestCompressMarkdown`, `TestCompressJSON`, `TestCompressLog`, `TestCompressDiff`, `TestCompressTestOutput`, `TestCompressStackTrace`. |
| Tests prove stack traces preserved | `tests/test_context_engine.py::TestCompressStackTrace::{test_every_file_line_frame_preserved_verbatim, test_recursive_frames_collapsed_with_count_marker, test_final_exception_line_preserved, test_unique_frames_not_collapsed}`. |
| Tests prove test names preserved | `tests/test_context_engine.py::TestCompressTestOutput::{test_failed_test_ids_preserved_in_payload, test_failed_test_ids_preserved_in_evidence_as_test_id_kind}`. |
| Tests prove obvious secrets redacted/rejected | `tests/test_context_redaction.py::TestRedactionScrub` (16 patterns), `TestRedactionReject` (3 cases), and `tests/test_context_engine.py::TestSecretsNeverLeak` (parametrize over 7 compressors × 6 secret shapes = 42 cases × 3 assertions = 126 invocations of the never-leak invariant). |
| Not wired into runtime yet | `grep -RIn 'from hermes_cli\.context\|import hermes_cli\.context' …` over `hermes_cli/`, `agent/`, `tools/`, `gateway/`, `tui_gateway/`, `web/`, `apps/`, `acp_adapter/`, `acp_registry/`, `providers/`, `plugins/`, `cron/`, plus root-level scripts (`cli.py`, `mcp_serve.py`, `model_tools.py`, `run_agent.py`, `batch_runner.py`, `hermes_bootstrap.py`, `mini_swe_runner.py`, `toolsets.py`, `toolset_distributions.py`, `trajectory_compressor.py`, `utils.py`) returns empty. |

## Verification command outputs

```
$ git diff --cached --name-only \
    | grep -Ev '^(hermes_cli/context/[^/]+\.py|tests/test_context_[a-z_]+\.py|docs/aci/jarvis-prime/JARVIS_CONTEXT_ENGINE\.md|docs/aci/reports/W13_CONTEXT_ENGINE_REPORT\.md)$' \
    | grep . && echo FAIL || echo OK
OK: scope clean

$ grep -RIn 'from hermes_cli\.context\|import hermes_cli\.context' \
    hermes_cli/ agent/ tools/ gateway/ tui_gateway/ web/ apps/ \
    acp_adapter/ acp_registry/ providers/ plugins/ cron/ \
    cli.py mcp_serve.py model_tools.py run_agent.py batch_runner.py \
    hermes_bootstrap.py mini_swe_runner.py toolsets.py toolset_distributions.py \
    trajectory_compressor.py utils.py 2>/dev/null \
    && echo FAIL || echo OK
OK: not wired
```

## Risks

1. **Evidence-preservation regex drift.** Real-world stack traces, logs,
   and test outputs that don't match the assumed shape silently lose
   evidence. Mitigation in this wave: explicit fixtures for recursion
   tracebacks, multi-frame tracebacks, ANSI-coloured logs, pytest progress
   lines. Adversarial fixtures for Windows-style paths and pytest
   collection-error variants are a known gap and a follow-up wave should
   add them.
2. **Redaction pattern lag vs `agent/redact.py`.** This wave mirrors ~13
   of the ~35 vendor prefixes catalogued in `agent/redact.py`. A new
   vendor leak is not blocked by W13 redaction until a follow-up sync
   wave. Documented in the design doc "Mirror lag" section.
3. **"Not wired" easy to violate downstream.** Future-wave PRs could land
   an import in `cli.py` / `mcp_serve.py`. Verification step 4 above
   guards this wave; downstream waves must add the same check.
4. **Stdlib `re` performance on very large inputs.** No DoS surface in
   W13 (no network, no untrusted producer wiring). A future runtime-wire
   wave must add an input-size cap at the call site. Documented in the
   design doc adoption notes.
5. **Slack `xapp-` divergence from `agent/redact.py`.** W13 redaction
   catches Slack app-level tokens (`xapp-`) while `agent/redact.py:78`
   does not. The improvement should be backported in a follow-up wave so
   the two modules don't drift further.

## Rollback

```bash
rm -rf hermes_cli/context
rm -f tests/test_context_packet.py tests/test_context_engine.py tests/test_context_redaction.py
rm -f docs/aci/jarvis-prime/JARVIS_CONTEXT_ENGINE.md
rm -f docs/aci/reports/W13_CONTEXT_ENGINE_REPORT.md
rmdir docs/aci/jarvis-prime 2>/dev/null || true
rmdir docs/aci/reports docs/aci 2>/dev/null || true
```

Then close the draft PR. No runtime state, no migrations, no external
services touched.

## Open questions / out of scope

- Runtime wiring (separate later wave).
- Token-aware sizing (separate layer above the engine if needed).
- Streaming compression (engine takes whole payloads).
- LLM-driven summarization (belongs in `agent/context_compressor.py`).

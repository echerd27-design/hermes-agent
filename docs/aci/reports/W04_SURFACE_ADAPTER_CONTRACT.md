# W04 — Surface Adapter Contract for JARVIS Prime Turn Results

## Mission

Define a single runtime contract — `JarvisTurn` plus five surface
adapter helpers — that CLI, Slack, Android, Termux, and voice flows can
all consume without re-deriving formatting per surface. Establish the
contract once so later waves can wire it into `hermes_cli/main.py`, the
gateway platform adapters under `gateway/platforms/`, and the Android
client without each callsite inventing its own rendering.

## Branch

- Logical wave branch: `aci/wave-04-surface-adapter-contract`
- Session branch (actual git ref): `claude/hopeful-goodall-yvKgC`

## Changed files

All four files are new — no existing files were modified.

| Path | Status |
|------|--------|
| `hermes_cli/jarvis_prime/__init__.py` | new |
| `hermes_cli/jarvis_prime/surfaces.py` | new |
| `tests/test_jarvis_prime_surfaces.py` | new |
| `docs/aci/reports/W04_SURFACE_ADAPTER_CONTRACT.md` | new (this file) |

No edits to `gateway/**`, `apps/android/**`, `hermes_cli/main.py`,
`pyproject.toml`, `uv.lock`, or `README.md`.

## Design summary

`hermes_cli/jarvis_prime/surfaces.py` defines:

- `JarvisTurn` — frozen `@dataclass` holding the operating-layer turn.
- `to_cli`, `to_slack`, `to_android`, `to_termux`, `to_voice` — pure
  functions, one per surface.
- `SURFACES` — mapping of surface name to adapter callable.
- `render(surface, turn)` — dispatcher that raises `ValueError` on
  unknown surface names.
- `SLACK_MAX = 600`, `TERMUX_MAX = 280`, `VOICE_MAX = 240` — length
  caps exposed as module constants so future waves can tune them
  without changing the adapter API.

`hermes_cli/jarvis_prime/__init__.py` re-exports the public surface so
callers can write `from hermes_cli.jarvis_prime import JarvisTurn, render`.

The module is stdlib-only: it imports `dataclasses`, `collections.abc`,
and `typing`. No network calls, no I/O, no logging, no third-party
dependencies.

## `JarvisTurn` schema

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `mission` | `str` | required | One-line statement of what the turn is doing. |
| `summary` | `str` | `""` | Main response body. Adapters truncate for short surfaces. |
| `route` | `str` | `"direct"` | Where JARVIS routed the turn: `direct`, `aos_council`, `claude_code`, `codex`, `mobile_voice`. |
| `mode` | `str` | `"operator"` | JARVIS mode: `companion`, `strategy`, `critic`, `operator`, `builder`, `mobile_voice`. |
| `actions` | `tuple[str, ...]` | `()` | Next concrete actions. |
| `verification` | `tuple[str, ...]` | `()` | Verification evidence lines (tests run, gates passed). |
| `risks` | `tuple[str, ...]` | `()` | Named residual risks. |
| `rollback` | `str` | `""` | Rollback path description. |
| `task_packet` | `Mapping[str, Any] \| None` | `None` | Optional structured resumable packet for mobile voice. |

Tuples (not lists) keep the dataclass safely immutable and avoid the
mutable-default-factory pitfall.

### Naming distinction from `agent.transports.codex_app_server_session.TurnResult`

The lower-level Codex transport defines its own
`TurnResult` at `agent/transports/codex_app_server_session.py:64`
with fields `final_text`, `projected_messages`, `tool_iterations`,
`interrupted`, `error`, `turn_id`, `thread_id`, `should_retire`. That
type models a single user→assistant→tool runtime cycle.

`JarvisTurn` is intentionally a different type at a different layer.
A JARVIS turn can be produced *from* a Codex `TurnResult` upstream, but
the operating-layer contract used by surface adapters is `JarvisTurn`.
Future waves must not collapse the two.

## Adapter table

| Surface | Return type | Length cap | Key constraint |
|---------|-------------|------------|----------------|
| `cli` | `str` | none | Always includes `Route:` and `Verification:` lines, even when fields are empty. Full Coding/Operator Mode block. |
| `slack` | `str` | `SLACK_MAX = 600` | Compact Slack mrkdwn. Single-`*` bold (not `**`). Word-boundary truncation. |
| `android` | `dict[str, Any]` | n/a | Flat snake_case keys mirroring `JarvisTurn`. JSON round-trippable with no custom encoder. |
| `termux` | `str` | `TERMUX_MAX = 280` | ASCII-only via `encode("ascii", "replace")`. No Unicode box-drawing, no ANSI. |
| `voice` | `str` | `VOICE_MAX = 240` | No markdown symbols (`*`, `_`, `` ` ``, `#`, `>` stripped). Sentence form for TTS. |

## Tests run

```bash
.venv/bin/pytest tests/test_jarvis_prime_surfaces.py -v
```

Result: **25 passed in 2.54s** (17 test definitions; `pytest.mark.parametrize`
expands `test_render_dispatches_each_surface` and
`test_minimal_turn_renders_cleanly` over all 5 surfaces).

Coverage by acceptance criterion:

| Acceptance criterion | Test(s) |
|----------------------|---------|
| No network calls | Module imports only stdlib; verified by `compileall` and import smoke. |
| No dependencies | Source uses only `dataclasses`, `collections.abc`, `typing`. |
| Tests cover all surfaces | `test_render_dispatches_each_surface[*]` (5 parametrized), `test_minimal_turn_renders_cleanly[*]` (5 parametrized), plus per-surface specific tests. |
| Mobile/voice output stays short | `test_to_termux_under_max_length`, `test_to_voice_under_max_length`, `test_long_summary_is_truncated_on_short_surfaces`. |
| Full CLI output includes route and verification | `test_to_cli_includes_route_and_verification_even_when_empty`, `test_to_cli_full_output_contains_all_sections`. |

## Verification results

| Command | Result |
|---------|--------|
| `python -m compileall hermes_cli/jarvis_prime/surfaces.py` | pass |
| `python -m compileall hermes_cli/jarvis_prime/__init__.py` | pass |
| `pytest tests/test_jarvis_prime_surfaces.py -v` | 25 passed |
| Smoke import: `from hermes_cli.jarvis_prime import JarvisTurn, render; render('cli', JarvisTurn(mission='ping'))` | output contains `Route:` and `Verification:` |
| `git diff --check` | clean |

## Remaining risks

- **Shape drift in later waves.** `JarvisTurn` is frozen and its field
  set is documented here. Any field addition is a follow-up wave so the
  contract stays stable for downstream consumers.
- **Length caps may need tuning.** `SLACK_MAX`, `TERMUX_MAX`, and
  `VOICE_MAX` are module constants; a later wave that wires the gateway
  Slack adapter can adjust them without touching the adapter API.
- **Slack mrkdwn vs. Block Kit.** This wave emits mrkdwn text only.
  A future wave wiring the gateway Slack adapter may add an alternate
  Block Kit JSON renderer alongside `to_slack`.
- **No callsite wiring.** This wave defines the contract only. `to_*`
  functions are unused by the rest of the codebase until later waves
  wire them into CLI / Slack / Android / gateway.

## Rollback plan

Because no existing files were modified, rollback is a pure deletion:

```bash
rm -rf hermes_cli/jarvis_prime/
rm tests/test_jarvis_prime_surfaces.py
rm docs/aci/reports/W04_SURFACE_ADAPTER_CONTRACT.md
# If the docs/aci/reports/ directory is now empty, optionally:
rmdir docs/aci/reports docs/aci
```

No merge conflicts, no downstream caller impact (nothing imports the
new module yet).

## PR summary

Draft PR title: `aci/wave-04: surface adapter contract for JARVIS Prime turn results`

Body bullets:

- Adds `hermes_cli.jarvis_prime` package with the `JarvisTurn`
  dataclass and five pure-function surface adapters (cli, slack,
  android, termux, voice) plus a `render(surface, turn)` dispatcher.
- Stdlib only. No network, no third-party deps, no callsite wiring.
- 25 tests pass under the project's pytest-xdist + pytest-timeout
  configuration.
- Naming chosen as `JarvisTurn` to avoid collision with the
  lower-level Codex transport `TurnResult` at
  `agent/transports/codex_app_server_session.py:64`.

## Out-of-scope items discovered

None. The wave's ALLOWED FILES, ACCEPTANCE CRITERIA, and VERIFY block
were sufficient and unambiguous. Future waves will be needed to:

- wire `to_cli` into `hermes_cli/main.py` (W05+),
- wire `to_slack` and `to_android` into `gateway/platforms/`
  adapters (W06+),
- wire `to_termux` and `to_voice` into the Android cockpit and
  voice flows (W07+),
- consider an alternate Slack Block Kit renderer alongside `to_slack`
  if/when richer Slack output is needed.

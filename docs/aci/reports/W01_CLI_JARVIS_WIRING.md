# Wave 01 — CLI JARVIS Slash Wiring

**Branch:** `aci/wave-01-cli-jarvis-slash`
**Date:** 2026-05-26
**Status:** Adapter shipped + runnable via `hermes jarvis …`; interactive REPL wiring deferred to Wave 02 (documented below).

---

## 1. Scope & contract

This wave adds a thin Python landing pad for **JARVIS Prime** so the
intended slash commands have a real, callable surface in the CLI
without touching the gateway, Android client, packaging, or the
existing interactive slash dispatcher.

**Allowed files (edited only):**

- `hermes_cli/jarvis_prime/**` *(new package)*
- `hermes_cli/main.py` *(one new `cmd_jarvis` + subparser block;
  `jarvis` registered in `_BUILTIN_SUBCOMMANDS`)*
- `tests/test_jarvis_prime_cli_commands.py` *(new)*
- `docs/aci/reports/W01_CLI_JARVIS_WIRING.md` *(this file)*

**Read-only / out of scope this wave:**

- `cli.py` (interactive REPL & slash dispatcher; `HermesCLI.process_command`)
- `hermes_cli/commands.py` (`COMMAND_REGISTRY`, `CommandDef`, `resolve_command`)
- `gateway/**`, `apps/android/**`, `pyproject.toml`, `uv.lock`,
  `README.md`, `.github/**`

---

## 2. What shipped

### 2.1 `hermes_cli/jarvis_prime/` package

Thin, dependency-free adapter that mirrors the six modes defined in
`skills/jarvis-prime/SKILL.md`.

| Module | Purpose |
|---|---|
| `modes.py` | `Mode(str, Enum)` — COMPANION, STRATEGY, CRITIC, OPERATOR, BUILDER, MOBILE_VOICE, AUTO. `NAMED_MODES` tuple. |
| `persona.py` | `DEFAULT_RESPONSE_FORMAT` + `OPERATIONAL_HANDOFF_FORMAT` quoted verbatim from `skills/jarvis-prime/SKILL.md` lines 73–94. `Persona` dataclass + `header_for(mode)` for the six named modes. |
| `classifier.py` | `ModeClassifier.classify(text) -> Mode`. Keyword heuristic — no LLM, no network. Default: `COMPANION`. |
| `router.py` | `Router.route(mode, text) -> RouteResult`. Picks `OPERATIONAL_HANDOFF_FORMAT` for OPERATOR/BUILDER, `DEFAULT_RESPONSE_FORMAT` otherwise. Rejects `AUTO` with `ValueError`. |
| `slash.py` | `SLASH_COMMANDS: dict[str, Mode]`, `dispatch(line) -> DispatchResult \| None`. `None` for unknown / non-slash / `/voice <subcommand>` — preserving existing behavior. |
| `__init__.py` | Re-exports the public surface. |

**Public API (importable today):** `Mode`, `ModeClassifier`, `Router`,
`RouteResult`, `Persona`, `SLASH_COMMANDS`, `dispatch`,
`DispatchResult`, `DEFAULT_RESPONSE_FORMAT`,
`OPERATIONAL_HANDOFF_FORMAT`, `header_for`, `NAMED_MODES`.

**Note on naming:** the task brief named four "existing" classes —
`JarvisPrime`, `ModeClassifier`, `Router`, `Persona`. Only the latter
three are introduced here as thin scaffolds; `JarvisPrime` is *not*
created as a separate class because the package itself plays that role
(see `__init__.py`'s public surface). If a future wave needs an
explicit `JarvisPrime` façade, it can wrap these primitives without
breaking imports.

### 2.2 `hermes_cli/main.py` argparse wiring

Three localized edits:

1. Added `"jarvis"` to the `_BUILTIN_SUBCOMMANDS` frozenset so plugin
   discovery is correctly skipped for `hermes jarvis …`.
2. Added `cmd_jarvis(args)` immediately after `cmd_model` — imports
   from `hermes_cli.jarvis_prime` lazily and prints the resolved mode,
   persona header, response-format template, and the payload.
3. Added a `jarvis_parser = subparsers.add_parser("jarvis", …)` block
   immediately after `model_parser.set_defaults(func=cmd_model)`,
   following the exact pattern used by `model`, `gateway`,
   `fallback`, etc.

End-to-end runnable today:

```
hermes jarvis /builder "ship the PR"
hermes jarvis /critic "this plan is too broad"
hermes jarvis /jarvis "code something for me"      # AUTO → BUILDER
hermes jarvis "I feel stuck this week"             # free-text → COMPANION
```

### 2.3 Tests

`tests/test_jarvis_prime_cli_commands.py` — **51 tests, all passing**
locally. Coverage:

- Slash → mode table (10 parametrized cases).
- Dispatch on concrete-mode slashes (6 cases).
- AUTO autoclassification via `/jarvis`, `/jp`, `/jarvis-prime`.
- Unknown / non-slash / non-string inputs return `None` (7 cases).
- `/voice` precedence: subcommand tokens (`on|off|tts|status`,
  case-insensitive) defer; bare `/voice` maps to Mobile Voice.
- Classifier heuristics for all six named modes.
- Router format selection (default vs operational handoff).
- Persona header uniqueness across the six named modes.
- AUTO rejection by Router and `header_for`.
- `cmd_jarvis` argparse glue: known slash, unknown slash, free-text
  classification, `/voice on` deferral.

---

## 3. Slash → Mode mapping (source of truth)

| Slash command | JARVIS mode |
|---|---|
| `/jarvis`, `/jp`, `/jarvis-prime` | `AUTO` → `ModeClassifier` on payload |
| `/builder` | `BUILDER` |
| `/operator` | `OPERATOR` |
| `/strategy` | `STRATEGY` |
| `/critic` | `CRITIC` |
| `/companion` | `COMPANION` |
| `/voice` (bare) | `MOBILE_VOICE` |
| `/voice on\|off\|tts\|status …` | `dispatch` returns `None` → existing voice handler retains control |
| `/mobile-voice` | `MOBILE_VOICE` |
| anything else | `None` |

---

## 4. What was NOT shipped (Wave 02 follow-up)

This wave's allowed-files contract excludes the two files that own
interactive slash command dispatch in the REPL. The adapter is
runnable via `hermes jarvis …` today; **inside the interactive Hermes
REPL, typing `/jarvis`, `/builder`, etc. will still hit the existing
unknown-command path until Wave 02 lands the integration below.**

### 4.1 `hermes_cli/commands.py` — register `CommandDef` entries

Around the existing `CommandDef("voice", "Toggle voice mode", …)` at
line 154 of `hermes_cli/commands.py`, add one `CommandDef` per JARVIS
slash so `resolve_command` and `/help` see them:

- `/jarvis`, `/jp`, `/jarvis-prime` (Action; description: "Route work
  through JARVIS Prime (auto-classified mode)")
- `/builder` (Action)
- `/operator` (Action)
- `/strategy` (Action)
- `/critic` (Action)
- `/companion` (Action)
- `/mobile-voice` (Action)

Leave the existing `/voice` `CommandDef` untouched — JARVIS will defer
to it whenever a subcommand token follows (`/voice on`, `/voice tts`,
etc.).

### 4.2 `cli.py` — wire `dispatch` into `HermesCLI.process_command`

In `cli.py:HermesCLI.process_command` (near the `resolve_command`
usage point reported around line 7829), add an early-dispatch branch
that:

1. Imports `from hermes_cli.jarvis_prime import dispatch` lazily.
2. Calls `result = dispatch(full_command_line)`.
3. On `result is not None`:
   - Renders `result.route.persona_header` and
     `result.route.response_format` via the CLI's existing print
     channel.
   - Passes `result.payload` to the agent loop as the user prompt,
     prefixed/system-augmented with the persona header so the model
     answers in-mode.
4. On `result is None`: fall through to the existing elif chain — no
   behavior change for unknown commands or the existing `/voice`
   toggle.

**Precedence rule (intentional and tested here):** `/voice <token>`
where token ∈ {`on`, `off`, `tts`, `status`} returns `None` from
`dispatch`, so the existing voice handler keeps full control. Bare
`/voice` is treated as a JARVIS Mobile Voice slash; if that conflicts
with future voice-toggle UX in cli.py, Wave 02 can resolve it by
either reordering the elif chain or expanding `_VOICE_SUBCOMMANDS` in
`hermes_cli/jarvis_prime/slash.py`.

---

## 5. Test inventory

| Test | Count | Notes |
|---|---|---|
| `test_slash_commands_table_maps_to_modes` | 10 | parametrized |
| `test_dispatch_concrete_modes_resolve` | 6 | parametrized |
| `test_dispatch_jarvis_autoclassifies_builder` | 1 | |
| `test_dispatch_jp_autoclassifies_critic` | 1 | |
| `test_dispatch_jarvis_prime_autoclassifies_strategy` | 1 | |
| `test_dispatch_unknown_returns_none` | 7 | parametrized |
| `test_dispatch_non_string_returns_none` | 1 | |
| `test_voice_with_subcommand_defers_to_existing_handler` | 6 | parametrized |
| `test_voice_bare_maps_to_mobile_voice` | 2 | parametrized |
| `test_classifier_heuristics` | 6 | parametrized |
| `test_classifier_empty_defaults_to_companion` | 1 | |
| `test_router_returns_route_result_with_default_format_for_reasoning_modes` | 1 | covers 4 modes inside |
| `test_router_returns_operational_format_for_operator_and_builder` | 1 | |
| `test_router_rejects_auto` | 1 | |
| `test_header_for_each_named_mode_unique_and_nonempty` | 1 | covers 6 modes inside |
| `test_header_for_auto_raises` | 1 | |
| `test_cmd_jarvis_runs_dispatch_for_known_slash` | 1 | |
| `test_cmd_jarvis_reports_unknown_slash` | 1 | |
| `test_cmd_jarvis_classifies_free_text` | 1 | |
| `test_cmd_jarvis_voice_subcommand_treated_as_unknown` | 1 | |
| **Total** | **51** | all passing |

Run with:

```
pytest tests/test_jarvis_prime_cli_commands.py -v
```

---

## 6. Verification

1. **Unit tests:** `pytest tests/test_jarvis_prime_cli_commands.py -v`
   → 51 passed, ~2s.
2. **Argparse smoke test:**
   ```
   hermes jarvis /builder "ship the PR"
   hermes jarvis /critic "this plan is too broad"
   hermes jarvis /voice
   hermes jarvis /voice on        # → Unknown JARVIS slash; voice toggle (Wave 02) keeps control
   hermes jarvis /jarvis "code something for me"
   hermes jarvis "I feel stuck this week"
   ```
3. **Non-regression on slash prefix tests:**
   `pytest tests/cli/test_cli_prefix_matching.py` — passes in a
   normally provisioned env. Test imports `cli.py`, which this wave
   did not modify.
4. **Diff guard before push:**
   ```
   git diff --name-only main...HEAD
   ```
   Expected paths only:
   - `hermes_cli/jarvis_prime/__init__.py`
   - `hermes_cli/jarvis_prime/classifier.py`
   - `hermes_cli/jarvis_prime/modes.py`
   - `hermes_cli/jarvis_prime/persona.py`
   - `hermes_cli/jarvis_prime/router.py`
   - `hermes_cli/jarvis_prime/slash.py`
   - `hermes_cli/main.py`
   - `tests/test_jarvis_prime_cli_commands.py`
   - `docs/aci/reports/W01_CLI_JARVIS_WIRING.md`

---

## 7. Risks & open issues

- **Heuristic-only classifier.** `ModeClassifier` is pure regex; it
  will misroute on adversarial phrasing. Acceptable for Wave 01 — the
  SKILL.md remains the authoritative routing spec, and the classifier
  can be swapped for an LLM call later without signature changes.
- **REPL unreachability this wave.** `/jarvis` and friends are
  callable as `hermes jarvis /jarvis …`; they will appear as unknown
  inside the interactive `hermes` REPL until Wave 02 lands the
  `CommandDef`s and `process_command` wiring documented in §4.
- **Class-name drift.** The task brief referenced four "existing"
  classes; only `ModeClassifier`, `Router`, and `Persona` exist as
  classes here. No `JarvisPrime` class is introduced; the package
  surface itself plays that role. Flagged so reviewers don't assume
  reuse where there was none.
- **SKILL.md drift detection.** `DEFAULT_RESPONSE_FORMAT` and
  `OPERATIONAL_HANDOFF_FORMAT` are inlined verbatim from
  `skills/jarvis-prime/SKILL.md`. There is no automated check today
  that they stay in sync; a future wave should either generate them
  from the markdown or add a drift test.

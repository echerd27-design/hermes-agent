# Wave 01 — JARVIS Prime Output Contract

## Mission

Standardize the JARVIS Prime turn/handoff output contract for all
future surfaces (gateway, Slack, mobile, CLI, agents) by adding a
single importable rendering module plus contract tests. This wave is
contract-only — no gateway, Android, or CLI runtime code is changed.

## Branch

`aci/wave-01-jarvis-output-contract`

## Changed files

- `hermes_cli/jarvis_prime/persona.py` (new)
- `hermes_cli/jarvis_prime/runtime.py` (new)
- `tests/test_jarvis_prime_output_contract.py` (new)
- `docs/aci/reports/W01_JARVIS_OUTPUT_CONTRACT.md` (this file)

Nothing under `gateway/**`, `apps/android/**`, `hermes_cli/main.py`,
`pyproject.toml`, `uv.lock`, or `README.md` is touched.

## Design summary

`hermes_cli.jarvis_prime.persona` is the single source of truth for
the six JARVIS Prime modes — `companion`, `strategy`, `critic`,
`operator`, `builder`, `mobile_voice` — and their tone labels. It
exposes `MODES`, `TONE_LABELS`, `validate_mode`, `tone_label`, and
`voice_intro`. The mode set mirrors
`docs/jarvis-prime-operating-system.md` and `skills/jarvis-prime/SKILL.md`.

`hermes_cli.jarvis_prime.runtime` defines a frozen `Handoff` dataclass
and two pure rendering functions:

- `render_handoff(handoff)` — long form following the operational
  handoff template in `skills/jarvis-prime/SKILL.md`, extended with a
  `Remaining risk` line from `docs/jarvis-verification-gates.md`:

  ```
  Builder Mode — repo work
  Mission: ship the JARVIS output contract
  Route selected: claude-code-builder
  Delegate: claude-code-builder
  Actions taken: scaffolded runtime.py, scaffolded persona.py
  Verification: pytest tests/test_jarvis_prime_output_contract.py passed
  Owner gates: merge to main
  Next step: open the draft PR
  Remaining risk: renderer not yet wired into gateway
  ```

- `render_handoff_compact(handoff, *, max_lines=6, max_width=80)` —
  mobile-safe form bounded by line and width budgets, matching the
  short-response contract in `docs/mobile-voice-development-workflow.md`:

  ```
  [mobile_voice] Mission: capture low-clearance warning idea
  Route: mobile-capture → claude-code-builder
  Gates: merge to main
  Next: expand into focused-mode packet
  Risk: scope creep if expanded too far
  ```

Both renderers are deterministic (same input → byte-identical output)
and the modules are pure (no I/O, no env reads, no network).

## Tests run

```
$ python -m compileall hermes_cli/jarvis_prime
Listing 'hermes_cli/jarvis_prime'...

$ pytest tests/test_jarvis_prime_output_contract.py -v
collected 19 items
... 19 passed in 1.46s
```

Coverage targets exercised:

- mode registry exact-match and validator error message
- `Handoff` mode validation + tuple-typed `owner_gates` / `actions`
- `Handoff.from_mapping` list→tuple coercion and unknown-key rejection
- long-form render contains every contract field for the builder
  route and the strategy route
- empty `actions` / `owner_gates` / `remaining_risk` render as `none`
- compact form respects 6-line, 80-char budgets for `mobile_voice`
- compact form keeps `Gates:` when present and drops it when empty
- compact form drops `Risk:` when empty
- compact form preserves mission and next-action lines even under
  500-character inputs (truncated with `…`)
- compact form rejects `max_lines < 4` with `ValueError`
- both renderers produce identical output across paired calls
- modules reload cleanly with no side effects

## Owner gates

None triggered. No publish, deploy, merge, secret rotation, account
creation, or third-party state change. The PR is opened as a draft.

## Remaining risks

1. **Namespace subpackage convention deviation.**
   `hermes_cli/jarvis_prime/` has no `__init__.py` because the
   universal-header contract restricts edits to the four ALLOWED
   FILES. The package works correctly as a PEP 420 namespace
   subpackage (imports + `compileall` verified). A future wave can
   promote it to a regular subpackage if Hermes plugin discovery
   begins to require `__init__.py`.
2. **Renderer is not yet wired into any surface.** Gateway, Slack,
   mobile, and CLI code still hand-format JARVIS turns. Wiring those
   surfaces to call `render_handoff` / `render_handoff_compact` is
   the explicit job of a later wave and is intentionally out of
   scope here.
3. **Truncation is line-based, not token-based.** Very dense
   single-line missions on narrow phone screens may still wrap. The
   compact budget caps each line at 80 characters; downstream
   surfaces with stricter widths should pass a smaller `max_width`.

## Rollback plan

`git revert` the wave commit on branch
`aci/wave-01-jarvis-output-contract`, or delete the branch entirely.
No schema migrations, no environment changes, no external service
state to undo. The four new files are the only artifact.

## PR summary (draft)

```
Wave 01 — JARVIS Prime output contract

Adds hermes_cli/jarvis_prime/{runtime,persona}.py with a stable
Handoff dataclass plus render_handoff and render_handoff_compact
functions. Both renderers are deterministic, pure, and pin the
operational handoff template from skills/jarvis-prime/SKILL.md and
the mobile-voice short-response contract.

Changed files
- hermes_cli/jarvis_prime/persona.py (new)
- hermes_cli/jarvis_prime/runtime.py (new)
- tests/test_jarvis_prime_output_contract.py (new)
- docs/aci/reports/W01_JARVIS_OUTPUT_CONTRACT.md (new)

Tests
- python -m compileall hermes_cli/jarvis_prime — ok
- pytest tests/test_jarvis_prime_output_contract.py — 19 passed

Remaining risks
- Renderer not yet wired into gateway/mobile (future wave).
- Namespace subpackage deviates from the `hermes_cli/proxy/`
  __init__.py convention (strict ALLOWED FILES contract).
- Compact form truncation is line-based; very narrow surfaces
  should pass a smaller max_width.

Rollback
- Revert the branch. No external state to undo.
```

## Follow-up waves

- **Wave 02 (proposed).** Wire `gateway/` response handlers to call
  `render_handoff` / `render_handoff_compact` based on the request
  surface (Slack vs. mobile vs. desktop CLI).
- **Wave 03 (proposed).** Promote `hermes_cli/jarvis_prime/` to a
  regular subpackage with `__init__.py` re-exporting `Handoff`,
  `render_handoff`, `render_handoff_compact` — once import paths
  stabilize and downstream callers exist.

# Wave 09 — Gate Report Renderer

## Wave summary

W09 delivers the presentation layer for JARVIS Prime gate results: a
stdlib-only module of pure renderers that turn gate-result data into
markdown, mobile, JSON, failure-only, and owner-approval views.

The companion runtime evaluator (`hermes_cli/jarvis_prime/gates.py`) is
the responsibility of a different wave. W09 is deliberately
**presentation-only** and never imports the evaluator — the two waves
can land in either order. To support this, every renderer is
duck-typed and accepts gate results as either objects-with-attributes
or plain dicts.

## Files changed

| File                                              | Status | Purpose |
|---------------------------------------------------|--------|---------|
| `hermes_cli/jarvis_prime/__init__.py`             | new    | Package init; re-exports the public renderer API. |
| `hermes_cli/jarvis_prime/gate_reports.py`         | new    | Five renderer helpers plus normalization helpers and the duck-typed contract. |
| `tests/test_jarvis_prime_gate_reports.py`         | new    | 41 pytest cases using local `FakeGateResult` / `FakeReport` dataclasses. |
| `docs/aci/reports/W09_GATE_REPORT_RENDERER.md`    | new    | This wave report. |

No other files are modified. The runtime gate module is **not** read,
imported, or created in this wave.

## Public API

Exported by `hermes_cli.jarvis_prime`:

| Name                       | Kind     | Purpose |
|----------------------------|----------|---------|
| `markdown_report(report)`  | function | Full markdown report (table of 8 gates, Result, Remaining risk, Next action). |
| `mobile_report(report)`    | function | Short ASCII summary bounded to ≤400 chars; always includes `Risk:` and `Next:`. |
| `as_dict(report)`          | function | JSON-safe dict; `json.dumps(..., sort_keys=True)` is guaranteed. |
| `failure_summary(report)`  | function | Only failed gates, plus Remaining risk and Next action. |
| `owner_approval_summary(report)` | function | Only owner-approval gates, plus Remaining risk and Next action. |
| `GATE_ORDER`               | constant | Canonical tuple of 8 gate keys. |
| `GATE_DISPLAY_NAMES`       | constant | Canonical key → display name (matches `docs/jarvis-verification-gates.md`). |
| `STATUS_PASS` / `STATUS_FAIL` / `STATUS_OWNER_APPROVAL` / `STATUS_SKIPPED` | constants | Canonical status strings. |
| `VALID_STATUSES`           | constant | Frozenset of the four canonical statuses. |
| `GateResultLike` / `ReportLike` | Protocol | Duck contract for object input. |
| `GateResultDict` / `ReportDict` | TypedDict | Duck contract for dict input. |

## Duck-typed contract

### Gate result

| Field      | Required | Default       | Notes |
|------------|----------|---------------|-------|
| `name`     | yes      | `"unknown"`   | Canonicalized via name aliases. |
| `status`   | yes      | `"skipped"`   | One of `pass`/`fail`/`owner_approval`/`skipped`; unknown values coerced to `skipped`. |
| `message`  | no       | `""`          | Free-text reason / detail. |
| `owner`    | no       | `""`          | Used by owner-approval summary. |
| `evidence` | no       | `""`          | Optional cite; shown in markdown long form, omitted from mobile. |

### Report

| Field            | Required | Default              | Notes |
|------------------|----------|----------------------|-------|
| `gates`          | yes      | `[]`                 | Sequence of gate-result objects/dicts. Non-sequence input is treated as empty. |
| `result` (alias `overall`) | no | derived    | If absent: `fail` > `owner_approval` > `pass` > `skipped`. |
| `remaining_risk` | no       | `"None stated."`     | Always rendered. |
| `next_action`    | no       | derived from overall | Defaults to `"Proceed."`, `"Block on fail; resolve failing gates before proceeding."`, `"Awaiting owner approval."`, or `"No action — all gates skipped."`. |
| `title`          | no       | `"JARVIS Gate Summary"` | Markdown heading. |
| `timestamp`      | no       | `""`                 | Pre-formatted string; never parsed. |

The 8 canonical gate keys are `planning`, `build`, `review`, `test`,
`security`, `release`, `owner_approval`, and `rollback`. Aliases
(`"Planning Gate"`, `"planning_gate"`, etc.) are accepted.

## Design decisions

1. **Stdlib-only.** No `jinja`, no `rich` — easy to vendor anywhere
   and to test hermetically.
2. **Always emit all 8 canonical gates.** Missing gates are
   synthesized as `SKIPPED — not run`. Output shape is deterministic
   regardless of how complete the input is.
3. **`gates.py` isolation.** The renderer never imports the runtime
   evaluator. A regression test asserts that
   `hermes_cli.jarvis_prime.gates` is not in `sys.modules` after the
   package loads.
4. **Mobile bounded.** `mobile_report` is single-line per section,
   truncates risk/next text, and is asserted ≤ 400 chars in tests.
5. **JSON-safe by construction.** `as_dict` only returns `str`,
   `int`, `bool`, `list`, `dict`. No datetimes, no enums, no sets.
6. **Stable ordering.** Gates are emitted in `GATE_ORDER`; unknown
   gate names appear at the end in input order. Two calls with the
   same input return byte-identical strings.

## Non-goals

- Does **not** evaluate gates — Wave 08's runtime evaluator is
  responsible for producing gate-result inputs.
- Does **not** parse timestamps — accepts pre-formatted strings only.
- Does **not** publish to Slack, SMS, email, etc. — pure rendering;
  the platform adapters wire it up later.
- Does **not** modify any runtime entry point (gateway, CLI command,
  cron, etc.) — the module is additive only and not yet wired.

## Test plan + verification

Tests are in `tests/test_jarvis_prime_gate_reports.py`. They use
locally-defined `FakeGateResult` / `FakeReport` dataclasses — no
import of the forbidden `gates.py`. Coverage includes:

- Duck-typed contract: object gates, dict gates, mixed input, object
  vs dict report, the `overall` alias.
- Markdown: all 8 gates present, missing gates as SKIPPED, determinism,
  input-order invariance, title/timestamp rendering.
- Mobile: length budget, first-failure callout, all-pass path,
  owner-approval callout, truncation of long risk/next, single-line
  invariants.
- `as_dict`: JSON round-trip, counts sum, no non-serializable types,
  required keys, all 8 canonical gates emitted.
- Failure summary: lists only failed gates, "no failed gates" branch,
  multiple failures.
- Owner-approval summary: owner name and message, "none pending"
  branch.
- Edge cases: empty report, unknown gate name, unknown status, missing
  optional fields, derived vs explicit overall, status aliases, name
  aliases, default risk/next, isolation from `gates.py`,
  non-sequence `gates` value.

Verification commands run from the repo root:

```bash
# 1. Import smoke
python -c "from hermes_cli.jarvis_prime import markdown_report, mobile_report, as_dict, failure_summary, owner_approval_summary; print('imports ok')"

# 2. Confirm no import of forbidden gates.py
grep -E 'jarvis_prime\.gates' hermes_cli/jarvis_prime/gate_reports.py hermes_cli/jarvis_prime/__init__.py
# expected: no matches (exit code 1)

# 3. Required by the wave packet
pytest tests/test_jarvis_prime_gate_reports.py -q
python -m compileall hermes_cli/jarvis_prime/gate_reports.py

# 4. JSON-safety
python -c "
import json
from hermes_cli.jarvis_prime import as_dict
class R:
    gates = []
    result = 'pass'
    remaining_risk = ''
    next_action = ''
print(json.dumps(as_dict(R()), sort_keys=True))
"

# 5. Whitespace hygiene
git diff --check -- hermes_cli/jarvis_prime tests/test_jarvis_prime_gate_reports.py docs/aci/reports/W09_GATE_REPORT_RENDERER.md
```

Result: all 41 tests pass; compileall is silent (no syntax errors);
grep exits 1 (no forbidden import); `git diff --check` exits 0.

## Remaining risk

- The duck-typed contract is informal: if Wave 08 chooses field names
  outside the accepted aliases, a small adapter wave will be needed.
  Neither W08 nor W09 is blocked — the renderer's name and status
  alias maps already accept the most likely shapes.
- This wave does not wire the renderer into any runtime path (CLI,
  gateway, Slack, etc.); a follow-up wave will pick the integration
  point and add tests for the wiring.

## Rollback

The wave is additive only. To revert:

- `git revert <commit>` against the wave commit, OR
- delete the new files:
  - `hermes_cli/jarvis_prime/gate_reports.py`
  - `hermes_cli/jarvis_prime/__init__.py`
  - `tests/test_jarvis_prime_gate_reports.py`
  - `docs/aci/reports/W09_GATE_REPORT_RENDERER.md`

No runtime path depends on this module yet, so revert is safe.

## JARVIS gate summary for this wave

```text
GATE SUMMARY
Planning gate:        PASS — scope, branch, allowed/forbidden files defined.
Build gate:           PASS — only allowed files touched; gates.py untouched.
Review gate:          PASS — deterministic output, duck-typed contract documented.
Test gate:            PASS — 41/41 pytest cases pass.
Security gate:        PASS — no secrets; stdlib-only; no new dependencies.
Release gate:         PASS — draft PR only; not merged to main.
Owner approval gate:  SKIPPED — additive docs + presentation code; no deploys, no merges.
Rollback gate:        PASS — `git revert <commit>` or delete the four new files.
Result:               PASS
Remaining risk:       Informal cross-wave contract; integration wiring still pending.
```

# Wave 05 — Review Packet Schema

## Mission

Create an independent review-packet schema for Codex reviewer tasks: a
shared, stdlib-only data structure + deterministic markdown renderer that
any agent or human can assemble in a uniform way to brief Codex on a
PR/branch.

## Branch

`aci/wave-05-review-packet-schema`

## Changed files

| Path | Status | Purpose |
| --- | --- | --- |
| `hermes_cli/jarvis_prime/__init__.py` | new | Package marker + public surface re-exports. |
| `hermes_cli/jarvis_prime/review_packets.py` | new | Schema (`ReviewPacket`, `ChecklistItem`, `TestEvidence`, `FixRecommendation`), validation (`normalize_decision`), defaults (`default_security_checklist`, `default_regression_checklist`), and renderer (`render_review_packet`). |
| `tests/test_jarvis_prime_review_packets.py` | new | 25 pytest cases covering every public function and every documented branch of the renderer. |
| `docs/aci/reports/W05_REVIEW_PACKET_SCHEMA.md` | new | This report. |

No files outside the four ALLOWED entries were modified.

## Tests run

```
uv run --no-project --with pytest --with pytest-xdist --with pytest-timeout \
  pytest tests/test_jarvis_prime_review_packets.py -p no:cacheprovider
# => 25 passed in 1.09s

python -m compileall hermes_cli/jarvis_prime/review_packets.py
# => Compiling 'hermes_cli/jarvis_prime/review_packets.py'... (no errors)
```

## Acceptance criteria → tests

| Criterion | Where covered |
| --- | --- |
| Does not require GitHub API. | Module imports only stdlib (`dataclasses`, `typing`). No `requests`, no `gh`, no MCP. |
| Produces markdown suitable for Codex. | `render_review_packet()` returns a deterministic markdown string; trailing newline, stable section order. `TestRenderApprove.test_determinism` asserts byte-for-byte stability. |
| Tests cover approve / request_changes / comment. | `TestRenderApprove`, `TestRenderRequestChanges`, `TestRenderComment` classes. |
| Tests cover missing test evidence. | `TestMissingTestEvidence.test_warning_blockquote_when_no_evidence`. |
| Tests cover security finding. | `TestSecurityFinding.test_callout_added_when_any_item_fails`. |

Bonus coverage: decision normalisation (uppercase, spaces, unknown values,
non-string), failed-test rendering, pipe-escaping in evidence tables,
default checklists, cross-cutting fix recommendations.

## Schema (public surface)

Re-exported from `hermes_cli.jarvis_prime`:

- `VALID_DECISIONS`, `VALID_STATUSES` — constant tuples.
- `ChecklistItem(label, status="todo", note="")`
- `TestEvidence(command, passed, summary="")`
- `FixRecommendation(file, change, rationale="")`
- `ReviewPacket(subject, mission, files_changed, acceptance_criteria,
  diff_summary, test_evidence, security_checklist, regression_checklist,
  decision, fix_recommendations=(), reviewer_notes="")`
- `normalize_decision(value) -> str`
- `default_security_checklist() -> tuple[ChecklistItem, ...]`
- `default_regression_checklist() -> tuple[ChecklistItem, ...]`
- `render_review_packet(packet) -> str`

All dataclasses are `frozen=True` → packets are immutable; tweak via
`dataclasses.replace`.

## Remaining risks

- **Schema may evolve** as Codex feedback comes in. The dataclasses are
  frozen and named, so additive changes (new optional fields) are safe;
  any rename or required-field addition is a breaking change for callers
  that pickle / persist packets — note when this wave's consumers land.
- **Markdown shape is fixed.** No theming hook today. If Codex needs a
  different section order or HTML output, a follow-up wave should add a
  pluggable renderer rather than editing the in-place format.
- **No builder wave yet.** This module only provides the schema; no
  wave-05 code populates a `ReviewPacket` from real git/PR state. That's
  intentional (acceptance criteria forbids the GitHub API in this wave)
  but means the schema's first real consumer will reveal any ergonomic
  gaps.

## Rollback plan

```bash
git checkout main -- :/  # (or whichever base)
rm -f hermes_cli/jarvis_prime/__init__.py
rm -f hermes_cli/jarvis_prime/review_packets.py
rmdir hermes_cli/jarvis_prime
rm -f tests/test_jarvis_prime_review_packets.py
rm -f docs/aci/reports/W05_REVIEW_PACKET_SCHEMA.md
rmdir docs/aci/reports docs/aci 2>/dev/null || true
```

Nothing else in the repo imports this module yet, so deleting it is
risk-free.

## PR summary (draft)

> **Wave 05 — Review packet schema for Codex reviewer tasks**
>
> Adds `hermes_cli.jarvis_prime.review_packets`, a stdlib-only module
> that defines the schema and deterministic markdown renderer for the
> briefing packets we hand to Codex when it acts as an independent
> reviewer. No network, no GitHub API, no LLM — pure data and rendering.
>
> Public surface: `ReviewPacket`, `ChecklistItem`, `TestEvidence`,
> `FixRecommendation`, `normalize_decision`,
> `default_security_checklist`, `default_regression_checklist`,
> `render_review_packet`.
>
> 25 pytest cases cover every public function and every documented
> branch of the renderer (approve / request_changes / comment, missing
> test evidence, security finding, default checklists, pipe-escaping).
> Draft PR — no merge to main; no consumers yet.

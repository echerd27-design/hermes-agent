# W07 — AOS Council Decision Schema

| Field | Value |
|---|---|
| Wave | 07 |
| Branch | `aci/wave-07-aos-decision-schema` |
| Mission | Create a structured AOS Council decision schema for strategy, architecture, security, and release judgment. |
| Status | Implementation complete; draft PR pending. |

## Context

JARVIS Prime sits above the AOS Council and routes mission briefs through structured deliberation before any worker executes (`docs/jarvis-prime-operating-system.md`, `docs/context/AEO_AOS_Council_Engine_Master_Reference_2026-05-17.md`). Before this wave, every council pass invented its own freeform markdown shape: the gateway and mobile surfaces could not parse a verdict, and the four canonical decision domains (architecture, security, strategy, release) could not be diffed, replayed, or stored.

This wave introduces a stdlib-only, dependency-free, **serialize-only** schema at `hermes_cli/jarvis_prime/aos.py` so AOS Council outputs have one canonical Python shape with two stable renderings: `to_dict()` for the gateway / mobile JSON consumer, and `to_markdown()` matching the Output Standard in `CLAUDE.md`. The module is the data layer beneath every future "render an AOS decision" surface — slash commands, Slack handoff cards, PR comment templates, memory store entries.

`AGENTS.md` line 700 documents JARVIS Prime as "spec, not runtime (yet)"; this schema is a concrete piece of the runtime that satisfies the AOS Council piece of that contract.

## Schema overview

Seven public symbols, all stdlib-only. Layering: `CouncilQuestion` is the input; `CouncilPerspective`, `SpecialistFinding`, and `ContrarianObjection` are the per-seat contributions; `CouncilDecision` is the synthesized verdict; `FinalRecommendation` is the top-level handoff that bundles everything plus the canonical Output Standard fields.

- **`DecisionStatus`** (`str, Enum`) — exactly four lowercase tokens: `approved`, `rejected`, `needs_owner`, `needs_more_evidence`. Subclassing `str` makes `json.dumps([DecisionStatus.APPROVED])` emit `'["approved"]'` directly with no custom encoder.
- **`CouncilQuestion`** — the mission brief plus `context`, `requested_by`, `mode`, `tags`.
- **`CouncilPerspective`** — one seat's read: `role` (open string), `summary`, `rationale`, `score` (1-5 int), `confidence` (1-5 int), `concerns`, `supports`. `__post_init__` raises `ValueError` if score or confidence is out of range.
- **`SpecialistFinding`** — domain specialist contribution: `specialist`, `domain`, `finding`, `evidence`, `confidence`, `blocking: bool`.
- **`ContrarianObjection`** — red-team output: `objection`, `severity` (open string), `rebuttal`, `addressed`, `raised_by`.
- **`CouncilDecision`** — synthesized verdict: `status`, `headline`, `rationale`, `scorecard` (`tuple[tuple[str, int], ...]`), `owner_questions`, `evidence_gaps`.
- **`FinalRecommendation`** — top-level handoff. Wraps the question + decision plus `perspectives`, `specialist_findings`, `contrarian_objections`, `recommended_plan`, `blockers`, `execution_checklist`, `validation_commands`, `rollback_notes`, `open_questions`, `schema_version = "aos.v1"`, and `generated_at`. Exposes `to_dict()`, `to_markdown()`, and `to_json(*, indent=2)`.

All dataclasses are `frozen=True`. `to_dict()` is hand-rolled (not `dataclasses.asdict`) so tuple → list conversion and `DecisionStatus → .value` are explicit. `to_markdown()` follows `CLAUDE.md`'s Output Standard heading order: Executive verdict → Evidence reviewed → Agent perspectives → (Specialist findings) → (Contrarian objections) → Decision scorecard → Recommended plan → Blockers and risks → Execution checklist → Validation commands → Rollback notes → Open questions. Sections backed by empty tuples are omitted; the Executive verdict is the only always-rendered section. `NEEDS_OWNER` decisions surface `owner_questions` immediately under Executive verdict; `NEEDS_MORE_EVIDENCE` decisions surface `evidence_gaps` the same way.

## Files changed

| Path | LOC | Purpose |
|---|---|---|
| `hermes_cli/jarvis_prime/aos.py` | 565 | New schema module — seven public types, helpers, docstrings. |
| `hermes_cli/jarvis_prime/__init__.py` | 28 | New subpackage entry; re-exports the seven public types. |
| `tests/test_jarvis_prime_aos.py` | 837 | 37 pytest tests (7 unit classes + 4-scenario `TestEndToEnd`). |
| `docs/aci/reports/W07_AOS_DECISION_SCHEMA.md` | — | This report. |

No FORBIDDEN paths touched (`skills/**`, `gateway/**`, `apps/android/**`, `pyproject.toml`, `uv.lock`, `README.md` are unchanged).

## Tests

Class breakdown:

- `TestDecisionStatus` — lowercase tokens, JSON-direct serialization, enum-validation rejection.
- `TestCouncilQuestion` — `to_dict` round-trip, markdown contains brief + context, empty-context section omitted.
- `TestCouncilPerspective` — parametrized score/confidence out-of-range, `N/5` rendering, concerns + supports preserved, dataclass is frozen.
- `TestSpecialistFinding` — blocking flag rendered, evidence order preserved, confidence range validated.
- `TestContrarianObjection` — addressed vs. open render distinctly, empty rebuttal omitted, severity is open string.
- `TestCouncilDecision` — status as string in JSON, scorecard as markdown table, `owner_questions` only render under `NEEDS_OWNER`, `evidence_gaps` only under `NEEDS_MORE_EVIDENCE`.
- `TestFinalRecommendation` — `schema_version` default + override, JSON dumpable, `to_json` indents, tuple → list shape lock, empty optional sections omitted, `## Open questions` rendered when populated and omitted when empty.
- `TestEndToEnd` — four realistic scenarios covering the wave's required domains (status mix: APPROVED ×2, NEEDS_OWNER ×1, NEEDS_MORE_EVIDENCE ×1):
  - `test_architecture_decision` — "split 225 KB hermes_cli/gateway.py into transport + session"; status `NEEDS_MORE_EVIDENCE`; asserts `evidence_gaps` and the contrarian's headline both surface in markdown.
  - `test_security_decision` — "ack shai-hulud-2026-05, rotate Mistral keys"; status `APPROVED`; asserts the blocking specialist finding renders `**Blocking:** yes`, the validation block stays inside a fenced code block, and the literal `pip uninstall -y mistralai` appears.
  - `test_strategy_decision` — "position Hermes as local-first AI cockpit"; status `NEEDS_OWNER`; asserts `Owner questions:` surfaces in the markdown and `## Open questions` section is rendered.
  - `test_release_decision` — "ship hermes-cli 0.15 with rollback gate"; status `APPROVED`; asserts the verbatim rollback pin `pip install hermes-cli==0.14.0` appears in the Rollback notes section and execution checklist is rendered as `- [ ]` checkboxes.

Result: **37 passed in 1.40s**. No skips, no warnings.

## Verification

The wave's literal VERIFY block plus a smoke import test:

```
$ python -m compileall hermes_cli/jarvis_prime/aos.py
(exit 0)

$ python -c "from hermes_cli.jarvis_prime import FinalRecommendation, DecisionStatus, CouncilQuestion, CouncilDecision, CouncilPerspective, SpecialistFinding, ContrarianObjection; print('imports ok')"
imports ok

$ python -m pytest tests/test_jarvis_prime_aos.py
....................................                                     [100%]
============================== 37 passed in 1.40s ==============================
```

The canonical test runner `scripts/run_tests.sh tests/test_jarvis_prime_aos.py` was not used in this run because the container lacks the `.venv` the script expects; pytest was installed at the system level (`pip install pytest pytest-xdist pytest-timeout`) so the `pyproject.toml` test config (`-n`, `--timeout=30`) resolves correctly. In a developer venv or CI, `scripts/run_tests.sh tests/test_jarvis_prime_aos.py` is the recommended invocation.

## Risks

- **Frozen vs. mutable** — frozen. Decisions are records; mutation would almost always be a bug. Cost: constructors take everything up front. Acceptable.
- **Open-string roles** — accepted for forward compatibility with the 233-agent registry under `skills/aos-enterprise-council/` plus future specialists. No enum to migrate when a new seat appears. Mitigation deferred: a private `_KNOWN_ROLES: frozenset[str]` constant could ship in a later wave for editor autocomplete, not enforcement.
- **No `from_dict`** — user-approved. The schema is for emission; the producer is the only consumer until the gateway/mobile surface ships. Avoids the "permissive parsing schema drift" failure mode visible in `security_advisories.py` cache-file handling. Adding `from_dict` later is additive.
- **Hand-rolled `to_dict`** — explicit over clever; ~50 LOC of mechanical mapping. The cost buys deterministic shape (tuples become lists, enums become strings) without surprise.
- **No markdown escaping** — accepted; council-authored internal data, not untrusted input. Documented in the `to_markdown` docstring. If a future surface needs to render to HTML, that surface is responsible for escaping.
- **`generated_at` as opaque string** — caller-supplied ISO-8601 or empty. Avoids implicit `datetime.now()` that hurts test determinism. Tradeoff: callers must remember to stamp; absent stamp renders as `*schema: aos.v1 — generated: *` which is ugly but harmless.
- **`schema_version` lives only on `FinalRecommendation`** — sub-types are always wrapped; duplicating the version on every dataclass would be noise. Future schema bumps add new optional fields and increment `aos.v1 → aos.v2`; the gateway/mobile consumer negotiates on the outermost value only.

No known consumers depend on this module yet, so the additive surface area is the only risk.

## Rollback

The wave is additive — no migrations, no config changes, no shared state, no consumers — so rollback is just removing the wave's files:

```
rm -rf hermes_cli/jarvis_prime/
rm tests/test_jarvis_prime_aos.py
rm docs/aci/reports/W07_AOS_DECISION_SCHEMA.md
```

Equivalent in git: revert the wave's single commit, or close the draft PR without merging. The harness branch `claude/wonderful-cerf-CaO1U` and the wave branch `aci/wave-07-aos-decision-schema` carry the same SHA; both are safe to discard.

## PR summary

> **Wave 07: AOS Council decision schema (`hermes_cli.jarvis_prime.aos`)**
>
> Adds a stdlib-only, dependency-free, frozen schema module at `hermes_cli/jarvis_prime/aos.py` with seven types (`DecisionStatus`, `CouncilQuestion`, `CouncilPerspective`, `SpecialistFinding`, `ContrarianObjection`, `CouncilDecision`, `FinalRecommendation`), each exposing `to_dict()` and `to_markdown()`. Markdown rendering follows the `CLAUDE.md` Output Standard heading order. 37 tests cover architecture, security, strategy, and release scenarios end-to-end plus per-type unit coverage. Serialize-only by design — no LLM call, no third-party imports, no consumer yet (forward-compat via `schema_version = "aos.v1"`).
>
> Verification: `python -m compileall hermes_cli/jarvis_prime/aos.py` (exit 0); `python -c "from hermes_cli.jarvis_prime import ..."` (ok); `python -m pytest tests/test_jarvis_prime_aos.py` (37 passed). Draft PR — do not merge.

## Open questions

None blocking.

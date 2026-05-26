# Wave 02 — Owner Authorization Enforcement

**Branch:** `aci/wave-02-owner-auth-tests`
**Status:** Draft PR
**Scope:** Pure-Python gate primitive + tests + this report. No callers migrated.

---

## 1. Executive Verdict

JARVIS Prime's owner-authorization mechanism — until now a free-text
phrase the operator typed and the codebase only enforced by convention —
is now a typed Python API in `hermes_cli/jarvis_prime/`. Every gated
high-impact action threads through a `GatedAction` enum and a
byte-for-byte equality check against the canonical phrase
`Yes, with authorization.`. Near misses fail. Unknown action categories
fail closed even with the correct phrase. A drift detector test reads
the phrase from `skills/aos-enterprise-council/operating-registry/registry.json`
and asserts it matches the Python constant, so the two sources cannot
silently diverge.

This wave is intentionally narrow: it ships the primitive. No existing
caller is migrated; that work is queued for follow-up waves and listed
under "Risks & Open Questions" below.

## 2. Mission Brief

From the Wave 02 universal-header MISSION block:

> Make owner authorization behavior impossible to bypass accidentally.

Action categories required by the prompt (10 total):

1. Spending money
2. Public posting
3. Account creation
4. OAuth / credential changes
5. Production deploys
6. DNS changes
7. Main-branch merges
8. Package publishing
9. App-store submissions
10. Legal / compliance / security / health / financial / regulated claims (single bucket)

Required phrase: `Yes, with authorization.`

Acceptance criteria (all verified by `tests/test_jarvis_prime_owner_auth.py`):

- Exact phrase required.
- Near misses fail.
- Case/spacing behavior is documented.
- Unknown gated actions fail closed.
- Tests cover all gated action categories.
- Gate summary shows pending actions clearly.

## 3. Evidence Reviewed

| File | Excerpt | Relevance |
|---|---|---|
| `AGENTS.md` lines 698–756 (JARVIS Prime section) | "owner-authorization mechanism (currently a free-text 'yes, with authorization' the operator types). These ship in follow-up PRs." | Confirms this wave is the documented follow-up. |
| `skills/aos-enterprise-council/operating-registry/registry.json:17` | `"owner_gate_phrase": "Yes, with authorization."` | Source of truth #1 for the phrase. |
| `skills/aos-enterprise-council/scripts/verify_registry.py:23` | `OWNER_GATE_VALUE = "Yes, with authorization."` | Source of truth #2; pre-dispatch verification. |
| `skills/aos-enterprise-council/SKILL.md` | "any merge, deploy, public post, credential change, or destructive action requires explicit 'Yes, with authorization.' from the owner" | Documents the gated-action coverage required of the council. |
| `tests/conftest.py` | Hermetic env strip, `TZ=UTC`, `PYTHONHASHSEED=0`, 30 s per-test SIGALRM | Confirms test-suite invariants the new tests inherit. |
| `tests/hermes_cli/test_auth_provider_gate.py` | `monkeypatch.delenv`, direct `from hermes_cli.X import Y` imports, snake_case `test_<behavior>_<condition>` names | Established pattern the new test file follows. |
| `hermes_cli/jarvis_prime/` | did not exist | Confirms greenfield module. |
| `tests/test_jarvis_prime_owner_auth.py` | did not exist | Confirms greenfield test. |
| `docs/aci/reports/` | did not exist | This wave establishes the convention. |

## 4. Decisions Recorded

Three planning-time decisions captured before any code was written:

1. **`hermes_cli/jarvis_prime/__init__.py` is added.** Strictly outside
   the ALLOWED FILES list, but every other subpackage under
   `hermes_cli/` (e.g. `proxy/`, `proxy/adapters/`) ships one and pytest
   import resolution depends on it across CI variants. Owner approved
   the addition during planning. This is the only deviation from the
   allowed-files list in this wave. The file is empty.
2. **Whitespace is strict.** No `.strip()`, no `re.sub`, no
   normalization. The comparison is `phrase == OWNER_GATE_PHRASE`. A
   trailing newline, a leading tab, or a double-space fails. This is
   the most defensive interpretation of "Near misses fail" and matches
   `OWNER_GATE_VALUE` equality in the council registry verifier.
3. **Regulated claims is one bucket.** The mission lists "legal,
   compliance, security, health, financial, or regulated claims" as a
   single category — encoded as `GatedAction.REGULATED_CLAIM`. Total
   enum members: 10.

## 5. Implementation Summary

### `hermes_cli/jarvis_prime/__init__.py`

Empty. Marks the subpackage for clean pytest imports.

### `hermes_cli/jarvis_prime/owner_auth.py`

- `OWNER_GATE_PHRASE: Final[str] = "Yes, with authorization."` — byte-for-byte equal to the registry constant.
- `GatedAction(str, Enum)` — 10 members listed in §2.
- Exception hierarchy: `AuthorizationError` → `PhraseMismatchError`, `UnknownActionError`.
- `resolve_action(action)` — coerces enum-or-string-or-anything to a `GatedAction`. Unknown input raises `UnknownActionError`.
- `authorize(action, phrase)` — resolves the action first (fail-closed), then byte-compares the phrase.
- Module docstring documents the case/spacing rules in plain prose.

### `hermes_cli/jarvis_prime/gates.py`

- `ACTION_DESCRIPTIONS` — one-line description per gated action. An import-time `assert set(ACTION_DESCRIPTIONS) == set(GatedAction)` catches drift if a category is added without a description.
- `@dataclass(frozen=True) class PendingGate(action, context, requested_at)`.
- `class GateLedger` — `request`, `confirm`, `pending`, `summary`. FIFO removal on confirm. Confirm with no matching pending entry raises `AuthorizationError` (not a silent no-op).
- `format_gate_summary(...)` — accepts a `GateLedger` or any iterable of `PendingGate`. Deterministic line-oriented format; empty case emits `"Pending owner gates (0): none"`.

### `tests/test_jarvis_prime_owner_auth.py`

67 tests (after parameterization) across 9 groups: canonical-phrase invariants, enum invariants, happy path across all 10 categories, near-miss rejection (16 cases), non-string phrase rejection (4 cases), unknown-action fail-closed (7 type variants + 2 string cases), exception hierarchy, ledger behavior, module surface.

## 6. Test Coverage Matrix

| Acceptance criterion | Test(s) |
|---|---|
| Exact phrase required | `test_authorize_succeeds_for_every_category_with_exact_phrase` (parameterized over all 10 categories), `test_owner_gate_phrase_literal_is_canonical` |
| Near misses fail | `test_authorize_rejects_near_miss_phrases` (16 parameterized cases: case, whitespace, punctuation, truncation, empty string), `test_authorize_rejects_non_string_phrase` (4 cases) |
| Case/spacing behavior is documented | `owner_auth.py` module docstring + `test_authorize_rejects_near_miss_phrases` covers each documented rule |
| Unknown gated actions fail closed | `test_unknown_action_string_fails_closed_with_correct_phrase`, `test_unknown_action_string_fails_closed_with_wrong_phrase`, `test_unknown_action_type_fails_closed` (7 type variants), `test_ledger_request_rejects_unknown_action`, `test_ledger_confirm_unknown_action_fails_closed` |
| Tests cover all gated action categories | `test_authorize_succeeds_for_every_category_with_exact_phrase` parameterized over `list(GatedAction)`; `test_gated_action_has_exactly_ten_members`; `test_action_descriptions_cover_every_gated_action` |
| Gate summary shows pending actions clearly | `test_empty_ledger_summary_says_none`, `test_ledger_summary_lists_all_pending_with_context`, `test_format_gate_summary_is_deterministic_snapshot`, `test_format_gate_summary_accepts_iterable_of_pending_gates`, `test_format_gate_summary_accepts_ledger`, `test_format_gate_summary_omits_context_line_when_empty` |
| Drift detector (registry → Python) | `test_owner_gate_phrase_matches_registry_json` |

## 7. Validation Commands

Run from the repo root:

```sh
# Universal-header VERIFY block:
pytest tests/test_jarvis_prime_owner_auth.py -v
python -m compileall hermes_cli/jarvis_prime

# Drift detector + module surface:
pytest tests/test_jarvis_prime_owner_auth.py::test_owner_gate_phrase_matches_registry_json -v

# Source-of-truth registry remains healthy (read-only, separate process):
python skills/aos-enterprise-council/scripts/verify_registry.py

# Import smoke test:
python -c "from hermes_cli.jarvis_prime.owner_auth import authorize, GatedAction, OWNER_GATE_PHRASE; from hermes_cli.jarvis_prime.gates import GateLedger, format_gate_summary; print('ok')"
```

## 8. Risks & Open Questions

- **No callers migrated yet.** This wave ships only the primitive.
  Accidental bypass is still possible until follow-up waves wire
  `authorize()` into Hermes CLI dispatch, Slack handlers, council
  skills, and CI release gates. Recommended next-wave punch list:
  - Slack command surface (`/jarvis build`, `/jarvis publish`, …) →
    register pending gate on entry, require confirmation phrase before
    side effects.
  - `hermes_cli/main.py` deploy / publish subcommands → wrap in
    `GateLedger.confirm`.
  - CI release pipeline → block main-branch merge + package publish
    on missing phrase in PR description or commit trailer.
  - Council bench agents → consume `ACTION_DESCRIPTIONS` so council
    summaries match runtime gate copy.
- **Drift detector is not yet in CI.** The
  `test_owner_gate_phrase_matches_registry_json` test fails loud
  locally, but no CI workflow runs `tests/test_jarvis_prime_owner_auth.py`
  yet (this wave is forbidden from touching CI configs). Recommended
  follow-up: add the test path to whatever pytest job is already wired
  for `hermes_cli/`.
- **Phrase is hardcoded in Python, not loaded from registry.json.**
  Deliberately deferred — a JSON-loader at import time risks
  circular imports against the council skill and adds startup cost.
  The drift detector test provides equivalent safety without the
  load-time coupling.
- **Single-process ledger.** `GateLedger` does not persist across
  process restarts. Adequate for Wave 02's primitive scope; a
  persisted variant (Slack thread state, kanban task, structured log)
  is a follow-up.

## 9. Rollback Plan

```sh
git revert <wave-02-commit-sha>
```

Nothing in this wave runs at import time outside the test process. No
database, no config file, no env var, no network call. Revert is
clean and immediate.

## 10. PR Summary

> Wave 02 — Owner Authorization Enforcement
>
> Hardens the JARVIS Prime owner-authorization phrase into a typed
> Python API. `hermes_cli.jarvis_prime.owner_auth.authorize(action, phrase)`
> requires byte-for-byte equality against `Yes, with authorization.` and
> resolves the action through a 10-member `GatedAction` enum. Unknown
> actions fail closed. `GateLedger` + `format_gate_summary` render
> pending gates in a deterministic format. 41 tests cover every
> category, every documented near-miss, fail-closed paths, and a
> drift detector against `skills/aos-enterprise-council/operating-registry/registry.json`.
>
> No callers migrated in this wave — the primitive ships first.
> See `docs/aci/reports/W02_OWNER_AUTH_ENFORCEMENT.md` §8 for the
> integration punch list.

---

## Wave-end checklist

- **Changed files:**
  - `hermes_cli/jarvis_prime/__init__.py` (new, empty; owner-approved deviation from strict allowed-files list)
  - `hermes_cli/jarvis_prime/owner_auth.py` (new)
  - `hermes_cli/jarvis_prime/gates.py` (new)
  - `tests/test_jarvis_prime_owner_auth.py` (new)
  - `docs/aci/reports/W02_OWNER_AUTH_ENFORCEMENT.md` (new — this file)
- **Tests run:** `scripts/run_tests.sh tests/test_jarvis_prime_owner_auth.py -v` → 67 passed.
- **Compile check:** `python -m compileall hermes_cli/jarvis_prime` → clean.
- **Source-of-truth registry untouched:** `python skills/aos-enterprise-council/scripts/verify_registry.py` → "AOS registry verification passed."
- **Remaining risks:** no callers migrated (see §8); drift detector not yet in a CI workflow (forbidden by allowed-files in this wave).
- **Rollback:** `git revert` the wave commit. No persistent state to clean up.
- **PR mode:** draft only, per universal-header NON-OVERLAP CONTRACT.

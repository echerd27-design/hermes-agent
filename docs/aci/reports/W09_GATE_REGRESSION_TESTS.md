# Wave 09 — Gate Regression Tests

## Mission

Harden JARVIS verification gates with realistic ACI build packets and
regression tests. Bring the eight-gate spec at
`docs/jarvis-verification-gates.md` from prose into runtime form so
later ACI waves can call gates against a build packet and get a
deterministic `pass / fail / needs_owner_approval` result.

## Branch and Files Changed

- Branch: `aci/wave-09-gate-regression-tests`
- Files (exactly three, all new, all inside ALLOWED FILES):
  - `hermes_cli/jarvis_prime/gates.py`
  - `tests/test_jarvis_prime_gates.py`
  - `docs/aci/reports/W09_GATE_REGRESSION_TESTS.md`

`hermes_cli/jarvis_prime/` is a PEP 420 namespace subpackage; no
`__init__.py` was added because it was not in ALLOWED FILES.

## Gates Implemented

| Gate | Pass condition (summary) | Fail trigger examples | Test classes |
|---|---|---|---|
| `planning_gate` | repo, branch, goal, allowed_files, acceptance_criteria all present; owner gates identified | any required field empty; owner gates not identified | `TestPlanningGate` (incl. parametrized field-missing matrix) |
| `build_gate` | changed_files ⊆ allowed_files; no concurrent editors; no secret in diff; protected files only edited with approval; docs-only stage only touches docs | out-of-scope path; >1 distinct concurrent editor; secret pattern in diff; protected edit without approval; runtime change in docs-only stage | `TestBuildGate` |
| `review_gate` | findings carry severity and a blocking-vs-improvement split; contrarian objection recorded | missing severity; missing contrarian objection; non-empty diff with no findings | `TestReviewGate` |
| `test_gate` | tests ran and passed, **or** skipped with a reason AND a named unverified risk; `git diff --check` clean | tests failed; skipped without reason; skipped without naming the risk; whitespace errors | `TestTestGate` |
| `security_gate` | no secret in diff; no unreviewed dependency change; credential edits approved; no network calls added — returns `needs_owner_approval` when `is_publish_or_deploy=True` | secret pattern; dependency change without separate review; credential edit without approval; new network calls | `TestSecurityGate` |
| `release_gate` | changed_files, pr_summary, pr_body_ready, commits_scoped, verification_summary, rollback_plan, remaining_risks all present | any of those missing | `TestReleaseGate` (parametrized) |
| `owner_approval_gate` | no owner-gated action → pass; else `owner_approval == OWNER_APPROVAL_PHRASE` (exact equality) | typo, case change, trailing whitespace, missing period, empty | `TestOwnerApproval` |
| `rollback_gate` | rollback_plan present; if `risky_runtime_change`, also requires `revert_strategy` | missing rollback plan; risky runtime change without revert strategy | `TestRollbackGate` |

`run_all_gates(packet)` returns a `dict[str, GateResult]` with all
eight entries; `overall_status(results)` aggregates them — `"fail"`
dominates `"needs_owner_approval"` which dominates `"pass"`.

## Realistic ACI Build Packets Covered

All eight scenarios listed in the mission are exercised end-to-end in
`TestRealisticScenarios`:

1. Clean docs-only PR → all gates pass.
2. Code change with tests → all gates pass.
3. Dependency change — fails security without separate review; passes
   with separate review.
4. Secret accidentally added → fails build **and** security.
5. Owner-gated publish attempt — without phrase the overall result is
   `fail`; with the exact phrase the overall result is
   `needs_owner_approval` (publish/deploy never auto-passes).
6. Missing rollback → fails rollback **and** release.
7. Concurrent Claude + Codex branch edit → fails build.
8. No tests with a valid skip reason + named risk → test gate passes.

## Verification Commands and Results

```text
$ python -m compileall hermes_cli/jarvis_prime/gates.py
Compiling 'hermes_cli/jarvis_prime/gates.py'...
```

```text
$ uv run --with pytest --with pytest-timeout --with pytest-xdist \
    pytest tests/test_jarvis_prime_gates.py -p no:cacheprovider --no-header
created: 4/4 workers
4 workers [68 items]
....................................................................   [100%]
============================== 68 passed in 2.19s ==============================
```

```text
$ git diff --check
(clean)
```

68 tests collected: 8 per-gate classes (with multiple pass/fail
methods plus parametrized field matrices) + 9 realistic-scenario
tests + 7 owner-approval phrase tests + 7 aggregation tests + 2
packet-defaults tests.

## Acceptance Criteria Checklist

- [x] **Every gate has both pass and fail tests** — verified by
  `TestPlanningGate`…`TestRollbackGate` each containing at least one
  passing and one failing case.
- [x] **Owner approval gate requires exact phrase** — verified by
  `TestOwnerApproval::test_exact_phrase_passes`,
  `_typo_fails`, `_trailing_whitespace_fails`, `_case_change_fails`,
  and `_phrase_constant_locked`.
- [x] **Concurrent editors fail build gate** — verified by
  `TestRealisticScenarios::test_concurrent_claude_codex_branch_edit_fails_build`
  and `TestBuildGate`'s concurrent-editors path.
- [x] **Dependency changes require separate review** — verified by
  `TestSecurityGate::test_fail_on_dependency_change_without_separate_review`
  and the matching `_passes` test.
- [x] **No production deploy can pass without owner approval** —
  verified by
  `TestAggregation::test_no_production_deploy_passes_without_owner_approval`,
  which iterates over five near-miss phrases and asserts the overall
  status is never `"pass"`.

## Remaining Risks

- **Wheel-packaging gap.** `pyproject.toml`'s
  `[tool.setuptools.packages.find]` (line 223) currently lists
  `"hermes_cli"` without a `.*` wildcard. The new
  `hermes_cli.jarvis_prime` subpackage will be importable in the
  source tree (and in tests, because `tests/conftest.py` inserts the
  project root into `sys.path`), but it will **not** ship in the
  installed wheel. Editing `pyproject.toml` is out of scope for Wave
  09 (it is not in ALLOWED FILES). Follow-up wave should either add
  `"hermes_cli.*"` to the include list or move the gates module into
  the already-packaged `hermes_cli` flat namespace.
- **Gates not yet wired.** This wave only proves the contract. No
  caller in the codebase (orchestration, JARVIS handoff, CI hook)
  invokes `run_all_gates` yet. A separate wave is needed to wire
  invocations and surface the results.
- **Secret detection is shape-based.** `_SECRET_PATTERNS` looks for a
  small set of token shapes (`sk-`, `AWS_SECRET_ACCESS_KEY=`,
  `-----BEGIN PRIVATE KEY-----`, etc.). It is not a replacement for
  `truffleHog` / `gitleaks`. Future waves may want to add a hook
  that runs a dedicated secret scanner and feeds its result into
  `Packet.diff_text` / a richer field.

## Rollback

- The wave adds three new files and edits none. Delete them — or
  `git revert <wave-commit>` — to restore the prior state with no
  schema, lock, or dependency migration needed.
- No runtime currently imports the gates module, so removal cannot
  break any existing call site.
- If the wave needs to be re-cut, branch from `main`, recreate
  `aci/wave-09-gate-regression-tests`, and re-run the verification
  commands above.

## PR Summary (draft)

> Wave 09 hardens the JARVIS Prime verification gate system by
> bringing the eight-gate spec at `docs/jarvis-verification-gates.md`
> from prose into a runtime module (`hermes_cli/jarvis_prime/gates.py`)
> with a 68-test regression suite (`tests/test_jarvis_prime_gates.py`).
>
> Each gate accepts an ACI build packet (`Packet`) and returns a
> `GateResult` with status `"pass"`, `"fail"`, or
> `"needs_owner_approval"`. The owner-approval phrase is exact-match
> only ("I approve this owner-gated action."), and no publish/deploy
> packet can produce an overall `"pass"` without it.
>
> Wave is **scoped to three new files**; no other paths are touched.
> Known remaining risk: the new subpackage is not yet in the wheel's
> `setuptools.packages.find` include list — flagged for a follow-up
> wave that is allowed to edit `pyproject.toml`. Tests pass via
> `tests/conftest.py`'s `sys.path` insert.

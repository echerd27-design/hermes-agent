# Wave 07 — CI Baseline Triage: Planning Artifact

**Status:** PLAN ONLY. No implementation. Awaiting owner approval.

**Branch:** `aci/wave-07-plan` (this branch — plan-only).
**Implementation branches:** `aci/wave-07-phase-Nx-...` (one per phase).

## Mission brief

Restore the `test` job in `.github/workflows/tests.yml` to green on
`main`. Exit criterion is strictly the `test` job (not `e2e`, `nix`,
`ruff`, `supply-chain-audit`, or `osv-scanner` — those are separate
waves). Success is three consecutive green `test` runs on `main`
after the final phase merges.

## Evidence reviewed

Local reproduction commands:

```bash
uv pip install -e ".[all,dev]"
source .venv/bin/activate
python -m pytest tests/ -q --ignore=tests/integration --ignore=tests/e2e \
  --tb=short -n auto --timeout=30 --timeout-method=signal
```

### Baseline shift discovered during planning

Initial naive sync (`uv sync --extra dev` — missing `[all]`):
**117 failed + 35 errors + 23641 passed + 169 skipped**.

After correctly syncing `.[all,dev]` (the same command CI runs):
**48 failed + 12 errors + 24388 passed + 163 skipped**.

The 60-percent baseline reduction came from one cause: the
`agent-client-protocol==0.9.0` distribution installs as the top-level
module name `acp`. It is declared at `pyproject.toml:110` under the
`[acp]` extra, and `[acp]` is included in `[all]` at line 199. Once
`[all]` is actually installed, the 9-module ImportError wall vanishes
and the secondary xdist-pollution cascade I attributed to that wall
also vanishes.

**Implication:** if CI's `test` job is actually red with the same
~117 number we saw locally pre-sync, then CI's
`uv pip install -e ".[all,dev]"` is silently NOT installing the
recursive self-extra `[acp]`. That is a documented uv resolver
edge case for recursive self-extras on editable installs. **Verify
this before any other work** by adding a single `acp` import smoke
step to the CI workflow.

### Real baseline failure histogram (28 modules → 14 modules, 60 events)

| Module                                         | Count | Suspected cause              |
|------------------------------------------------|------:|------------------------------|
| `tests/cli/test_worktree.py`                   |    29 | `git commit` in fixture; container has no user.name/user.email |
| `tests/hermes_cli/test_gateway_service.py`     |     8 | systemd-only paths           |
| `tests/tools/test_ssh_environment.py`          |     7 | `RuntimeError: SSH is not installed or not in PATH. Install OpenSSH client: apt install openssh-client` |
| `tests/agent/test_context_references.py`       |     7 | TBD — investigate            |
| `tests/cli/test_worktree_security.py`          |     5 | Same git identity cause as `test_worktree.py` |
| `tests/tools/test_credential_pool_env_fallback.py` | 2 | TBD                          |
| `tests/tools/test_vision_tools.py`             |     1 | TBD                          |
| `tests/tools/test_terminal_output_transform_hook.py` | 1 | TBD                         |
| `tests/tools/test_credential_files.py`         |     1 | TBD                          |
| `tests/test_transform_llm_output_hook.py`      |     1 | TBD                          |
| `tests/hermes_cli/test_web_server.py`          |     1 | PTY readback empty in container (`TestPtyWebSocket`) |
| `tests/hermes_cli/test_update_hangup_protection.py` | 1 | TBD                         |
| `tests/hermes_cli/test_auth_nous_provider.py`  |     1 | TBD                          |
| `tests/gateway/test_complete_path_at_filter.py`|     1 | TBD                          |

**49 of 60 failures (82%) are environment-fixture issues** (git
identity, missing system tools). Only 11 remaining failures are
spread across 11 modules at 1-2 each — those are the genuine triage
targets.

### Council critiques folded in

The contrarian-reviewer caught a major flaw in the original draft:
"Phase 1 was going to add the `acp` dep, but it's already there
(`pyproject.toml:110`)." Both reviewers independently called for:

1. A frozen baseline artifact before any merge
   (`docs/aci/reports/W07_BASELINE.md`).
2. Splitting CI-env install (mechanical) from `acp` investigation
   (diagnostic).
3. Hunting xdist worker pollution **before** fixing victim tests, to
   avoid chasing ghost failures.
4. Hard cap on per-subsystem real-fix phase (5 subsystems / 15 days
   max).
5. Reordering so the cheapest mechanical phase runs first to shrink
   the surface for the harder pollution hunt.

## Candidate plans

### Plan A — Original "deps-first" sequence (REJECTED)

Phase 1 add `acp` dep → Phase 2 xdist hunt → Phase 3 skipif → Phase 4
per-subsystem fixes → Phase 5 flakes.

**Why rejected:** Phase 1 premise is wrong (dep is already declared);
PR would be a no-op and burn 1-2 days. Sequencing also wastes effort
because pollution victims may appear to need "fixing" until the
polluter is found.

### Plan B — Contrarian's "stabilize the instrument first"

Phase 0 classification matrix → Phase 1 worker isolation → Phase 2
re-baseline → Phase 3+ env/skipif/real fixes.

**Strength:** stabilizes the measurement instrument before fixing
what it measures. **Weakness:** pollution hunt is open-ended; could
balloon to a quarter. Also: with the corrected `.[all,dev]` baseline,
the apparent pollution surface shrank from ~30 victims to ~11,
suggesting most "pollution" was actually the cascade from the `acp`
install issue. Pollution-first may no longer be the right invariant.

### Plan C — RECOMMENDED — "verify-CI-environment-first, then surgical"

Sequenced for fastest-time-to-green given the corrected evidence:

- **Phase 0 (no code change, 1 hour):** Capture
  `docs/aci/reports/W07_BASELINE.md` — the frozen baseline of
  failing tests, the collection hash, and one classification axis
  (`-n0` vs `-n auto`) for each currently-failing module.
- **Phase 1 (single PR, CI plumbing only):** Add to
  `.github/workflows/tests.yml`:
  1. `apt install -y openssh-client` after the ripgrep install.
  2. `git config --global user.email ci@example.com && git config
     --global user.name "CI Runner"` after Python setup.
  3. A diagnostic step: `python -c "import acp; print(acp.__file__)"`
     run immediately after `uv pip install -e ".[all,dev]"`. If
     this step fails, the CI `[acp]` resolution edge case is
     confirmed and the `[acp]` extra must be installed explicitly
     in a follow-up commit.
- **Phase 2 (single PR, env-skip markers):** Add
  `@pytest.mark.skipif(...)` guards to:
  - `tests/hermes_cli/test_web_server.py::TestPtyWebSocket` (PTY
    unavailable in the test environment — wrap with a `_has_pty()`
    check, not just runtime detection).
  - `tests/hermes_cli/test_gateway_service.py` (systemd unavailable —
    `_has_systemd()`).
  - `tests/tools/test_ssh_environment.py` is now covered by Phase 1
    if CI installs openssh-client; no skip needed, but add a
    `skipif(not shutil.which("ssh"))` defense-in-depth so the
    suite is portable to dev environments without ssh.
- **Phase 3 (single PR, classification matrix on residual):** With
  Phases 1-2 merged, re-run the suite and produce a 3-column matrix
  per remaining failing test: passes under `-n0`, passes under
  `-n auto -p no:randomly`, passes under `-n auto`. Commit the
  matrix to `docs/aci/reports/W07_RESIDUAL.md`. This bounds Phase 4
  with concrete data.
- **Phase 4 (1 PR per subsystem, hard cap 5 subsystems / 15 days):**
  Real fixes for the 11 residual failing modules. Each PR has its
  own allowed-files allowlist. Kill criterion: at 3 subsystems in 9
  days, escalate to owner for triage; remaining failures get xfail
  markers and spin out to Wave 08.
- **Phase 5 (single PR, only if needed):** Flake stabilization for
  any tests showing nondeterminism after Phase 4 (none currently
  observed in the corrected baseline).

## Scorecard

| Criterion                          | A (deps-first) | B (pollution-first) | C (CI-env-first) |
|------------------------------------|---------------:|--------------------:|-----------------:|
| Time to green (estimated)          |  Worst         | Worst (open-ended)  | **Best**         |
| Probability Phase 1 ships          |  Low           | Medium              | **High**         |
| Risk of masking real regressions   |  Medium        | Low                 | Medium           |
| Wave-discipline alignment          |  Medium        | Low                 | **High**         |
| Owner-approval surface area        |  Wide          | Wide                | **Narrow**       |
| Bisectability of failures          |  Poor          | Best                | Good             |

**Plan C wins** because the corrected baseline shows pollution is
not the dominant cluster (49/60 failures are environment-fixture).
Verify CI's actual environment first; classify residuals second.

## Open blockers and decisions needed from owner

Before Phase 1 starts, the owner must decide:

1. **`acp` resolver edge case.** If Phase 1's diagnostic step
   confirms CI is not installing `[acp]`, do you want:
   (a) explicit `[acp]` in the CI install line, or
   (b) flatten `[all]` to not depend on the recursive self-extra
   (cleaner long-term but touches `pyproject.toml`)?
2. **PTY/systemd skipif policy.** Should environment-dep tests use
   (a) hard `skipif` markers that always skip in CI as long as the
   env isn't there, or (b) `xfail(strict=True)` so the team sees
   green-but-yellow status? Recommend (a) for clarity.
3. **Phase 4 hard cap.** Confirm 5 subsystems / 15 days kill
   criterion. If less aggressive (e.g., 8/30), say so now.
4. **Out-of-scope items.** Confirm these are explicitly OUT of Wave
   07: `e2e` job, `nix` job, `ruff + ty diff` warnings, OSV scanner,
   supply-chain audit, the lint-diff bot's pre-existing 9010 ty
   warnings, CodeRabbit configuration.
5. **Wave 06 PR #41 merge timing.** Wave 07 Phase 0 baseline should
   be captured against the same SHA whether or not #41 is merged.
   Recommend: capture baseline on `main` (excluding #41) so the
   baseline doesn't drift with Wave 06's status.

## Build phases (acceptance criteria + validation per phase)

### Phase 0 — Frozen baseline (no code change, but is a PR)

- **Branch:** `aci/wave-07-phase-0-baseline`
- **Allowed files:** `docs/aci/reports/W07_BASELINE.md` (new).
- **Acceptance criteria:**
  - The report contains: SHA of `main` at capture; full
    `pytest --collect-only -q | sha256sum`; per-failing-module
    pass/fail count; a one-line cause hypothesis per module.
  - No tests are modified.
- **Validation:** `git diff --stat` shows only one file changed.
- **Rollback:** revert the single doc commit; no code is touched.

### Phase 1 — CI environment install (single PR)

- **Branch:** `aci/wave-07-phase-1-ci-env`
- **Allowed files:**
  - `.github/workflows/tests.yml` (only)
  - `docs/aci/reports/W07_PHASE1.md` (new — wave-discipline report)
- **Acceptance criteria:**
  - Workflow installs `openssh-client` and configures
    `git config --global user.email/name` before tests run.
  - Workflow adds a diagnostic step
    `python -c "import acp; print(acp.__file__)"` after
    `uv pip install -e ".[all,dev]"`.
  - On the PR, CI's `test` job runs and either (a) the 7 ssh
    failures and 34 git-identity failures clear and `test` shows a
    materially smaller failure count, or (b) the diagnostic step
    fails with `ModuleNotFoundError: No module named 'acp'`, which
    is itself the answer to question 1 above.
- **Validation:**
  - `gh pr view ...` shows `test` job result delta vs baseline.
  - Locally: cannot fully validate (the change is CI-only) — call
    it out in the PR body.
- **Rollback:** revert the single workflow commit.

### Phase 2 — Environment-dependent test guards (single PR)

- **Branch:** `aci/wave-07-phase-2-skipif`
- **Allowed files:**
  - `tests/hermes_cli/test_web_server.py` (only the
    `TestPtyWebSocket` class — wrap with skipif).
  - `tests/hermes_cli/test_gateway_service.py` (only the systemd
    class — wrap with skipif).
  - `tests/tools/test_ssh_environment.py` (defensive
    `skipif(not shutil.which("ssh"))` at module top).
  - A new `tests/_env_helpers.py` containing `_has_pty()`,
    `_has_systemd()`, `_has_ssh()` helpers (stdlib only).
  - `docs/aci/reports/W07_PHASE2.md` (new).
- **Acceptance criteria:**
  - Each skip marker has a clear `reason=` explaining the env
    requirement.
  - In CI, the skip count goes up by exactly the count of guarded
    tests; failure count goes down by the same.
  - Locally on a dev machine WITH the deps, every guarded test
    still runs and either passes or fails as it did before — the
    guard does not skip when capable.
- **Validation:**
  - `pytest tests/hermes_cli/test_web_server.py
    tests/hermes_cli/test_gateway_service.py
    tests/tools/test_ssh_environment.py -v` — shows skipped reasons.
  - Diff `--collect-only` hash vs Phase 0 baseline — only the
    guarded tests should change collection state.
- **Rollback:** revert the PR; the suite goes back to producing
  hard failures (not regressions).

### Phase 3 — Residual classification matrix (single PR)

- **Branch:** `aci/wave-07-phase-3-residual-matrix`
- **Allowed files:** `docs/aci/reports/W07_RESIDUAL.md` (new) +
  optional `scripts/classify_test_failures.py` (stdlib only) if a
  helper is warranted.
- **Acceptance criteria:**
  - For each test still failing after Phases 1+2, the report
    records: passes under `-n0`, passes under
    `-n auto -p no:randomly`, passes under `-n auto`.
  - The 11 residual modules are categorized as
    `genuine|pollution_victim|polluter|flake|env`.
- **Validation:** owner reviews the matrix before Phase 4 starts.
- **Rollback:** revert the doc(s); no code touched.

### Phase 4 — Per-subsystem real fixes (1 PR per subsystem)

- **Branches:** `aci/wave-07-phase-4-<subsystem>`
- **Hard cap:** 5 subsystems / 15 days. Escalate at 3/9.
- **Allowed files:** strictly the subsystem's source files + its
  tests + a per-phase report under `docs/aci/reports/W07_PHASE4_<n>.md`.
- **Acceptance criteria:**
  - Each PR includes a before/after run of the targeted tests in
    isolation AND in full-suite AND under `-p no:randomly` AND with
    `--forked` (per assurance director's gate).
  - The PR body names the root cause (not "fixed flakiness").
- **Validation:** `pytest <subsystem>/ -v` + a 3x full-suite re-run
  for order-sensitivity.
- **Rollback:** revert the per-subsystem PR.

### Phase 5 — Flake stabilization (single PR, only if Phase 3
matrix shows flakes)

- **Branch:** `aci/wave-07-phase-5-flakes`
- **Allowed files:** the flaky test files + a Phase 5 report.
- **Acceptance criteria:** rerun-stable for 10 consecutive runs.
- **Validation:** `for i in $(seq 1 10); do pytest <files> -q; done`
- **Rollback:** revert.

## Validation (wave-wide)

After every phase merges to `main`:

1. Three consecutive scheduled-trigger runs of `.github/workflows/tests.yml`
   on `main` must show `test = success`.
2. The `e2e` and `nix` jobs are explicitly out of scope; their
   status doesn't gate this wave.
3. The final wave report `docs/aci/reports/W07_DONE.md` ships
   alongside Phase 4's last merge (or Phase 5 if used) and includes:
   the green-run evidence, the per-phase summaries, the residual
   list (anything escalated to Wave 08), and the rollback playbook
   for the wave as a whole.

## Risks and mitigations

| Risk                                     | Likelihood | Mitigation |
|------------------------------------------|-----------:|------------|
| Phase 1 diagnostic says `acp` IS importable in CI — meaning the original 117 number came from a different cause we haven't found | Medium | Phase 0's classification matrix exists precisely for this — re-baseline mid-wave if Phase 1's signal contradicts expectations. |
| Phase 4 balloons past 5 subsystems | Medium | Hard cap. Escalate at 3/9 days. |
| A skipif marker accidentally hides a genuine regression | Medium | Phase 0 baseline + Phase 3 collection-hash diff catch any post-merge skip count drift. |
| Polluter test lives in a file we never touch | Low | Phase 3 matrix isolates pollution; Phase 4 fixes polluter at source, not victims. |
| CI workflow changes need GitHub Actions approvals not granted to Claude | Medium | Phase 1 PR opens as draft; owner takes it through human review. |

## Out of scope (must NOT be done in Wave 07)

- The `e2e` job in `tests.yml`.
- The `nix`, `ruff + ty diff`, `Windows footguns`, `Scan PR for
  critical supply chain risks`, `Check PyPI dependency upper bounds`,
  `check-attribution`, `check-common-ancestor` jobs.
- The 9010 pre-existing `ty` type-checker warnings (lint-diff bot
  explicitly says "never fails the build").
- CodeRabbit configuration or `.coderabbit.yaml`.
- Wave 06 (PR #41) merge timing decisions.
- Any new third-party dependency unless Phase 1's diagnostic
  forces one.
- Test isolation architecture changes (per-test subprocess workers,
  full `--forked` mode by default, etc.) — that's a Wave 08
  conversation.
- Any product-code refactor beyond the minimum needed to fix a
  Phase 4 test.

## Council perspectives (folded in)

### Principal systems architect (implicit from prior wave conventions)

The wave structure mirrors Wave 06's discipline: small allowed-files
allowlist, per-phase wave report under `docs/aci/reports/`, draft
PRs only, no merges without owner approval. Each phase is a complete
unit that can stand alone if the wave is aborted mid-stream.

### Contrarian reviewer (summary)

Caught the `acp`-is-already-declared flaw. Insisted on:
- Classification matrix BEFORE any phase that "fixes" tests.
- Worker pollution as the underlying invariant to stabilize.
- Hard scope cap on per-subsystem phase.

Plan C folds in (1) and (3); folds in (2) as Phase 3 rather than
Phase 1, justified by the corrected baseline showing pollution is no
longer the dominant cluster (the `acp` cascade explained most
apparent pollution).

### Assurance-risk director (summary)

GO with three amendments:
- Frozen W07_BASELINE.md gate (Phase 0).
- Split CI-env install (mechanical) from acp investigation
  (diagnostic) — Plan C does this via the diagnostic step inside
  Phase 1.
- Phase 4 hard-capped at 5 subsystems / 15 days. Done.

### Delivery-scope-controller (summary)

Hard exit criterion = `test` job green only. Reorder so the
cheapest mechanical phase runs first to shrink the surface for the
harder pollution hunt. Done (Phase 1 is CI env install).

## Acceptance criteria (wave-wide)

1. `.github/workflows/tests.yml` `test` job is green on 3
   consecutive `main` runs.
2. Skip count drift between Phase 0 baseline and Wave 07 done is
   explained in `W07_DONE.md` line-by-line.
3. No skipped test was skipped without a reason citing the
   environment requirement.
4. No third-party dep was added without an explicit owner-approved
   risk gate per the assurance director's policy.
5. No file outside the per-phase allowed-files allowlist was
   modified in any phase PR.

## Validation commands (wave-wide)

```bash
# Per-phase, before opening PR:
source .venv/bin/activate
python -m pytest tests/ -q --ignore=tests/integration --ignore=tests/e2e \
  --tb=short -n auto --timeout=30 --timeout-method=signal

# Order-sensitivity check (Phase 4 specifically):
for seed in 1 2 3; do
  python -m pytest tests/ -q --ignore=tests/integration --ignore=tests/e2e \
    -p randomly --randomly-seed=$seed --tb=no
done

# Collection-hash check (every phase):
python -m pytest --collect-only -q | sha256sum
```

## Rollback notes (wave-wide)

- Each phase is a standalone PR. Revert order: Phase 5 → 4 → 3 → 2 → 1 → 0.
- Phase 1's CI workflow change is the only one that affects CI
  itself; reverting it restores the pre-wave CI behavior exactly.
- Phase 2's skipif markers are pure subtractions from the run set
  on a system without the env deps, and pure no-ops on systems with
  them. Reverting reproduces the original failures, not new ones.

## Open questions (blocking only)

1. Owner: which option for the `acp` resolver edge case if Phase 1
   confirms it (explicit `[acp]` in CI install, vs flatten
   `[all]`)?
2. Owner: is the 5-subsystem / 15-day Phase 4 cap acceptable, or
   too tight / too loose?
3. Owner: should Wave 07 start before, after, or in parallel with
   Wave 06 PR #41's merge?

---

End of plan. Implementation does not begin until owner approves
and explicitly authorizes Phase 0.

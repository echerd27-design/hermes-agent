# W06 — Task Graph Planner

## Mission

Add a deterministic, stdlib-only task graph planner for nine common JARVIS Prime
missions. Each plan separates `builder`, `reviewer`, `tester`, and
`owner_approval` phases so downstream waves (W07 `jobs.py`, W08 `job_store.py`)
can queue and execute work against a stable, diffable contract.

## Scope

- **Branch:** `aci/wave-06-task-graph-planner`
- **Allowed files (touched):**
  - `hermes_cli/jarvis_prime/task_planner.py`
  - `hermes_cli/jarvis_prime/__init__.py`
  - `tests/test_jarvis_prime_task_planner.py`
  - `docs/aci/reports/W06_TASK_GRAPH_PLANNER.md`
- **Forbidden files (not touched):**
  - `hermes_cli/jarvis_prime/jobs.py`
  - `hermes_cli/jarvis_prime/job_store.py`
  - `gateway/**`, `apps/android/**`, `pyproject.toml`, `uv.lock`, `README.md`

## Changed Files

| Status | Path |
|---|---|
| A | `hermes_cli/jarvis_prime/__init__.py` |
| A | `hermes_cli/jarvis_prime/task_planner.py` |
| A | `tests/test_jarvis_prime_task_planner.py` |
| A | `docs/aci/reports/W06_TASK_GRAPH_PLANNER.md` |

No file outside the allowed list was modified.

## Public API

Exported from `hermes_cli.jarvis_prime`:

- `MISSIONS: tuple[str, ...]` — nine frozen mission keys.
- `plan_for(mission: str) -> dict` — dispatcher; raises `ValueError` on unknown mission.
- `plan_repo_audit()`, `plan_bug_fix()`, `plan_launch_readiness()`,
  `plan_android_build_check()`, `plan_gateway_setup()`, `plan_slack_setup()`,
  `plan_docs_only_update()`, `plan_security_review()`, `plan_release_pr()` —
  one per supported mission, each `-> dict`.

## Plan Schema (v1.0)

```text
{
  "mission":     str,
  "version":     "1.0",
  "summary":     str,
  "phase_order": ("builder", "reviewer", "tester", "owner_approval"),
  "phases": [
    {
      "name":  str,                     # one of phase_order
      "tasks": [
        {
          "id":         str,            # "{mission}.{phase}.{slug}"
          "title":      str,
          "role":       str,            # == phase name
          "agent":      str,            # AOS council member or JARVIS worker
          "gate":       str,            # JARVIS verification gate
          "depends_on": list[str],      # task ids within the same plan
        },
        ...
      ],
    },
    ...
  ],
  "edges": list[tuple[str, str]]        # sorted lexically, derived from depends_on
}
```

Agent names match the AOS Council bench in `CLAUDE.md` plus JARVIS workers in
`docs/jarvis-prime-operating-system.md`. Gate names match
`docs/jarvis-verification-gates.md`.

## Mission Coverage

| Mission | Tasks | Edges |
|---|---:|---:|
| `repo_audit` | 6 | 6 |
| `bug_fix` | 7 | 9 |
| `launch_readiness` | 6 | 7 |
| `android_build_check` | 5 | 5 |
| `gateway_setup` | 6 | 7 |
| `slack_setup` | 5 | 5 |
| `docs_only_update` | 5 | 5 |
| `security_review` | 6 | 7 |
| `release_pr` | 6 | 7 |

## Verification

Commands run from the repo root:

```bash
python -m compileall hermes_cli/jarvis_prime/task_planner.py \
                     hermes_cli/jarvis_prime/__init__.py
# → both files compile clean

grep -nE "^(from|import)\s+\S*(jobs|job_store)" \
     hermes_cli/jarvis_prime/task_planner.py \
     hermes_cli/jarvis_prime/__init__.py
# → no matches (exit 1)

uv run --with pytest-xdist --with pytest-timeout pytest \
     tests/test_jarvis_prime_task_planner.py -v -o addopts=""
# → 98 passed
```

The 98-test suite covers (≥ 8 mission types via parameterization):

- frozen `MISSIONS` tuple with 9 unique keys
- `PHASE_ORDER` matches the wave contract
- four-phase separation for every mission
- each task's `role` matches its phase name
- task ids unique and mission/phase namespaced
- `depends_on` references resolve within plan
- `edges` derived from `depends_on` and sorted
- determinism — `plan_*()` is a pure function
- `plan_for` dispatch + `ValueError` for unknown
- returned plans isolated from internal state
- no forbidden imports in `task_planner.py` or `__init__.py`
- all agent names are known council/worker names
- all gate names are known verification gates

## Gate Summary

```text
GATE SUMMARY
Planning gate:        pass — scope and allowed files locked
Build gate:           pass — only allowed files modified
Review gate:          pass — pure-data module, no side effects, no I/O
Test gate:            pass — 98 / 98 passed; ≥ 8 mission coverage
Security gate:        pass — no secrets, no network, no credentials
Release gate:         pass — draft PR only; no merge
Owner approval gate:  not required — internal, no public surface
Rollback gate:        pass — single-commit revert
Result:               ready for review
Remaining risk:       schema v1.0 will be consumed by W07/W08; coordinate
                      changes if shape evolves
```

## Remaining Risks

1. **Schema coupling.** W07 (`jobs.py`) and W08 (`job_store.py`) will consume the
   v1.0 plan shape. A breaking change after merge requires a coordinated PR
   across all three waves. Mitigation: `version` field already present so a
   future v2.0 can coexist.
2. **String-coupled agent and gate names.** Agent names are matched against
   `CLAUDE.md` and JARVIS docs; gates against
   `docs/jarvis-verification-gates.md`. Renames there require a matching update
   here. Tests pin the known set so the next mover sees the breakage.
3. **Deliberate non-feature: no execution.** This module produces graphs only.
   Anyone reading `plan_for("bug_fix")` and expecting it to start work will be
   disappointed; W07/W08 are the execution surface.

## Rollback Plan

```bash
git revert <commit-sha>
```

No downstream consumers exist on this branch (`jobs.py` / `job_store.py` are
forbidden in this wave and created elsewhere), so the revert is clean and
non-orphaning. The `hermes_cli/jarvis_prime/` directory is created by this
wave and would be removed by the revert.

## PR Summary

W06 adds `hermes_cli/jarvis_prime/task_planner.py`, a deterministic stdlib-only
producer of task graphs for nine JARVIS Prime missions. Each plan separates
builder, reviewer, tester, and owner_approval phases with AOS-aligned agents
and verification gates. No runtime side effects, no I/O, no LLM. 98 tests pass.
Consumed by W07 / W08 in later waves; draft PR only — no merge.

# W06 — JARVIS Prime Durable Job Model

## Mission

Wave 06 establishes the **stdlib-only durable data model** for JARVIS
Prime: jobs decomposed into tasks, a validated status state machine,
dependency-blocking semantics, worker assignments, verification gate
evidence at both task and job level, an append-only event log, and a
deep JSON round-trip. The model lives at
`hermes_cli/jarvis_prime/jobs.py` and is exported through the new
`hermes_cli.jarvis_prime` package. **Nothing in this wave is wired
into the gateway, persistence, or any runtime system**; later waves
will carry the model into those surfaces.

## Changed files

- `hermes_cli/jarvis_prime/__init__.py` (new package init,
  re-exports the public surface).
- `hermes_cli/jarvis_prime/jobs.py` (the data model, validator,
  exceptions, and serialization).
- `tests/test_jarvis_prime_jobs.py` (41 collected tests across 8
  test classes).
- `docs/aci/reports/W06_JOB_MODEL.md` (this report; new
  `docs/aci/reports/` directory chain).

No other files were modified. `hermes_cli/__init__.py` and every
existing module are untouched.

## Design summary

- **`TaskStatus`** has exactly the 7 values required by the wave
  prompt: `planned`, `running`, `validating`, `blocked`, `failed`,
  `done`, `cancelled`.
- **Status transition table** (audited "middle" path —
  failed-must-re-queue, validating-may-rerun-in-place,
  cancel-from-anywhere):
  ```
  planned    → running, blocked, cancelled
  running    → validating, blocked, failed, cancelled
  validating → done, failed, running, cancelled
  blocked    → planned, cancelled
  failed     → planned, cancelled
  done       → (terminal)
  cancelled  → (terminal)
  ```
- **Dataclasses** (in dependency order): `TaskDependency`,
  `WorkerAssignment`, `GateEvidence`, `JobEvent`, `Task`, `Job`.
  All IDs are UUID-hex strings via `field(default_factory=...)`;
  all timestamps are ISO 8601 UTC strings with trailing `Z`.
- **Dependency-blocking**: `Job.transition_task(task_id, RUNNING)`
  enforces that every `kind="blocks"` predecessor is `DONE`,
  otherwise raises `DependencyBlockedError` carrying the offending
  ids. `kind="informs"` edges never block.
- **Cycle detection**: `Job.add_dependency` runs a 3-color DFS over
  the blocking-edge subgraph and rolls back the speculative edge if
  a cycle is detected (`CyclicDependencyError`).
- **Event log**: every mutating method on `Job` (`add_task`,
  `add_dependency`, `assign_worker`, `record_gate`,
  `record_job_gate`, `note`, `transition_task`) appends exactly one
  `JobEvent` of a typed event_type. Direct callers are expected
  not to mutate `events`, `gates`, or `tasks` outside the API.
- **Gates at both levels**: `Task.gates` for per-task verification
  evidence; `Job.gates` for spans-multiple-tasks gates such as
  `release` and `owner_approval`.
- **Serialization**: `Job.to_dict`/`Job.from_dict` and the JSON
  wrappers preserve the full graph (tasks, deps, workers,
  per-task gates, job-level gates, events, metadata,
  `schema_version`).
- **`GateType`** mirrors `docs/jarvis-verification-gates.md`
  vocabulary: planning, build, review, test, security, release,
  owner_approval, rollback.

## Verification commands run

- `python -m compileall hermes_cli/jarvis_prime/jobs.py
  hermes_cli/jarvis_prime/__init__.py` → both files compiled cleanly.
- `.venv/bin/pytest tests/test_jarvis_prime_jobs.py -v` →
  **41 passed in 3.59s** (xdist parametrization expands the legal-
  edge and cancel-from-anywhere parametrized tests).
- `python -c "from hermes_cli.jarvis_prime import Job, Task,
  TaskStatus, validate_transition; print('ok')"` → `import ok`.
- JSON round-trip smoke (Job with one task) → `round-trip ok`.

## Tests run

All 8 test classes green:

- `TestTaskStatusEnum` (3) — exactly 7 members; expected lowercase
  values; only `DONE` and `CANCELLED` are terminal.
- `TestValidateTransition` (15 incl. parametrizations) — every
  legal edge passes; self-loops, `done`/`cancelled` outgoing edges,
  and the `failed → running` direct-retry edge all raise; the
  error message names valid targets.
- `TestJobConstruction` (3) — auto-IDs and ISO-shaped timestamps;
  uniqueness across 50 constructions.
- `TestDependencyBlocking` (4) — `blocks` dep prevents
  `planned → running`; unblocks at predecessor `DONE`; `informs`
  never blocks; `UnknownTaskError` for missing IDs.
- `TestCyclicDependencyDetection` (2) — self-edges and two-node
  cycles rejected at `add_dependency`; speculative edge rolled
  back on cycle detection.
- `TestJobEventLog` (3) — one event per mutation, correct
  `event_type`, `from_status` / `to_status` recorded for
  transitions.
- `TestJobLevelGates` (2) — job-level vs task-level gate routing.
- `TestSerializationRoundTrip` (4) — empty job, schema_version
  presence, enum-as-string, fully-populated deep round-trip.

## Remaining risks

- **DAG acyclicity is enforced only at edge-insert time.** A
  mutation pattern that bypasses `Job.add_dependency` (e.g.
  appending directly to `task.dependencies`) is unprotected. The
  API surface is the contract; we don't enforce immutability of
  the dataclass fields.
- **No persistence layer yet.** Callers are responsible for
  driving `to_json`/`from_json` themselves. A later wave should
  add a persistence boundary (file or DB) and a write barrier.
- **Single-writer assumption.** No locking; concurrent mutation
  of the same `Job` is undefined. Acceptable for W06 since this
  is a pure in-memory model.
- **No replay-from-events constructor.** The event log records
  history but cannot today rebuild a `Job` from `events` alone —
  the model snapshot is the source of truth.

## Out of scope (deferred)

- Gateway/runtime wiring of `Job` and friends.
- Persistence: SQLite, file-backed stores, or hooks into
  `kanban_db.py`.
- Replay-from-events `Job` reconstruction.
- Schema migration helpers for `SCHEMA_VERSION` bumps.
- Cross-job operations (multi-job DAGs, job-of-jobs).
- Concurrency primitives (locking, optimistic writes).
- CLI/skill integration that exposes the model to users.

## Rollback plan

The wave is **purely additive**. To revert:

1. `git rm hermes_cli/jarvis_prime/jobs.py
   hermes_cli/jarvis_prime/__init__.py
   tests/test_jarvis_prime_jobs.py
   docs/aci/reports/W06_JOB_MODEL.md`
2. `rmdir hermes_cli/jarvis_prime docs/aci/reports docs/aci`
3. Commit and push the deletion.

No shared module was touched, so no downstream consumers can be
broken by removal.

## PR summary

- **Title**: `feat(jarvis-prime): durable job model (Wave 06)`
- **Body skeleton**:
  - Summary — three bullets: stdlib data model, status state
    machine, JSON round-trip; explicitly NOT wired to gateway.
  - Files changed — the four allowed files.
  - Verification — the four commands run above with results.
  - Risks — the four bullets in "Remaining risks".
  - Rollback — pointer to this report's rollback plan.
- **Draft only.** Do not merge in this wave; the wave's
  acceptance is the green test run plus this report.

## Gate summary

| Gate              | Outcome         | Evidence |
|-------------------|-----------------|----------|
| Planning          | pass            | `/root/.claude/plans/universal-header-you-are-encapsulated-scott.md` (approved plan); two clarifying questions answered (transition rules: audit; gates: task-level + job-level). |
| Build             | pass            | `python -m compileall hermes_cli/jarvis_prime/jobs.py hermes_cli/jarvis_prime/__init__.py` clean. |
| Review            | self-review     | Plan agent + this implementation; no external reviewer in W06. Codex review deferred to a follow-up wave. |
| Test              | pass            | `.venv/bin/pytest tests/test_jarvis_prime_jobs.py -v` → 41 passed. |
| Security          | pass (low risk) | Pure stdlib dataclasses; no I/O, no network, no eval, no secrets handled. |
| Release           | n/a (W06)       | No release in this wave; draft PR only. |
| Owner approval    | pending         | Awaiting owner sign-off on the draft PR. |
| Rollback          | ready           | Pure-additive; see "Rollback plan" section. |

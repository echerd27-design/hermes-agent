# Wave 06 — Local Job Store

Branch: `aci/wave-06-local-job-store`
Status: draft PR

## Mission

Create a local filesystem job store for durable JARVIS jobs, with the
per-job layout:

```
~/.hermes/jobs/<job-id>/
  job.json
  ledger.jsonl
  artifacts/
  reports/
```

## Changed files

| File | Purpose |
| --- | --- |
| `hermes_cli/jarvis_prime/__init__.py` | New package. Re-exports `JobStore`. |
| `hermes_cli/jarvis_prime/job_store.py` | New module. `JobStore` class — CRUD, append-only ledger, list. |
| `tests/test_jarvis_prime_job_store.py` | New test module. 29 tests covering every public method. |
| `docs/aci/reports/W06_LOCAL_JOB_STORE.md` | This wave report. |

No files outside the ALLOWED list were touched. `cron/jobs.py` was not
modified.

## Design summary

- `JobStore(root=None)` — schema-agnostic, root injectable for tests, default
  is `get_hermes_home() / "jobs"` resolved **lazily** so tests that redirect
  `HERMES_HOME` after construction still see the redirect.
- `create_job(data, job_id=None)` — generates a 12-char hex id (matching the
  `cron/jobs.py:594` convention) when not supplied. Caller-supplied dict is
  merged with three store-owned fields (`id`, `created_at`, `updated_at`).
  Raises `FileExistsError` on duplicate.
- `load_job` / `save_job` — atomic write via tempfile + fsync + `os.replace`
  (`utils.atomic_replace`, the symlink-aware helper at `utils.py:61`). The
  `id` and `created_at` fields are preserved across saves so a stray dict
  cannot rebrand a job.
- `list_jobs()` — sorted ids; orphan directories without a `job.json` are
  skipped silently.
- `delete_job(job_id)` — recursive removal. Returns `True` if anything was
  deleted.
- `append_ledger(job_id, entry)` — single-line append to `ledger.jsonl` with
  fsync. Auto-injects `ts` (UTC ISO) when the caller doesn't provide one.
  POSIX `O_APPEND` gives us atomicity within a single process for the small
  writes we emit.
- `read_ledger(job_id)` — returns ordered list of dicts. Malformed lines are
  logged at WARNING and skipped (forward-compatibility for partial appends).

## Reused utilities

- `hermes_constants.get_hermes_home()` — single source of truth for
  `~/.hermes/`. The autouse `_hermetic_environment` fixture in
  `tests/conftest.py:331` redirects `HERMES_HOME` to a per-test tempdir, so
  the store is automatically isolated in the wider test suite. Wave-06
  tests still pass an explicit `root` for in-isolation runs.
- `utils.atomic_replace` — symlink-aware `os.replace` wrapper used by
  `cron/jobs.py:save_jobs` for the same atomicity pattern.

## Tests run

```bash
python -m compileall hermes_cli/jarvis_prime/job_store.py      # exit 0
python -m pytest tests/test_jarvis_prime_job_store.py -v       # 29 passed in 3.73s
```

Coverage spans:
- Directory shape & ID generation (5 tests)
- Load / save round-tripping & bookkeeping invariants (6 tests)
- `list_jobs` & `delete_job` (5 tests)
- Ledger append, read, malformed-line handling, missing-job handling (8 tests)
- Default-root lazy resolution via `HERMES_HOME` (3 tests)
- Misc API guards (2 tests)

## Remaining risks

- **No cross-process locking** on the ledger. POSIX `O_APPEND` is atomic
  within a single process for small writes, but two gateways appending
  concurrently could in principle interleave. Acceptable for Wave 06; a
  later wave can add `fcntl.flock` if multi-process appends become a real
  scenario.
- **No permission tightening (0700 / 0600).** `cron/jobs.py` chmods its
  dirs to owner-only as a best-effort, but the acceptance list for this
  wave does not require it. Adding it later is an orthogonal change
  with no API churn.
- **Schema is open by design.** `job.json` accepts any JSON-serialisable
  dict. The lifecycle / dispatcher wave will introduce a schema, runtime
  validation, and well-known fields (state, owner, mode, etc.) on top of
  this store.

## Rollback

```bash
git checkout main          # or whichever base branch
git branch -D aci/wave-06-local-job-store
rm -rf hermes_cli/jarvis_prime
rm tests/test_jarvis_prime_job_store.py
rm docs/aci/reports/W06_LOCAL_JOB_STORE.md
rmdir docs/aci/reports docs/aci          # optional, only if empty
```

The store has no migrations, no schema, no consumers in this PR — removing
the four files removes 100% of the wave.

## PR summary

Wave 06 adds a per-job filesystem store at `~/.hermes/jobs/<id>/` (with
`job.json`, append-only `ledger.jsonl`, `artifacts/`, and `reports/`) for
durable JARVIS jobs. Schema-agnostic dict storage, atomic `job.json` writes
via tempfile + `os.replace`, append-only ledger with optional caller
timestamps, no SQLite, no changes to `cron/jobs.py`. 29 tests; foundation
for the JARVIS job lifecycle wave.

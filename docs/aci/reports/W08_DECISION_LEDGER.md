# Wave 08 — Decision Ledger

| Field | Value |
|-------|-------|
| Wave | 08 — Decision Ledger |
| Branch | `aci/wave-08-decision-ledger` |
| Parent | `claude/adoring-volta-KueMP` |
| Role | `/builder` |
| Date | 2026-05-26 |

## Summary

Adds an append-only JSONL decision-ledger helper at `hermes_cli/jarvis_prime/ledger.py`. Standalone (stdlib only), independent of the wave's sibling files `events.py` and `job_store.py` (owned by other waves and not present on this branch).

## Changed files

- `hermes_cli/jarvis_prime/__init__.py` — new subpackage marker; re-exports the ledger public API.
- `hermes_cli/jarvis_prime/ledger.py` — the helper (stdlib only).
- `tests/test_jarvis_prime_ledger.py` — 16 pytest cases covering append, read, tail, filter, and corruption tolerance.
- `docs/aci/reports/W08_DECISION_LEDGER.md` — this report.

No file outside the wave's ALLOWED FILES list was modified.

## Public API

```python
append(path, event: dict) -> None
read(path) -> ReadResult                       # records + corrupt lines
tail(path, n: int) -> list[LedgerRecord]
filter_by_type(path, event_type: str) -> list[LedgerRecord]
```

Supporting frozen dataclasses: `LedgerRecord(line_number, payload)`, `CorruptLine(line_number, raw, error)`, `ReadResult(records, corrupt)`.

Contract: one JSON object per line; corrupt lines are reported via `ReadResult.corrupt`, never raised; missing files read as empty; blank lines silently skipped.

## Decision record (this wave)

- **Evidence.** `hermes_cli/jarvis_prime/` did not exist on this branch — fully greenfield. The "decision ledger" concept is defined in `skills/aos-enterprise-council/agents/qa/decision-quality-gate.md` (evidence → options → choice → validation → rollback). Wave mission listed sibling files as forbidden / not-to-import, so isolation is structural, not just stylistic.
- **Options considered.**
  - *Class-based vs function-based.* Function-based chosen — file-path-driven matches other `hermes_cli/` file stores (cron, kanban), avoids state, and keeps the import surface flat.
  - *SQLite vs JSONL.* JSONL chosen — mission specified "append JSONL event", append-only is a one-line write with OS-level atomicity for small lines, no schema migration, trivially diff-able for review.
  - *Raise vs report on corruption.* Report chosen — mission criterion is "tolerate corrupted line by reporting it, not crashing". `ReadResult` exposes both halves so callers can audit without try/except boilerplate.
  - *Dataclass vs TypedDict for records.* Frozen dataclass chosen — gives equality + repr for free and matches the immutability of the underlying ledger entries.
- **Choice + rationale.** Function-based, JSONL, dataclass records, report-on-corrupt. Smallest surface that satisfies the spec, zero coupling to wave siblings, zero third-party deps.
- **Validation plan.** `pytest tests/test_jarvis_prime_ledger.py` (16 cases) plus `python -m compileall hermes_cli/jarvis_prime/ledger.py`.
- **Risk / rollback.** See sections below.

## Tests run

```
uv run --extra dev pytest tests/test_jarvis_prime_ledger.py
=> 16 passed in 1.23s

uv run --extra dev python -m compileall hermes_cli/jarvis_prime/ledger.py
=> Compiling 'hermes_cli/jarvis_prime/ledger.py'... (exit 0)
```

Coverage matrix (passing):

| Behavior | Test |
|----------|------|
| Append + read round-trip; auto-stamp `ts` | `test_append_then_read_roundtrips_and_auto_stamps_ts` |
| Caller-supplied `ts` preserved | `test_append_preserves_caller_supplied_ts` |
| Missing parent dirs created | `test_append_creates_missing_parent_directories` |
| Non-dict event raises `TypeError` | `test_append_rejects_non_dict_event` |
| Newlines in strings round-trip safely | `test_append_escapes_embedded_newlines_in_string_values` |
| Missing file → empty result | `test_read_missing_file_returns_empty_result` |
| Append order preserved | `test_read_returns_records_in_append_order` |
| Blank lines skipped | `test_read_skips_blank_lines` |
| Non-JSON line reported as corrupt | `test_read_reports_non_json_line_as_corrupt` |
| JSON non-dict reported as corrupt | `test_read_reports_non_dict_json_as_corrupt` |
| Records around corruption preserved | `test_read_preserves_records_around_corruption` |
| `tail` returns last n in order; n=0/n>len edge cases | `test_tail_returns_last_n_records_in_order` |
| Negative `tail` rejected | `test_tail_rejects_negative_n` |
| `filter_by_type` matches `type` field only | `test_filter_by_type_returns_only_matching_records` |
| Static guard: no `events` / `job_store` import | `test_ledger_module_does_not_import_events` |
| Every appended line is standalone-valid JSON | `test_appended_lines_are_valid_json_per_line` |

Tests use `tempfile.TemporaryDirectory()` directly (per the wave's acceptance criterion) via a small fixture; no third-party deps; no network.

## Remaining risks

- **Multi-process appenders.** Single-process `open("a")` writes ≤ PIPE_BUF bytes are atomic on POSIX. Concurrent multi-process append from many writers (especially on Windows) is *not* addressed here. Mitigation: read-side corruption tolerance keeps the ledger usable even if a partial line slips in; a future wave can add file locking or rotation if needed.
- **No `fsync`.** A crash between `write` and OS flush could truncate the last line. Read-side tolerance handles this; full durability is deferred.
- **No rotation / size cap.** The ledger grows unbounded. Acceptable for a decision ledger (sparse events) but worth revisiting if a high-frequency caller adopts it.
- **Cross-wave coupling.** A future wave adding `events.py` / `job_store.py` to the same subpackage might want to share types. Ledger's API is small and frozen — easy to wrap from those modules without modifying it.

## Rollback plan

```
git checkout claude/adoring-volta-KueMP
git branch -D aci/wave-08-decision-ledger
rm -rf hermes_cli/jarvis_prime
rm  tests/test_jarvis_prime_ledger.py
rm  docs/aci/reports/W08_DECISION_LEDGER.md
rmdir docs/aci/reports docs/aci   # only if empty
```

No live system, network, deployment, secret, or shared-state impact to undo. Draft PR can simply be closed.

## PR summary (for draft PR body)

Wave 08 (`/builder`): adds `hermes_cli/jarvis_prime/ledger.py`, a stdlib-only append-only JSONL decision-ledger helper plus its package `__init__.py`, with 16 pytest cases. Independent of sibling files owned by other waves; no third-party deps. Draft only — do not merge.

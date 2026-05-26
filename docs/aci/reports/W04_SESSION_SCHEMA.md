# Wave 04 — JARVIS Prime Session Schema

## Mission

JARVIS Prime (see `docs/jarvis-prime-operating-system.md`) is reachable from
CLI, Slack, Termux, Android, the gateway, and voice. A single logical session
must carry the active job, the last mode, and ambient metadata between those
surfaces so a voice conversation can resume in Slack or Termux without losing
context.

This wave installs the data model only. It is the foundation for the
gateway adapters, persistence, and surface wiring that later waves will land.
No gateway code, no Android code, no storage layer is touched.

## Changed Files

- `hermes_cli/jarvis_prime/__init__.py` (new) — package marker; re-exports
  the four public names with `__all__`.
- `hermes_cli/jarvis_prime/session.py` (new) — stdlib-only schema:
  `Surface` enum, `Session` dataclass, `derive_session_id`, `is_valid_session_id`.
- `tests/test_jarvis_prime_session.py` (new) — 24 pytest cases across five
  test classes.
- `docs/aci/reports/W04_SESSION_SCHEMA.md` (this file).

No other files in the repository are modified. `gateway/`, `apps/android/`,
`pyproject.toml`, `uv.lock`, and `README.md` are untouched.

## Schema Summary

| Field           | Type                  | Required | Notes                                                  |
| --------------- | --------------------- | -------- | ------------------------------------------------------ |
| `surface`       | str (Surface enum)    | yes      | one of: cli, slack, termux, android, gateway, voice    |
| `session_id`    | str (UUID)            | derived  | auto-derived via UUID5 if empty; validated if provided |
| `user_id`       | Optional[str]         | no       | None for anonymous sessions                            |
| `active_job_id` | Optional[str]         | no       | nullable handle to the in-flight job                   |
| `last_mode`     | str                   | no       | free-form (e.g. "builder", "reviewer")                 |
| `created_at`    | datetime (UTC)        | derived  | defaults to `datetime.now(timezone.utc)`               |
| `updated_at`    | datetime (UTC)        | derived  | defaults to `datetime.now(timezone.utc)`               |
| `metadata`      | dict[str, Any]        | no       | shallow-copied on serialize; JSON-encodable values     |

Naive datetimes are silently coerced to UTC so deterministic id derivation
stays stable across callers.

## Public API

- `Surface` — `str` enum with the six allowed surface values.
- `derive_session_id(surface, user_id, created_at)` — deterministic UUID5
  over `uuid.NAMESPACE_DNS` with the seed
  `"jarvis-prime|{surface}|{user_id or ''}|{iso_utc(created_at)}"`.
- `is_valid_session_id(value)` — permissive predicate; returns False for
  non-strings, empty strings, and unparseable UUIDs.
- `Session` dataclass with `to_dict()` / `from_dict()` / `to_json()` /
  `from_json()` / `touch()`.

## Tests Run

```text
python -m compileall hermes_cli/jarvis_prime/session.py hermes_cli/jarvis_prime/__init__.py
pytest tests/test_jarvis_prime_session.py -v
```

Result: **24 passed in 2.69s**. Coverage spans:

- Surface enum exhaustiveness
- Determinism (same inputs → same id)
- Surface discrimination (different surfaces → different ids)
- User discrimination (different users → different ids)
- Construction validation (invalid surface / invalid session_id → ValueError)
- Naive-datetime coercion to UTC
- `to_dict` / `from_dict` round trip
- `to_json` / `from_json` round trip
- **Mobile surfaces** (`termux`, `android`, `voice`) round trip — acceptance criterion
- Nested metadata round trip
- Forward-compat: `from_dict` silently ignores unknown keys
- Defensive: `from_dict` rejects non-dict metadata, missing surface
- `touch()` advances `updated_at` without mutating `session_id`

## Remaining Risks

- **No persistence layer yet.** Sessions live in memory only; nothing
  writes them to disk or to the gateway store. That arrives in a later wave.
- **No gateway wiring yet.** Surface adapters (CLI, Slack, Termux, Android,
  voice) don't yet read or write `Session` objects. Schema is the contract;
  callers come next.
- **Anonymous-session collision corner case.** Two `user_id=None` sessions
  on the same surface created in the same microsecond derive the same
  `session_id`. Acceptable for a single-user JARVIS environment; the fix
  (per-process salt or caller-supplied nonce) lands when the multi-tenant
  gateway path is wired up.
- **No backward-compat baggage.** `from_dict` silently ignores unknown keys
  so future field additions don't break older readers, but there is no
  schema-version field yet. If the schema ever needs an incompatible
  change, a versioning shim will need to be introduced.

## Rollback Plan

This wave is purely additive — nothing imports the new package yet. To
roll back:

```bash
git rm -r hermes_cli/jarvis_prime/
git rm tests/test_jarvis_prime_session.py
git rm -r docs/aci/reports/
```

(or `git revert` the wave commit). No call sites need updating because
no production code yet imports `hermes_cli.jarvis_prime`.

## PR Summary

Wave 04 lands the JARVIS Prime cross-surface session schema as a
stdlib-only `hermes_cli.jarvis_prime` package. The `Session` dataclass
captures surface (CLI / Slack / Termux / Android / gateway / voice),
user, active job, last mode, timestamps, and metadata, with a
deterministic UUID5 session-id derivation and lossless dict/json
serialization. Twenty-four pytest cases cover round trips on the
mobile surfaces and the determinism / validation guarantees. No
gateway, Android, or storage code is touched — this wave is the
contract that later waves will adapt to.

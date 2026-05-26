# Wave 08 — Event Types

**Branch:** `aci/wave-08-event-types`
**Status:** Draft PR (no merge to main)
**Builder mode:** `/builder`

## Mission

Introduce the canonical event envelope used by JARVIS Prime modes,
orchestration workers, gates, owner-approval flows, and notification
surfaces. This is plumbing — no behavior change to the running agent;
later waves will write against the model defined here.

## Changed files

| Path                                        | Kind     | LOC |
| ------------------------------------------- | -------- | --- |
| `hermes_cli/jarvis_prime/__init__.py`       | new      | 9   |
| `hermes_cli/jarvis_prime/events.py`         | new      | 318 |
| `tests/test_jarvis_prime_events.py`         | new      | 386 |
| `docs/aci/reports/W08_EVENT_TYPES.md`       | new      | (this file) |

No files outside the ALLOWED FILES list were touched. The wave did
**not** modify `pyproject.toml`, `uv.lock`, `README.md`, `gateway/**`,
or `apps/android/**`. No new runtime dependency was added —
`StrEnum` and `dataclass(frozen=True, slots=True)` are stdlib in
Python 3.11+.

`docs/aci/` and `docs/aci/reports/` were created by this wave;
neither existed before. `hermes_cli/jarvis_prime/` was likewise
created — it has no overlap with the user-facing
`skills/jarvis-prime/SKILL.md` (different layer, different path).

## Event model

`hermes_cli.jarvis_prime.events.Event` is a frozen, slots-enabled
dataclass with five required fields plus an audit trail:

| Field        | Type              | Notes                              |
| ------------ | ----------------- | ---------------------------------- |
| `event_id`   | `str`             | uuid4 hex (32 chars) by default    |
| `type`       | `str`             | validated against `EventType`      |
| `timestamp`  | `str`             | ISO-8601 UTC, parsed at construct  |
| `source`     | `str`             | free-form (`jarvis.cli`, etc.)     |
| `payload`    | `dict[str, Any]`  | JSON-safe + secret-scrubbed        |
| `redactions` | `tuple[str, ...]` | dotted paths of scrubbed fields    |

`EventType` (a `StrEnum`) covers every name in the Wave 08 spec:

```
message.received       mode.classified       route.selected
memory.recalled        task.created          worker.started
worker.finished        gate.failed           owner.approval.required
test.finished          pr.created            notification.sent
memory.saved
```

### JSON safety

`_make_json_safe` is run on every payload at emit time and again
at `from_dict` time so untrusted input cannot smuggle non-serializable
values:

- Allowed leaves: `str`, `int`, `bool`, `None`, finite `float`.
- Auto-converted: `datetime`/`date` → ISO string, `UUID`/`Path` →
  `str`, `Enum` → its `value`, `set`/`frozenset`/`tuple` → `list`.
- Reject: `NaN`/`Inf`, non-`str` dict keys, anything else
  (raises `ValueError` naming the dotted path).

### Secret hygiene

`_redact_secrets` walks the JSON-safe payload and replaces any value
flagged by either trigger with the literal `"[REDACTED]"`:

1. **Key-name match** — case-insensitive, mirrors the credential
   suffix list in `tests/conftest.py:48-93` (`_API_KEY`, `_TOKEN`,
   `_SECRET`, `_PASSWORD`, `_CREDENTIALS`, `_ACCESS_KEY`,
   `_PRIVATE_KEY`, `_OAUTH_TOKEN`, `_WEBHOOK_SECRET`, etc.) plus the
   standalone names `password`, `token`, `api_key`, `authorization`,
   `bearer`, `client_secret`, …
2. **Value-shape match** — `sk-…`, `sk-ant-…`, `gh[pousr]_…`,
   `AKIA…`, `ASIA…`, `xox[baprs]-…`, JWTs, `Bearer …`, and PEM
   `-----BEGIN … PRIVATE KEY-----` headers.
3. **High-entropy fallback** — strings matching
   `^[A-Za-z0-9+/=_-]{40,}$` are redacted *unless* the surrounding
   key is on a small allowlist (`event_id`, `sha`, `commit_sha`,
   `hash`, `content_hash`, `digest`, `checksum`, `etag`, `id`,
   `uuid`, `trace_id`, `span_id`, `request_id`, `correlation_id`).

The list of redacted dotted paths is surfaced as the immutable
`redactions` tuple on the event, so downstream consumers can audit
hygiene without seeing values.

## Tests run

`scripts/run_tests.sh` was unavailable in this remote environment
(no shipped venv), so the equivalent invocation was used:

```
.venv/bin/python -m pytest tests/test_jarvis_prime_events.py -v
```

Result: **79 passed in 2.75s** across 4 xdist workers, with
`TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0` (matching the conftest's
hermetic-test invariants).

Coverage highlights:

- Parametrized round-trip across every event type (`to_dict` / `to_json` → `from_dict` returns an equal event).
- `EventType` matches the spec exactly (no drift).
- All five required fields are validated at construct and at deserialize time.
- `NaN`, `Inf`, `complex`, `bytes`, `object()`, lambdas in the payload all raise.
- Eleven secret-shaped values and twelve secret-named keys are scrubbed; their paths appear in `redactions`.
- Allowlisted high-entropy keys (`commit_sha`, `sha`, `content_hash`, `event_id`, `trace_id`) are preserved.
- `to_json` produces deterministic, sorted-key output.
- `Event` is frozen and `payload` is a defensive copy (input mutation cannot leak in).

A standalone smoke check was also run:

```
$ python -c "from hermes_cli.jarvis_prime import Event, EventType; \
           e = Event.new(EventType.MESSAGE_RECEIVED, 'jarvis.cli', \
                         {'text': 'hi', 'api_key': 'sk-xxxxxxxxxxxxxxxxxxxxxxxx'}); \
           print(e.to_json()); print('redactions:', e.redactions)"
json: {"event_id": "...", "payload": {"api_key": "[REDACTED]", "text": "hi"},
       "redactions": ["api_key"], "source": "jarvis.cli",
       "timestamp": "2026-05-26T...+00:00", "type": "message.received"}
redactions: ('api_key',)
```

`python -m compileall hermes_cli/jarvis_prime/events.py` passes
without errors.

## Remaining risks

- **Heuristic redaction is best-effort.** A short or non-pattern-matching secret (e.g. a 12-char shared API key with no prefix) placed under an innocent-looking key name can still slip through. Mitigation: combine key-name + value-shape detection, and prefer hygiene at emit sites in later waves (callers should put credential-like values under credential-named keys when in doubt).
- **High-entropy false positives.** Long opaque IDs not on the allowlist will be redacted. The allowlist is intentionally small (audit-log–style names) — when later waves discover new safe names, they should extend `_REDACTION_ALLOWLIST_KEYS` in `events.py` (and add a regression test).
- **Determinism contract.** `to_json` sorted-key output is part of the public API (downstream consumers will hash it for audit trails). The test `test_to_json_uses_sorted_top_level_keys` pins this; future refactors must preserve it.
- **No emit wiring yet.** This wave is the model only. Until later waves call `Event.new(...)` from real code paths, the envelope is unused.
- **Required dev tooling.** `pytest`, `pytest-xdist`, `pytest-timeout`, and `pytest-split` had to be installed into `.venv` to run the suite — this is a property of the remote container, not a code change, and is not committed.

## Required changes spotted outside allowed files

None. The wave is self-contained.

## Rollback plan

Per the task spec:

```
git checkout aci/wave-08-event-types
rm hermes_cli/jarvis_prime/events.py
rm hermes_cli/jarvis_prime/__init__.py
rm tests/test_jarvis_prime_events.py
rm docs/aci/reports/W08_EVENT_TYPES.md
git commit -am "revert: Wave 08 event model"
```

Or simply delete the branch — nothing else in the repo imports
from `hermes_cli.jarvis_prime`, so removal is loss-free.

## PR summary (draft)

> **Wave 08 — Standard event model for JARVIS / Hermes orchestration**
>
> Introduces `hermes_cli.jarvis_prime.events.Event` — a frozen
> dataclass envelope with 13 typed event names, JSON-safe payload
> coercion, and value-shape + key-name secret redaction. Adds 79
> parametrized tests covering every event type, both redaction
> triggers, the high-entropy allowlist, JSON safety, and
> determinism. No runtime wiring — pure model + tests. Draft.
>
> **Acceptance criteria**
> - Event object serializes safely. ✓
> - Required fields: `event_id`, `type`, `timestamp`, `source`, `payload`. ✓
> - Payload must be JSON-safe. ✓
> - Secret-looking values are rejected/redacted. ✓ (key-name + value-shape, with audit trail)
> - Tests cover every event type. ✓ (parametrized over all 13)
>
> **Verify**
> - `pytest tests/test_jarvis_prime_events.py` → 79 passed
> - `python -m compileall hermes_cli/jarvis_prime/events.py` → ok

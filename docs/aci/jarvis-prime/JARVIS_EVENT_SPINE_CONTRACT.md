# Jarvis Prime Event Spine — Contract

Status: v1 (schema version 1). Defined by
`hermes_cli/jarvis_prime/event_spine.py`. Nothing in the runtime imports it
yet — this document and the module together are the contract that
producers (router, gateway, workers, scheduler) and consumers (Android
body, audit log, dashboards) will agree on as they wire in.

## 1. Purpose

The event spine is the single agreed shape for events that move between
the Hermes/Jarvis backend and every consumer surface. Without it, the
router, gateway, audit log, and Android app each invent their own payload
shapes and drift apart at the first incident. With it, every surface
reads the same envelope and can dispatch on a stable set of event types.

Product framing:

- Product-facing name is **Jarvis Prime**.
- Android is the **body / control surface**, not the AI brain.
- The brain (runtime, router, gates, model selection) stays in the
  Hermes backend.
- The event spine carries information from the brain to the body, never
  secrets, and never executable code.

## 2. Event taxonomy

Nineteen canonical event types, grouped by domain. Producers emit; the
Android body and the audit log consume.

### Messaging

| Type | Producer | Consumer |
|---|---|---|
| `jarvis.message.received` | gateway, router | Android body, audit |
| `jarvis.message.responded` | router | Android body, audit |

### Presence

| Type | Producer | Consumer |
|---|---|---|
| `jarvis.presence.changed` | gateway | Android body |

### Tasks

| Type | Producer | Consumer |
|---|---|---|
| `jarvis.task.created` | router, workers | Android body, audit |
| `jarvis.task.phase.changed` | workers | Android body, audit |
| `jarvis.task.blocked` | workers | Android body, audit |
| `jarvis.task.completed` | workers | Android body, audit |

### Workers

| Type | Producer | Consumer |
|---|---|---|
| `jarvis.worker.started` | scheduler | audit |
| `jarvis.worker.finished` | scheduler | audit |

### Approvals

| Type | Producer | Consumer |
|---|---|---|
| `jarvis.approval.requested` | gates | Android body, audit |
| `jarvis.approval.granted` | gates | audit |
| `jarvis.approval.denied` | gates | audit |

### Memory

| Type | Producer | Consumer |
|---|---|---|
| `jarvis.memory.created` | memory layer | audit |
| `jarvis.memory.updated` | memory layer | audit |

### Proof

| Type | Producer | Consumer |
|---|---|---|
| `jarvis.proof.created` | verification gates | audit |

### Notification

| Type | Producer | Consumer |
|---|---|---|
| `jarvis.notification.requested` | router | Android body |

### Safety

| Type | Producer | Consumer |
|---|---|---|
| `jarvis.emergency_stop.triggered` | gates, operator | Android body, audit |

### Gateway

| Type | Producer | Consumer |
|---|---|---|
| `jarvis.gateway.connected` | gateway | Android body, audit |
| `jarvis.gateway.disconnected` | gateway | Android body, audit |

## 3. Event envelope schema

Every event is a JSON object with these fields:

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | UUIDv4 hex, 32 chars, no dashes |
| `type` | string | yes | One of the 19 values above |
| `ts` | string | yes | UTC `YYYY-MM-DDTHH:MM:SS.ffffffZ` |
| `source` | string | yes | Producer id: `router`, `gateway`, `worker:<id>` |
| `actor` | string\|null | no | Who triggered: `user`, `system`, `worker:<id>` |
| `subject` | string\|null | no | Domain id (task id, message id, approval id, memory id) — recommended for indexing |
| `correlation_id` | string\|null | no | Conversation / run thread id |
| `schema_version` | int | yes | Currently `1` |
| `payload` | object | yes | JSON-safe dict, validated, secret-free |

The dataclass `Event` is frozen. The `payload` dict is stored plain;
treat it as immutable after construction. Use `dataclasses.replace` for
the rare reshape case.

## 4. Per-type payload conventions

Recommended (non-binding in v1) payload keys, mirroring what the
`render_mobile()` hint extractor reads. Producers are free to add
additional keys; consumers must ignore unknown keys.

| Type | Recommended payload keys |
|---|---|
| `jarvis.message.received` | `preview` (str, short) |
| `jarvis.message.responded` | `preview` |
| `jarvis.presence.changed` | `state` (`online` / `away` / `offline`) |
| `jarvis.task.created` | `title`, `phase` |
| `jarvis.task.phase.changed` | `title`, `phase` |
| `jarvis.task.blocked` | `reason` |
| `jarvis.task.completed` | `title` |
| `jarvis.worker.started` | `worker` (id) |
| `jarvis.worker.finished` | `worker`, `duration_ms` (int) |
| `jarvis.approval.requested` | `summary` |
| `jarvis.approval.granted` | `decision`, `summary?` |
| `jarvis.approval.denied` | `decision`, `summary?` |
| `jarvis.memory.created` | `title` or `key` |
| `jarvis.memory.updated` | `title` or `key` |
| `jarvis.proof.created` | `kind`, `title?` |
| `jarvis.notification.requested` | `text` |
| `jarvis.emergency_stop.triggered` | `reason` |
| `jarvis.gateway.connected` | `gateway` (id or URL) |
| `jarvis.gateway.disconnected` | `gateway` |

## 5. JSON-safety and secret policy

`validate_payload(payload)` is the producer-side gate. It accepts only
JSON-native Python types:

- `str`, `int`, finite `float`, `bool`, `None`
- `list` / `tuple` (tuples are normalized to lists)
- nested `dict` with `str` keys

It rejects (raising `InvalidPayloadError`) any of:

- `bytes`, `set`, `datetime`, custom classes
- `NaN`, `+/-inf`
- non-string dict keys
- payloads whose JSON encoding exceeds `MAX_PAYLOAD_BYTES` (16 KB)

Error messages include the key path (`payload.foo.bar[3]`).

**Secrets are rejected, not silently redacted.** The contract holds at
the producer boundary — producers must scrub their data first. The
scanner trips on either:

1. **Key-name match** (case-insensitive substring) on any of:
   `token`, `api_key`, `apikey`, `password`, `passwd`, `secret`,
   `bearer`, `authorization`, `auth`, `session_key`, `private_key`,
   `client_secret`, `refresh_token`, `access_token`.

2. **Value-pattern match** for known token shapes:
   - `sk-…` (16+ chars) — OpenAI-style
   - `Bearer …` (16+ chars) — HTTP auth headers
   - `ghp_…` (30+ chars), `github_pat_…` (20+ chars) — GitHub PATs
   - `AKIA…` (16 uppercase) — AWS access key id
   - `xox[abposr]-…` (10+ chars) — Slack tokens

A hit raises `SecretInPayloadError(key_path)`. The exception message
names the key path but never includes the matched value.

A separate helper, `redact_payload(payload)`, returns a deep-copied
dict where matches are replaced by `[REDACTED]`. It is intended for
audit-side tooling that ingests already-validated events; it is **not**
in the validation path. Producers should not rely on it as a safety
net.

## 6. Wire format

- **On disk:** UTF-8 JSONL. One event per line. Each line is
  `event.to_json()` followed by `\n`. `to_json` uses
  `sort_keys=True, separators=(",", ":")` so two equivalent events
  produce identical bytes (deterministic hashing, easier diffing).
- **Over the gateway:** the same JSON object per message. The wave
  that wires the gateway is responsible for framing (length-prefix or
  newline-delimited).
- **Empty lines** in JSONL files are skipped on read.

## 7. Android / mobile gateway integration

Android is the body — events flow **in** to it; the AI runtime stays in
Hermes backend. The mobile gateway streams events as they happen; the
Android body subscribes and dispatches by `type` and (optionally)
`subject`.

### Compact renderer

`render_mobile(event)` produces a single-line, ≤120-char string suitable
for a notification body or status row:

```
[HH:MM:SS short.type] subject — hint
```

- `short.type` is the event type with `jarvis.` removed.
- `subject` is the event's `subject` field if set.
- `hint` is a per-type extractor (see §4). Unknown types render with
  empty hint.
- Control characters are stripped; the line is truncated with `…` at
  120 characters.

### Notification mapping recommendations

| Event | Default mobile treatment |
|---|---|
| `jarvis.message.received` | inline preview, no sound |
| `jarvis.notification.requested` | push if foregrounded by router |
| `jarvis.approval.requested` | high-priority notification with action |
| `jarvis.emergency_stop.triggered` | critical/alarm priority |
| `jarvis.task.blocked` | warning priority |
| `jarvis.gateway.disconnected` | passive status badge |
| everything else | log-only / dashboard-only |

### Permissions posture (binding rules)

- No automatic notification permission prompt on first launch.
- Microphone permission only after the user taps voice.
- Optional permissions are optional; the body must still work if denied.
- No SMS, Call Log, or always-listening behavior.
- Python runtime is **never** embedded in the APK.
- Gateway-side secrets are **never** stored in Android.

## 8. Producer cookbook

```python
from hermes_cli.jarvis_prime.event_spine import (
    EventType,
    append_jsonl,
    new_event,
)

event = new_event(
    EventType.TASK_BLOCKED,
    source="worker:codex-1",
    actor="system",
    subject="task-1729",
    correlation_id="run-abc",
    payload={"reason": "needs owner approval"},
)

append_jsonl("~/.hermes/spine/2026-05-26.jsonl", event)
```

`new_event` fills in `id` and `ts`; pass `EventType` or its string
value. The constructor and the `Event.__post_init__` chain run
validation immediately — bad inputs raise at the point of emission.

## 9. Consumer cookbook

```python
from hermes_cli.jarvis_prime.event_spine import (
    EventType,
    Event,
    read_jsonl,
    render_mobile,
)

for event in read_jsonl("/path/to/spine.jsonl"):
    if event.type == EventType.APPROVAL_REQUESTED.value:
        push_to_android(render_mobile(event), action="approve_or_deny")
    elif event.type == EventType.EMERGENCY_STOP_TRIGGERED.value:
        page_owner(event)
```

`read_jsonl` is a generator — memory stays bounded over long audit
files. Each yielded `Event` has already been re-validated against the
contract.

## 10. Versioning and forward-compat

`SCHEMA_VERSION` is currently `1`. Adding new event types, renaming
existing ones, or restructuring the envelope is a breaking change and
requires bumping the version.

Forward-compat policy: **strict**. `Event.from_dict` raises
`EventSpineError` when it sees a `schema_version` greater than the
running module's `SCHEMA_VERSION`. Consumers cannot silently drop
fields they don't understand — they must upgrade in lockstep.

Adding new optional fields to the envelope or new payload keys does
**not** require a version bump; consumers are required to ignore
unknown keys.

## 11. Non-goals (v1)

- No multi-process JSONL safety. `append_jsonl` is single-writer per
  file; concurrent writers may interleave on lines larger than POSIX
  `PIPE_BUF` (~4 KB).
- No encryption-at-rest. Treat JSONL files as sensitive operational
  data, not a secrets store.
- No signed events. Tamper-evidence will come from a later wave (HMAC
  per line, or signed log batches).
- No broker. There is no pub/sub here; this is a contract, not a
  transport.
- No high-entropy heuristic secret detection. Regex patterns + key
  names only. False-positives on UUIDs and base64 thumbnails would
  drive producers to redact too aggressively.

## 12. Decisions recorded (v1)

| # | Decision | Choice | Why |
|---|---|---|---|
| D1 | Secret policy | reject at producer | surfaces producer bugs early |
| D2 | Timestamp | ISO-8601 UTC microseconds, `…Z` | sorts lexically, human-readable on Android |
| D3 | ID format | `uuid4().hex` (32 chars) | compact, JSON-safe, no dashes for mobile UI |
| D4 | JSONL locking | none | portable to Termux/Windows; documented single-writer contract |
| D5 | Payload mutability | plain dict, "treat as immutable" | minimal API, no surprising wrapper types |
| D6 | Forward-compat | strict on `schema_version` | drift surfaces immediately |
| D7 | Entropy heuristic | off | too noisy without context; revisit later |
| D8 | `render_mobile` cap | 120 chars | practical Android notification body cap |

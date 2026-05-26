# W04 — Jarvis Prime Event Spine Contract

**Branch:** `aci/jarvis-prime-04-event-spine-contract`
**PR title:** `W04: Add Jarvis Prime Event Spine contract`
**Status:** draft — do not merge to `main`.

## Wave goal

Define the on-the-wire and on-disk shape of every event that Jarvis Prime
producers (router, gateway, workers, scheduler) emit and every consumer
(Android body, audit log, dashboards) reads. The spine is the single
agreed contract that prevents the Android surface, the gateway, and the
audit log from drifting apart at the first real incident. This wave
ships the contract as runtime code only — no producers or consumers are
wired to it yet.

## Scope delivered

Four new files, zero modified files.

- `hermes_cli/jarvis_prime/event_spine.py` — stdlib-only module: 19
  canonical event types (`EventType` + `EVENT_TYPES`), a frozen `Event`
  dataclass, JSON-safe payload validation, secret rejection at the
  producer boundary, `redact_payload` helper for audit tooling,
  `to_dict` / `from_dict` / `to_json` / `from_json`, `render_mobile`
  compact renderer, and `append_jsonl` / `read_jsonl` helpers.
- `tests/test_jarvis_prime_event_spine.py` — 86 pytest cases covering
  every event type, every public function, validation positives and
  negatives, secret detection (keys + values), redaction semantics,
  `from_dict` strictness, JSON determinism, JSONL round-trip, mobile
  renderer behavior, frozen-dataclass invariants, stdlib-only AST guard,
  and the namespace-package import assumption.
- `docs/aci/jarvis-prime/JARVIS_EVENT_SPINE_CONTRACT.md` — the contract
  spec: taxonomy, envelope, per-type payload conventions, secret policy,
  wire format, Android integration guide with permissions posture,
  producer and consumer cookbooks, versioning policy, and recorded
  decisions.
- `docs/aci/reports/W04_EVENT_SPINE_REPORT.md` — this file.

## Out of scope

- `hermes_cli/jarvis_prime/__init__.py` — not in ALLOWED FILES. Imports
  rely on PEP 420 namespace-subpackage semantics inside the regular
  `hermes_cli` package (verified by an explicit
  `importlib.import_module` test).
- Wiring producers (router, gateway, workers, scheduler).
- Wiring consumers (Android body, audit log).
- Any Android changes (`apps/android/**`).
- `hermes_cli/jarvis_prime/runtime.py`, `router.py`, `gates.py`,
  `hermes_cli/model_router.py`, `docs/ai-intelligence/model-registry.yaml`.
- `skills/`, `README.md`, `pyproject.toml`, `uv.lock`, `.github/`.
- Any HTTP, gateway, or broker transport — this is the data contract
  only.

## Decisions taken

| # | Decision | Choice | Rationale |
|---|---|---|---|
| D1 | Secret policy | **reject** at `validate_payload`; `redact_payload` is a separate helper | producers must scrub; surfaces bugs early |
| D2 | Timestamp | ISO-8601 UTC microseconds, `…Z` suffix | sorts lexically, human-readable on Android |
| D3 | ID | `uuid.uuid4().hex` (32 chars, no dashes) | compact, JSON-safe |
| D4 | JSONL locking | **none** — single-writer-per-file contract | portable to Termux/Windows |
| D5 | Payload mutability | plain `dict`, treated as immutable | minimal API surface |
| D6 | Forward-compat | **strict** — `from_dict` raises on newer `schema_version` | drift surfaces immediately |
| D7 | Entropy heuristic | off in v1 | regex + key-name only; revisit later |
| D8 | `render_mobile` cap | 120 chars | practical Android notification body cap |

## Test summary

```
$ .venv/bin/python -m pytest tests/test_jarvis_prime_event_spine.py -o addopts=""
============================== 86 passed in 1.16s ==============================
```

Test categories:

- Enum surface (count + literal-equality vs the spec set)
- Per-event-type construction (parametrized over all 19 types)
- Validation positives (nested JSON-native types, tuple→list)
- Validation negatives (`bytes`, `set`, `datetime`, custom class, NaN,
  Inf, non-string key, oversize, non-dict root)
- Secret rejection (18 trigger keys + 7 value patterns; messages never
  include the matched value)
- `redact_payload` (replaces, deep-copies, does not mutate input)
- `from_dict` strictness (unknown keys, missing required fields,
  unknown type, newer `schema_version`, bad JSON)
- JSON determinism (insertion-order-independent bytes)
- JSONL round-trip (every event type written and read back; empty lines
  skipped)
- `render_mobile` (prefix stripped, subject included, control chars
  removed, 120-char truncation, worker-finished duration)
- Frozen-dataclass invariant (`FrozenInstanceError` on field set)
- Stdlib-only AST guard (every imported top-level module is in
  `sys.stdlib_module_names`)
- Namespace-package import smoke (`importlib.import_module` succeeds)

## Known limitations

- **JSONL single-writer** — concurrent producers against the same file
  may interleave on lines larger than POSIX `PIPE_BUF` (~4 KB).
  Documented in the module and the contract doc.
- **No entropy heuristic** — base64 / hex strings that don't match the
  known patterns and aren't under a secret-looking key will pass.
  Producers own that decision.
- **Strict schema versioning** — consumers cannot read events from a
  newer producer. Intentional: drift must surface immediately.
- **Module not yet wired** — nothing in the runtime imports it. That's
  the point of this wave; later waves add producers and consumers.

## Collision report

A pre-implementation scan of open PRs found five sibling waves that
each introduce **`hermes_cli/jarvis_prime/__init__.py`** with different
content:

- PR #11 (`aci/wave-08-decision-ledger`) — `ledger.py` re-exports
- PR #13 (`aci/wave-05-verification-packet`) — `verification.py` re-exports
- PR #15 (`aci/wave-05-review-packet-schema`) — `review_packets.py` re-exports
- PR #16 (`claude/awesome-goldberg-zrzaA`) — `specialists.py` re-exports
- PR #17 (`claude/hopeful-goodall-yvKgC`) — `surfaces.py` re-exports

None of those PRs touch `event_spine.py`, the tests file, or either
docs file in this wave's ALLOWED list. **This wave's diff therefore
does not collide.** The merge order will determine which sibling's
`__init__.py` wins on disk; whichever it is, this wave's
`event_spine.py` is importable through PEP 420 namespace-subpackage
semantics regardless of whether an `__init__.py` exists, so this
contract module is robust to all five outcomes.

When a future wave consolidates `__init__.py` (or when this directory's
ownership is decided), `event_spine` should be added to that file's
re-exports.

## Next waves

- **Producers:** wire the router, gateway, and worker scheduler to emit
  via `new_event(...)` and stream over the gateway / append to the
  local JSONL audit file.
- **Consumers:** wire the Android body's notification bridge to
  `render_mobile(event)` and event-type dispatch.
- **Audit log:** standardize on `~/.hermes/spine/<date>.jsonl` (or
  per-source sharding for multi-writer scenarios) and ship a small
  reader/dashboard.
- **Signing (later):** add HMAC-per-line or signed batches for
  tamper-evident audit.

## Verification commands

```
.venv/bin/python -m pytest tests/test_jarvis_prime_event_spine.py -o addopts=""
.venv/bin/python -m compileall hermes_cli/jarvis_prime/event_spine.py
.venv/bin/python -c "import hermes_cli.jarvis_prime.event_spine as m; assert len(m.EVENT_TYPES) == 19"
git diff --stat origin/main
git diff --name-only origin/main | grep -vE '^(hermes_cli/jarvis_prime/event_spine\.py|tests/test_jarvis_prime_event_spine\.py|docs/aci/jarvis-prime/JARVIS_EVENT_SPINE_CONTRACT\.md|docs/aci/reports/W04_EVENT_SPINE_REPORT\.md)$'
grep -rn "from hermes_cli.jarvis_prime\|import hermes_cli.jarvis_prime" hermes_cli/ gateway/ tui_gateway/
```

Expected:

- 86 passed
- `compileall` returns 0
- The smoke import prints nothing (assertion passes silently)
- `git diff --stat` shows exactly four new files
- The grep for out-of-scope diffs returns empty
- The grep for runtime wiring returns empty

## Rollback

No existing files were modified. To roll back:

```
git checkout main
git branch -D aci/jarvis-prime-04-event-spine-contract
```

If pushed:

```
git push origin --delete aci/jarvis-prime-04-event-spine-contract
```

Then close the draft PR. No production state, no migrations, no
dependencies, no external services touched.

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| PEP 420 import breaks if a sibling `__init__.py` ships broken | low | dedicated namespace-package import test in the suite catches it at PR-build time |
| Regex false-positives flag benign strings | low | patterns require minimum length 16; producers can pre-redact when they own the string |
| JSONL interleaving under concurrent writers | medium | single-writer contract documented; a later wave can layer a writer with locks |
| Strict schema versioning blocks consumer drift | by design | this is the point; bumps must land producer-then-consumer |
| Frozen-dataclass escape via payload `dict` mutation | low | documented invariant; consider `MappingProxyType` in a future version |

## PR summary

```
W04: Add Jarvis Prime Event Spine contract

Stdlib-only contract module defining the 19 Jarvis Prime event types,
a frozen Event dataclass with JSON-safe payload validation, producer-side
secret rejection, deterministic JSONL on-disk format, and a compact mobile
renderer. Nothing wires it yet — subsequent waves will plug producers
(router/gateway/workers) and consumers (Android body, audit log).

Files: 4 new, 0 modified. Tests: 86 passed. Draft only.
```

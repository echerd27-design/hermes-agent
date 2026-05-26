# Wave 03 — JARVIS Prime Memory Contract

**Branch:** `aci/wave-03-memory-contract`
**Status:** draft PR; do not merge
**Mission:** Audit and harden JARVIS Prime memory behavior without changing global Hermes memory architecture.

## Wave summary

| Item | Value |
| --- | --- |
| Allowed files | `hermes_cli/jarvis_prime/memory.py`, `tests/test_jarvis_prime_memory_contract.py`, `docs/aci/reports/W03_MEMORY_CONTRACT.md` |
| Forbidden files | `pyproject.toml`, `plugins/memory/__init__.py`, anything else |
| Branch | `aci/wave-03-memory-contract` |
| New package layout | `hermes_cli/jarvis_prime/` resolves as a **PEP 420 namespace package** — the parent `hermes_cli/` is a regular package, the child directory has no `__init__.py`, and the contract file is the only resident. Adding an `__init__.py` is out of scope. |
| Persistence introduced | none |

## Storage path & limits

The new module is a **pure in-process policy-enforcement contract layer**. It holds two ordered lists on a `JarvisMemory` instance — `_durable` and `_session` — and persists nothing across processes.

Durable persistence in this repository is already owned by the **plugin provider system** at `plugins/memory/` (Honcho, Mem0, Supermemory, RetainDB, Hindsight, and any user-installed providers under `$HERMES_HOME/plugins/`). A single active provider is selected via `memory.provider` in `config.yaml`; discovery and loading live in `plugins/memory/__init__.py` (408 lines) and the interactive setup wizard at `hermes_cli/memory_setup.py` (465 lines).

The mission explicitly forbids changing that architecture. This contract therefore sits in front of (and is decoupled from) the provider system. It is a *front door* that enforces the policy in `docs/memory-and-personality-policy.md` before anything reaches a downstream persistence layer.

Concrete limits of this wave:

- No disk I/O, no environment reads, no network.
- No cross-process sharing — each `JarvisMemory()` instance is isolated.
- No thread-safety guarantees; callers must serialize access if needed.
- No wiring to `plugins/memory` (out of scope; future wave).

## What is enforced

| Rule (policy source: `docs/memory-and-personality-policy.md`) | Durable surface | Session surface | `summarize_for_prompt` |
| --- | --- | --- | --- |
| Secret-shaped values (tokens, API keys, passwords, OAuth, Bearer headers, high-entropy strings) | **raises `MemoryRejected`** | accepts but **redacts silently** via `redact()` | final `redact()` pass on every line (defence in depth) |
| Stale artifacts (`PR #N`, `issue #N`, `fixes #N`, hex SHAs 7-40 chars) | **raises `MemoryRejected`** | accepts unchanged (policy doc: "session, PR handoff, or task notes") | n/a |
| Raw voice dumps (`[voice]` / `[raw_voice]` / `[voice_dump]` prefix) | **raises `MemoryRejected`** | accepts unchanged | n/a |
| Empty key or empty value | `ValueError` | `ValueError` | n/a |
| Output bound | n/a | n/a | result length always `<= max_chars`; durable entries are emitted before session entries |
| `clear_session()` | leaves durable untouched | wipes all session entries | n/a |

The durable surface is split by category so callers cannot accidentally label task progress as a durable decision:

- `remember_decision(key, value)` — project direction
- `remember_lesson(key, value, *, repo=...)` — repo-scoped lessons (matches the "lessons from difficult procedures that become skills" policy line)
- `remember_preference(key, value)` — user preferences
- `note_task_progress(key, value)` — session only

## Detection patterns

All patterns are module-level compiled regexes (`re.compile(...)`), built once at import time. They mirror the credential suffix list in `tests/conftest.py:60-141` so the contract aligns with the existing hermetic-test invariants.

| Detector | Catches |
| --- | --- |
| `_SECRET_PREFIX_RE` | `sk-…`, `ghp_…`, `gho_…`, `ghu_…`, `ghs_…`, `github_pat_…`, `xox[abprs]-…`, `AKIA[0-9A-Z]{16}`, `AIza…`, `hf_…` |
| `_SECRET_KEYWORD_RE` | `password / passwd / secret / api_key / api-key / apikey / access_token / auth_token / bearer / client_secret / private_key / oauth_token` followed by `:` or `=` and any non-whitespace value (case-insensitive) |
| `_BEARER_RE` | `Bearer <token>` headers |
| `_HIGH_ENTROPY_RE` | 32+ char tokens from `[A-Za-z0-9_\-/+]` that contain **both** at least one letter and at least one digit. The mix requirement prevents long all-lowercase prose phrases from being flagged. |
| `_STALE_PR_ISSUE_RE` | `pr #N`, `issue #N`, `fixes #N`, `closes #N`, `fix #N` (case-insensitive) |
| `_STALE_HASH_NUM_RE` | `#NNN` outside a word |
| `_STALE_SHA_RE` | 7-40 char lowercase hex blob |
| `_VOICE_PREFIX_RE` | leading `[voice]`, `[raw_voice]`, or `[voice_dump]` (case-insensitive) |

## Tests

`tests/test_jarvis_prime_memory_contract.py` — hermetic, sync, no fixtures beyond pytest defaults (the existing `tests/conftest.py` strips credential env vars and isolates `HERMES_HOME` for every test).

| Test class | What it verifies |
| --- | --- |
| `TestDurableVsSession` | durable entries survive `clear_session`; buckets are disjoint; `forget` removes only the named durable entry; same-key re-insertion replaces in place |
| `TestSecretRejection` | parametrized over seven secret shapes — all three durable methods raise `MemoryRejected`; `note_task_progress` stores `[REDACTED]`; `is_secret_like` and `redact` behave as documented; prose is not flagged |
| `TestStaleArtifactRejection` | parametrized over six artifact references — durable methods raise; session accepts unchanged; prose is not flagged |
| `TestRawVoiceRejection` | parametrized over four voice prefixes — durable methods raise; session accepts unchanged |
| `TestSummarizeForPrompt` | empty memory → `""`; output length always `<= max_chars` across 50/200/400/1200 budgets with 50 durable + 50 session entries; durable lines precede session lines; secrets stored through `note_task_progress` are redacted in the summary; `max_chars=0` returns `""`; repo scope appears in the output |
| `TestRepoScopedLessons` | `repo=` is a required kwarg; empty `repo` raises `ValueError`; `repo` is preserved on the entry |
| `TestInputValidation` | empty key or value raises `ValueError` across all surfaces; `__all__` exposes the documented public surface |

## Verification commands

These are the exact commands from the wave prompt's VERIFY block:

```bash
pytest tests/test_jarvis_prime_memory_contract.py
python -m compileall hermes_cli/jarvis_prime/memory.py
```

Pytest config (`pyproject.toml`) sets `testpaths = ["tests"]`. `tests/conftest.py` inserts `PROJECT_ROOT` into `sys.path`, so `from hermes_cli.jarvis_prime import memory` resolves the namespace package correctly.

## Remaining risks

1. **Regex-based secret detection has false negatives** for novel credential formats (new vendor prefixes, base64 payloads without obvious markers). Mitigation belongs in a follow-on wave that wires the contract to provider-side scrubbing.
2. **Regex-based detection has false positives** for legitimately long mixed alphanumeric identifiers. Callers can split such identifiers across `key` and `value`, or store them via `note_task_progress` if they are transient.
3. **Voice-dump detection is marker-based** (`[voice]` prefix). A raw voice transcript without the marker would not be rejected. The intake pipeline (Slack/Termux ingestion) must tag voice inputs with the marker upstream — out of scope for this wave.
4. **No persistence** in this contract means durable state vanishes on process restart. The plugin provider system remains the durable substrate; wiring is a future wave.
5. **No thread-safety**. Concurrent mutations from the agent loop and a background scheduler would race. Add a lock when wiring in.
6. **No timestamps in the summary output**. `summarize_for_prompt` does not currently include `created_at` to keep output compact; a future wave may want to surface "most recent N entries" semantics.

## Out of scope for this wave

- Wiring to `plugins/memory/*` providers.
- Persistence schema for durable entries.
- Cross-process or cross-session synchronization.
- Slack / Termux / voice ingestion pipeline.
- `JARVIS remember` / `JARVIS forget` / `JARVIS correct` natural-language commands.
- Owner-gate authorization-decision tracking (referenced in `docs/jarvis-prime-operating-system.md:293-312`).

## Rollback

`git revert` the branch. No migrations, no shared-file changes, no external state, no provider config changes — the wave is fully reversible by removing the three new files.

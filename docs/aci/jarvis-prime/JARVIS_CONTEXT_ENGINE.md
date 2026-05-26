# Jarvis Prime Context Engine

Internal compression layer for model and tool payloads — Jarvis Prime's
TokenJuice-equivalent. Stateless, stdlib-only, pure-function. Lives at
`hermes_cli/context/` and is **not wired into the runtime** in wave W13;
adoption is a separate later wave.

## Mission

Reviewer-grade compression with **evidence preservation**. The engine must
shrink long payloads (logs, diffs, test output, stack traces, JSON
responses, markdown summaries, arbitrary text) into something that fits in
a model context window, while never losing the artifacts that make the
payload diagnostically useful: file paths, line numbers, function names,
test ids, error messages, stack frames, security warnings, owner-gated
phrases.

It must also refuse to leak obvious secrets. Every compressor scrubs
secret-like content **before** anything else runs.

## Public API

```python
from hermes_cli.context import (
    # Data
    ContextPacket,                # frozen dataclass returned by every compressor
    SOURCE_TYPES,                 # closed tuple of source_type values
    EVIDENCE_KINDS,               # closed tuple of preserved_evidence kinds
    SECRET_PATTERNS,              # ((kind, compiled_re), ...)
    COMPRESSORS,                  # ((source_type, fn), ...) for reflection

    # Compressors — return ContextPacket
    compress_text,                # arbitrary text / chat output
    compress_markdown,            # markdown documents
    compress_json,                # JSON payloads (str | Mapping | Sequence)
    compress_log,                 # application or build logs
    compress_diff,                # unified diffs
    compress_test_output,         # pytest / unittest / npm-test output
    compress_stack_trace,         # Python tracebacks

    # Redaction
    scrub,                        # (text) -> (cleaned, count_redacted)
    reject,                       # (text) -> first secret kind or None
)
```

### ContextPacket

```python
@dataclass(frozen=True)
class ContextPacket:
    source_type: str               # one of SOURCE_TYPES
    payload: str                   # the compressed body
    original_length: int           # chars in the input
    compressed_length: int         # chars in `payload`
    preserved_evidence: tuple[tuple[str, str], ...]   # ((kind, snippet), ...)
    warnings: tuple[str, ...]      # engine diagnostics
    artifact_ref: str | None       # caller-supplied stash pointer
```

- `compression_ratio` property (`compressed / original`, or 1.0 on empty input).
- `to_dict()` / `from_dict()` for JSON round-trip.

`preserved_evidence` kinds are a closed set: `file_path`, `line_ref`,
`function_name`, `test_id`, `error_message`, `stack_frame`,
`security_warning`, `owner_gate`.

## Compression rules

| Function | Policy |
|---|---|
| `compress_text` | Collapse runs of 2+ blank lines to one. Truncate to `max_chars` with `[... N chars elided ...]` marker, anchored to a paragraph boundary when possible. |
| `compress_markdown` | Headings (`^#{1,6} `) and fenced code blocks (` ``` `) verbatim. Prose paragraphs > 5 lines collapsed to first + `[... N lines elided ...]` + last. |
| `compress_json` | Parse with `json.loads`. Recurse into objects unchanged. Arrays of length > 5 replaced with `[first, second, "[<elided N items>]", last]`. Re-serialize compactly. Invalid JSON falls back to text compression with a warning. |
| `compress_log` | Strip ANSI escapes. Collapse consecutive identical lines into `<line> (× N)`. Any line matching `ERROR|WARN|WARNING|CRITICAL|FATAL|Traceback` is kept verbatim regardless of repetition. |
| `compress_diff` | Keep every line starting with `diff --git`, `+++`, `---`, `@@`, `+`, or `-`. Runs of 3+ unchanged context lines collapsed to `[... N unchanged lines ...]`. |
| `compress_test_output` | Keep every line matching `^(FAILED\|ERROR\|PASSED\|SKIPPED\|XFAIL\|XPASS) `. Keep every traceback block verbatim. Drop progress lines like `..F. [ 33%]`. |
| `compress_stack_trace` | Keep every `File "...", line N, in fn` frame plus its code line. Consecutive identical frames (recursion) collapsed to `... (frame repeated N more time(s)) ...`. Final exception line preserved verbatim. |

## Ordering inside every compressor

1. **`redaction.scrub(text)` runs first.** Returns `(cleaned, count_redacted)`. Count feeds `warnings` as `"redacted N secret-like tokens"`.
2. **Evidence extraction runs on the scrubbed text.** This ordering matters: if scrub ran second, an `error_message` line could quote a secret verbatim and survive in `preserved_evidence` even with a clean `payload`. Placeholder shape `[REDACTED:<kind>]` is chosen to avoid matching any evidence regex (square brackets aren't in `file:line`, `test_id`, or function-name shapes).
3. **Compression rules** for the specific payload type run on the scrubbed text to build `payload`.
4. **Assemble and return** the frozen `ContextPacket`.

## Redaction policy

`hermes_cli/context/redaction.py` is a **standalone mirror** of the secret
shapes most likely to appear in model / tool payloads. It does **not**
import from `agent/redact.py`. Reasons:

- `agent/redact.py` is **log-display** redaction — preserves head-6/tail-4
  characters for debuggability. Our use case is **payload** redaction:
  every secret must be fully replaced by a typed placeholder so downstream
  evidence extractors can pattern-match the placeholder shape and never
  accidentally capture a secret value.
- The forbidden-edit contract for this wave means we cannot coordinate
  changes to `agent/redact.py`; coupling would create a maintenance
  hazard.

Patterns mirrored (subset, payload-relevant):

| kind | shape |
|---|---|
| `openai_sk` | `sk-[A-Za-z0-9_-]{10,}` |
| `github_pat_classic` | `ghp_[A-Za-z0-9]{10,}` |
| `github_pat_fine_grained` | `github_pat_[A-Za-z0-9_]{10,}` |
| `github_oauth` | `gh[ousr]_[A-Za-z0-9]{10,}` |
| `slack_token` | `(?:xox[baprs]\|xapp)-[A-Za-z0-9-]{10,}` |
| `aws_access_key` | `AKIA[A-Z0-9]{16}` |
| `gcp_api_key` | `AIza[A-Za-z0-9_-]{30,}` |
| `jwt` | `eyJ[A-Za-z0-9_-]{10,}(?:\.[A-Za-z0-9_=-]{4,}){0,2}` |
| `private_key_block` | `-----BEGIN…PRIVATE KEY-----…-----END…PRIVATE KEY-----` |
| `auth_bearer` | `Authorization: Bearer <token>` (token replaced) |
| `env_assign_secret` | `(API_KEY\|TOKEN\|SECRET\|PASSWORD\|…)=<value>` |
| `json_field_secret` | `"token"`/`"api_key"`/`"secret"`/`"password"`/`"access_token"`/`"refresh_token"`: `"<value>"` |
| `db_connstr` | `(postgres\|mysql\|mongodb\|redis\|amqp)://user:<password>@host` (password replaced) |

**Mirror lag:** if `agent/redact.py` gains a new vendor prefix, a follow-up
wave should mirror it here. The W13 engine intentionally improves on
`agent/redact.py` in one place — Slack `xapp-` tokens are caught; a
follow-up wave should backport that improvement.

`reject(text)` is exposed as an alternative path for callers that would
rather refuse a payload than redact it.

## Relationship to existing modules

Several modules in the repo already touch the word "context" or
"compress". To avoid future-reviewer confusion:

| Module | Layer | What it does |
|---|---|---|
| `agent/context_engine.py` | runtime ABC | Plugin contract for whole-conversation compaction. Decides when to fire, handles session lifecycle. |
| `agent/context_compressor.py` | runtime impl | The default LLM-driven implementation of the above ABC. |
| `agent/redact.py` | log-display | Masks secrets in log lines while preserving head/tail for debuggability. |
| `trajectory_compressor.py` | async / LLM | Summarizes stored conversation trajectories via OpenRouter. |
| **`hermes_cli/context/`** (this wave) | **stateless / per-payload** | **Pure-function compressors for individual payloads — one stack trace, one diff, one log chunk. No I/O, no network, no LLM.** |

The five modules occupy distinct layers and should not be merged.

## Adoption notes (future wave)

When a future wave wires the engine into the runtime:

1. Add an **input-size cap** at the call site. The engine is stdlib `re`
   over arbitrarily large strings; pathological inputs should be rejected
   upstream rather than compressed.
2. Bridge `ContextPacket.preserved_evidence` into the verification packet
   (W05) and review packet (W05) so reviewers see structured evidence
   alongside the compressed payload.
3. Use `ContextPacket.artifact_ref` to point at the full-fidelity stash
   (S3 / disk / DB) for callers who need to recover the original text.
4. The engine has no async surface — call it from sync code or wrap it in
   `asyncio.to_thread()` if running inside an event loop with a large
   payload.

## Out of scope (this wave)

- Runtime wiring. Verification step 4 in the wave report enforces this.
- LLM-driven summarization. That belongs in `agent/context_compressor.py`.
- Token-aware compression. The engine is character-count based; if a
  future wave needs token-aware sizing, add it as a layer **above** the
  engine.
- Streaming compression. The engine consumes whole payloads.

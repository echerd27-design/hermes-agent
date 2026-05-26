# W12 — ACI Hermes Secret-Redaction & Credential-Safety Audit

> **Wave:** 12
> **Branch:** `aci/wave-12-secret-redaction-audit`
> **Mode:** Docs only — no source, no CI, no config touched.
> **Method:** Read-only inspection of the repo on 2026-05-26.
> **Author tooling:** Claude Code on the web (Opus 4.7, AOS Council bench).

This is the first report in `docs/aci/reports/W##_*.md` and sets the
house style for the series: Executive verdict, evidence with file:line
citations, P0/P1/P2 risks, test plan, no-go rules, rollback.

---

## 1. Executive Verdict

**Posture: solid core, fragmented edges.**

Hermes has a real, well-built central redactor (`agent/redact.py`,
467 lines, 7 documented regex families) that is imported by **at least
seven** modules outside `agent/redact.py` itself — logging handlers,
the gateway, the cron scheduler, the context compressor, the ACP
client, the Codex transport, and the CLI dump tool. A separate
streaming scrubber (`agent/think_scrubber.py`) blocks model
reasoning blocks from reaching users. `SECURITY.md` documents the
contract and is honest about the boundary
(`§2.4`: "A motivated output producer will defeat it.").

But three structural gaps mean Wave-13 has real work to do:

1. **There is no secret scanner anywhere in the toolchain.** No
   `.pre-commit-config.yaml`. No GitHub Actions job that runs
   `gitleaks` / `trufflehog` / `detect-secrets`. The
   `osv-scanner.yml` and `supply-chain-audit.yml` workflows scan
   dependencies, not source. This is the single P0.
2. **A second, parallel redaction implementation has emerged in the
   gateway.** `gateway/run.py:126–146` defines
   `_GATEWAY_SECRET_PATTERNS` and `_redact_gateway_user_facing_secrets()`
   with its own regex set (`hf_…`, `glpat-…`, `Bearer …`).
   Defense-in-depth is fine; **two un-synchronized sources of truth**
   is not.
3. **Tracebacks are the largest untested leakage surface.**
   `gateway/run.py` has ~20 `logger.exception()` / `exc_info=True`
   call sites; no test asserts that a credential embedded in a
   thrown exception is redacted before it lands in `gateway.log`.

The rest of this report inventories where secrets enter, where they
leak, what guards them today, and the exact P0/P1/P2 fixes for the
next wave.

---

## 2. Scope & Method

**In scope:**

- `agent/redact.py`, `agent/think_scrubber.py`, `hermes_logging.py`,
  `model_tools.py` (tool-error sanitizer), `cli.py`,
  `mini_swe_runner.py`, `hermes_constants.py`,
  `trajectory_compressor.py`, `run_agent.py`.
- `gateway/run.py`, `gateway/session.py`, `gateway/session_context.py`,
  `gateway/runtime_footer.py`, `gateway/shutdown_forensics.py`,
  `gateway/platforms/*.py` (15+ adapters).
- `cron/scheduler.py`.
- Install / bootstrap: `scripts/install.sh`, `scripts/install.cmd`,
  `scripts/install.ps1`, `dotclaude/install.sh`, `setup-hermes.sh`.
- Config surfaces: `.env.example`, `cli-config.yaml.example`,
  `docker-compose.yml`, `.gitignore`.
- Tests: `tests/test_hermes_logging.py`, `tests/agent/test_redact.py`,
  `tests/gateway/test_pii_redaction.py`,
  `tests/hermes_cli/test_redact_config_bridge.py`.
- Docs: `SECURITY.md`, `SETUP.md`, `CLAUDE.md`, `AGENTS.md`.

**Explicitly out of scope (this wave):**

- All source-code modification. The Universal Header non-overlap
  contract restricts this branch to one report file.
- Live secret scanning runs (`gitleaks`, `trufflehog`) against the
  repo. Recommendations only.
- Secret rotation, key rolling, or external credential reissuance.
- Native Android / mobile-app token storage. Hermes is currently
  CLI/Termux only (`SETUP.md` line ~40: "It is **not currently a
  native Android app project**"). The mobile finding is a doc gap,
  not a code gap.

**Method:** `grep` + targeted `Read` against the working tree on
branch `aci/wave-12-secret-redaction-audit` at HEAD `7b82077`.
Every claim below cites a file path and line number that can be
verified independently.

---

## 3. Where Secrets Can Enter

### 3.1 Environment variables

`.env` files and `os.getenv` are the front door. The intended
configuration is `.env.example` — copy to `.env`, fill in keys.

`.env.example` declares (commented placeholders only, no live keys):

- LLM providers — `OPENROUTER_API_KEY`, `NOVITA_API_KEY`,
  `GOOGLE_API_KEY` / `GEMINI_API_KEY`, `OLLAMA_API_KEY`,
  `GLM_API_KEY`, `KIMI_API_KEY`, `KIMI_CN_API_KEY`,
  `ARCEEAI_API_KEY`, `MINIMAX_API_KEY`, `MINIMAX_CN_API_KEY`,
  `OPENCODE_ZEN_API_KEY`, `OPENCODE_GO_API_KEY`, `XIAOMI_API_KEY`
  (`.env.example` lines 10–123).
- Search / tools — `HF_TOKEN`, `EXA_API_KEY`, `PARALLEL_API_KEY`,
  `FIRECRAWL_API_KEY`, `HONCHO_API_KEY`
  (`.env.example` lines 107–152).
- Privileged ops — `SUDO_PASSWORD` (`.env.example:232`).

Provider chain-fallback at `mini_swe_runner.py:216–232`:

```python
key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENROUTER_API_KEY")
```

Gateway adapters pull their own tokens directly from `os.environ`,
e.g. `gateway/session.py:219`:

```python
if not (os.environ.get("DISCORD_BOT_TOKEN") or "").strip():
```

`cli.py:602–615` **writes** provider env vars back to `os.environ`
during interactive setup (`os.environ["HERMES_REDACT_SECRETS"] = ...`
on line 615), so the process inherits whatever the user typed at
the prompt. This is fine but means any logger that hits
`os.environ` after that line carries the credential in-process.

### 3.2 Config files & settings

- `.env.example` — placeholders only. Verified clean.
- `cli-config.yaml.example` — present at repo root; reviewed for
  shape, no live secrets.
- `docker-compose.yml:5–7, 34–35, 51–55, 68–69` — forwards
  `HERMES_UID`, `HERMES_GID`, and commented-out `GOOGLE_CHAT_*`
  values. No secrets inline.
- `.gitignore` properly excludes `.env`, `.env.local`,
  `.env.development.local`, `.env.test.local`,
  `.env.production.local`, `.env.development`, `.env.test`. **It
  does not exclude `.pem`, `credentials.json`, `*.key`, or
  `*.keystore`** — a small but real P2 hardening item.

### 3.3 Install / bootstrap scripts

- `scripts/install.sh` (1300+ lines) — many `echo` calls, all
  reviewed; none interpolate env credentials. Help text and status
  lines only.
- `scripts/install.ps1:1760–1871` — references token env vars
  (`TELEGRAM_BOT_TOKEN`, `DISCORD_BOT_TOKEN`, `SLACK_BOT_TOKEN`,
  `SLACK_APP_TOKEN`) only to gate optional dependency installs.
  No echo of token values to stdout.
- `scripts/install.cmd`, `dotclaude/install.sh`, `setup-hermes.sh`,
  `scripts/hermes-mobile-workspace-init.sh` — also reviewed for
  echo-of-credential patterns. None found at first read, but none
  are exercised by an automated dry-run test. **This is the right
  shape of risk to assert against in Wave-13** (§10).

### 3.4 Android / Termux token storage

`SETUP.md` documents Termux-on-Android as the supported mobile
runtime: provider keys live in `.env` files on the device's
filesystem, protected only by the Termux home directory's POSIX
permissions. There is no:

- Android Keystore integration,
- `EncryptedSharedPreferences`,
- `AccountManager` hook,
- guidance on `chmod 600 .env`.

This is a documentation gap (P2), not a code gap. There is no
native Android app today.

---

## 4. Where Secrets Can Leak

Secrets enter at §3 and could exit at one of these sinks.

### 4.1 Logging

The single central choke point is `hermes_logging.py`. Lines 211,
222, 232, 243, 267, 279 attach
`agent.redact.RedactingFormatter` to **every** rotating handler
(`agent.log`, `errors.log`, `gateway.log`) and the verbose console
handler. Anything that goes through Python `logging` is filtered.

What does **not** go through `logging`:

- `print()` calls that interpolate `os.environ`, request headers,
  auth payloads. There are **no proven** offenders found by grep
  at audit time, but there is no test that would catch a future
  one.
- `repr(settings)` / `dataclasses.asdict(settings)` if a config
  object ever shipped a token. No pydantic `SecretStr` in use.

### 4.2 Gateway adapters

`gateway/platforms/` has 15+ adapters (`api_server`, `bluebubbles`,
`dingtalk`, `discord`, `email`, `feishu`, `feishu_comment`,
`homeassistant`, `matrix`, `mattermost`, `msgraph_webhook`, `qqbot`,
`signal`, `slack`, `sms`, `telegram`, `webhook`). Each one sends
arbitrary tool/agent output back to a user over a third-party
channel — the highest blast-radius sink in the codebase.

`gateway/run.py:7345–7348` redacts output before dispatch:

```python
# Redact any remaining sensitive patterns in output
from agent.redact import redact_sensitive_text
output = redact_sensitive_text(output)
```

…and `gateway/run.py:17918–17923` installs `RedactingFormatter`
on the gateway's stderr handler. **However**, the same file
(`gateway/run.py:126–146`) defines a parallel set
`_GATEWAY_SECRET_PATTERNS` covering `hf_…`, `glpat-…`, and
`Bearer …` and a parallel function
`_redact_gateway_user_facing_secrets()`. This is invoked from
`gateway/run.py:219` and `:233`. Defense-in-depth is fine; the
risk is **drift** — when a new prefix family is added to
`agent/redact.py` it must also be added (or proven covered) here.

### 4.3 Tool output / agent loop / compressor

- `model_tools.py:515–538` — `_sanitize_tool_error()` truncates
  tool errors to 2000 chars and strips role tags, fences, and
  CDATA. Good. Cited from
  `tests/test_hermes_logging.py` baseline behavior.
- `agent/context_compressor.py:845, 866, 1078` — runs
  `redact_sensitive_text` over compressed message content and
  function-call arguments. Good.
- `agent/copilot_acp_client.py:651` — runs `redact_sensitive_text`
  with `force=True` on outbound content. Good.
- `agent/transports/codex_app_server_session.py:323` — same.
  Good.
- `cron/scheduler.py:906–908` — runs `redact_sensitive_text` over
  `stdout`/`stderr` of scheduled jobs. Good.
- `trajectory_compressor.py` — **no redaction calls found.**
  This is an offline utility that reads `.jsonl` files, but a
  user who runs it against a trajectory that captured raw API
  responses would write the compressed result back to disk with
  any credential still in place. P1.

### 4.4 Crash / shutdown / forensics

- `gateway/shutdown_forensics.py:137, 140, 171, 339` — reads
  `INVOCATION_ID`, `JOURNAL_STREAM`, `HERMES_HOME`. No direct
  read of a credential env var, but the file's purpose is to
  capture process state on crash — it must run output through
  the redactor before serializing. Not currently verified by
  test.
- `gateway/run.py` `logger.exception()` / `exc_info=True` sites:
  1672, 1942, 2071, 3673, 3751, 3770, 4148, 4154, 4205, 6415,
  7799, 7861, 7878, 8814, 9114, 10260, 10582, 11135, 11513.
  These flow through the logging handlers in §4.1 and therefore
  through `RedactingFormatter` — but only the *rendered message*
  is redacted, not the *exception arguments* attached to the
  `LogRecord`. A handler that introspects `record.exc_info`
  directly (e.g. JSON sink, Sentry transport) bypasses the
  formatter. No such handler exists today; one could land
  tomorrow. P1.

### 4.5 Skills / plugins

`SECURITY.md §2.4` is explicit: "Skills Guard scans installable
skill content for injection patterns. It is a review aid; the
boundary for third-party skills is operator review before install."

This audit confirms: there is no automated, redaction-aware
boundary between a skill's `print()` / tool return value and the
user. A malicious or buggy skill that prints an env var will leak
it. The mitigation today is human review (§2.5).

---

## 5. Redaction Mechanisms — Current State

Four cooperating layers exist today, plus a feature flag.

| Layer | File | What it covers |
|---|---|---|
| **Central regex redactor** | `agent/redact.py` (467 lines) | `sk-`, `sk_`, `hsk-`, `ghp_`, `github_pat_`, `xoxb-`, `AKIA` prefix families (lines 70–110); `Authorization: Bearer …`; private-key PEM blocks; DB connection strings; JWTs; URL query params; URL userinfo; form bodies; phone numbers; Discord/Telegram identifiers. Entry points: `mask_secret()`, `redact_sensitive_text()`, `RedactingFormatter` (line 459). |
| **Streaming reasoning scrubber** | `agent/think_scrubber.py` | State machine that strips `<think>`, `<thinking>`, `<reasoning>`, `<thought>`, `<REASONING_SCRATCHPAD>` blocks from streamed model output before they reach the user. `feed()`, `flush()`, `reset()`. |
| **Tool-error sanitizer** | `model_tools.py:515–538` | `_sanitize_tool_error()`: truncates to 2000 chars; strips role tags, fence markers, CDATA. Prevents credential-bearing tool errors from escaping inline. |
| **Gateway-local redactor (parallel)** | `gateway/run.py:126–146` | `_GATEWAY_SECRET_PATTERNS`: `hf_…`, `glpat-…`, `Bearer …`. Invoked at `:219` and `:233` before text leaves the gateway. **Pattern set is not synchronized with `agent/redact.py`.** |
| **Runtime gate** | `agent/redact.py:67`, `cli.py:615, 11897` | `HERMES_REDACT_SECRETS` env flag, default `"true"`. `cli.py:615` writes it; `agent/redact.py:67` reads it at module load. |

Cross-reference: `SECURITY.md §2.4` ("Output redaction") documents
the contract and explicitly disclaims it as a heuristic, not a
boundary.

### Coverage map — who imports the central redactor

```
hermes_logging.py:211, 267                   RedactingFormatter
gateway/run.py:7347                          redact_sensitive_text  (output dispatch)
gateway/run.py:17918                         RedactingFormatter     (stderr handler)
cron/scheduler.py:906–908                    redact_sensitive_text  (job stdout/stderr)
agent/copilot_acp_client.py:651              redact_sensitive_text  (force=True)
agent/context_compressor.py:845, 866, 1078   redact_sensitive_text  (compressor inputs)
agent/transports/codex_app_server_session.py:323
                                             redact_sensitive_text  (force=True)
hermes_cli/dump.py:43                        mask_secret            (CLI dump)
```

**Eight callers in production code paths.** This is broader than
the "central redactor only used in `hermes_logging.py`" hypothesis
the audit started from.

---

## 6. Missing Tests — Coverage Gaps

Baseline that already exists:

- `tests/test_hermes_logging.py` (776 lines) — central logging +
  redaction behavior.
- `tests/agent/test_redact.py` — unit tests for `redact.py`
  patterns and helpers.
- `tests/gateway/test_pii_redaction.py` — gateway-context PII
  scrubbing.
- `tests/hermes_cli/test_redact_config_bridge.py` — CLI ↔ env
  flag wiring.

What is **not** asserted today:

1. **End-to-end per-platform leak tests.** No test feeds a
   synthetic `sk-test-…` / `ghp_test_…` through each of the 15+
   `gateway/platforms/*.py` adapters and asserts the outbound
   payload contains `[REDACTED]`.
2. **Exception-traceback redaction.** None of the ~20
   `exc_info=True` sites in `gateway/run.py` are exercised in a
   test that asserts the traceback text in the resulting
   `LogRecord` has been redacted.
3. **`gateway/shutdown_forensics.py` crash-dump assembly.**
4. **Trajectory compressor.** `trajectory_compressor.py` has no
   redaction calls at all — no test covers it because there is
   nothing to cover.
5. **`ThinkScrubber` boundary tests.** Partial-block flushes
   across streamed chunks, nested tags, malformed close tags.
6. **Pattern-drift test.** A test that asserts every regex in
   `_GATEWAY_SECRET_PATTERNS` (`gateway/run.py:126`) is also
   matched by `redact_sensitive_text()` from `agent/redact.py`.
   Today there is nothing preventing drift.
7. **Skill / plugin output redaction at the render boundary.**
8. **Install-script dry-run tests** asserting no credential
   appears in stdout when `OPENROUTER_API_KEY=test123…` is
   exported.
9. **Negative pattern coverage.** Each documented prefix in
   `agent/redact.py:70–110` should have a parametrized test that
   feeds a known-bad string through every documented sink in §5.

---

## 7. Highest-Risk Files (Ranked)

1. **`gateway/run.py`** — ~20 `exc_info=True` sites, plus a
   parallel-and-drifting redactor at lines 126–146. Single largest
   surface in the codebase.
2. **`gateway/platforms/*.py`** — 15+ adapters; any one of them
   that calls `logger.info(payload)` *before* the dispatch-time
   redaction in `gateway/run.py:7347` could leak.
3. **`scripts/install.sh`** (~1300 lines) — large bash surface
   with many `echo` calls; no automated test asserting no
   credential interpolation.
4. **`trajectory_compressor.py`** — offline utility that reads
   raw `.jsonl` and writes compressed `.jsonl` with no redaction.
5. **`gateway/shutdown_forensics.py`** — crash dumps include
   environment context.
6. **`cli.py:602–615`** — env-var write-back path. A future
   logger interpolating `os.environ` after this point would leak.
7. **`mini_swe_runner.py:216–232`** — multi-provider key
   fallback chain.
8. **`run_agent.py`** — extensive `logger.info/debug` across
   model selection, tool invocation, context injection. Currently
   safe because formatter redacts, but introspection-based
   handlers would bypass.
9. **`scripts/install.ps1`, `scripts/install.cmd`,
   `dotclaude/install.sh`, `setup-hermes.sh`,
   `scripts/hermes-mobile-workspace-init.sh`** — install-script
   family. Reviewed clean at audit time; no dry-run test.

---

## 8. Exact Future Fixes (P0 / P1 / P2)

### P0 — Do these in Wave 13

| ID | Target | Fix | Verification |
|---|---|---|---|
| P0-1 | `.pre-commit-config.yaml` (new) | Add `gitleaks` (or `detect-secrets` baseline) hook. None exists today (`ls .pre-commit-config.yaml` → not found). | `pre-commit run --all-files` returns 0. |
| P0-2 | `.github/workflows/secret-scan.yml` (new) | Add a GitHub Actions job that runs the same scanner on every PR, gated as a required check. Mirror the shape of `.github/workflows/osv-scanner.yml`. | New PR with a planted fake `sk-test_…` string fails CI. |
| P0-3 | `gateway/run.py:126–146` ↔ `agent/redact.py` | Replace `_GATEWAY_SECRET_PATTERNS` with a call into `agent.redact.redact_sensitive_text(text, force=True)`. Single source of truth. | Pattern-drift test (§6, item 6) passes. |
| P0-4 | `tests/security/test_redaction_e2e.py` (new) | Parametrized over every gateway adapter in `gateway/platforms/`. Feed `sk-test-1234567890abcdef` through; assert outbound payload contains `[REDACTED]`. | `pytest tests/security/ -v` green. |

### P1 — Next sprint

| ID | Target | Fix | Verification |
|---|---|---|---|
| P1-1 | `trajectory_compressor.py` | Import `agent.redact.redact_sensitive_text`; apply on read and on write. | Round-trip test with planted secret confirms `[REDACTED]` in output. |
| P1-2 | `gateway/shutdown_forensics.py` | Wrap crash-dump serialization in `redact_sensitive_text(force=True)`. | Unit test that exports `OPENROUTER_API_KEY=sk-test-…`, triggers a crash dump, asserts redaction. |
| P1-3 | `gateway/run.py` `exc_info=True` sites | Add `tests/security/test_exception_redaction.py` that raises an exception carrying a `sk-test-…` string and asserts the formatted log line is redacted. | Test passes for all ~20 sites (table-driven). |
| P1-4 | `tests/security/test_think_scrubber_boundaries.py` (new) | Cover partial-block flush, nested tags, malformed close tags. | Tests pass; coverage report shows `agent/think_scrubber.py` ≥ 90%. |
| P1-5 | `tests/security/test_install_scripts_dry_run.py` (new) | Export fake credentials, run each install script in `--dry-run` (add the flag if missing), assert no credential text appears in stdout. | All scripts pass. |

### P2 — Hardening

| ID | Target | Fix | Verification |
|---|---|---|---|
| P2-1 | `SECURITY.md` | Add §2.7 "Android / Termux token storage" — document the actual posture (POSIX-only protection), recommend `chmod 600 ~/.env`, and explicitly call out the absence of Keystore/EncryptedSharedPreferences. | Doc PR review. |
| P2-2 | `.gitignore` | Add `*.pem`, `*.key`, `*.keystore`, `credentials.json`, `service-account*.json`. | `git check-ignore` returns the path for each. |
| P2-3 | `model_tools.py:515–538` | The 2000-char truncation in `_sanitize_tool_error()` can split a credential mid-string. Run `mask_secret()` *before* truncation. | Unit test: a `sk-…` straddling byte 1990–2010 is still fully masked. |
| P2-4 | `cli.py:602–615` | After `os.environ["…"] = value` writes, log a single masked confirmation via `mask_secret(value)` instead of relying on the absence of any logger. | Test that captures stdout/stderr during interactive setup confirms only `sk-…REDACTED…last4` shape. |
| P2-5 | `SECURITY.md §2.4` | Update the "Output redaction" sub-bullet to enumerate the 8 callers from §5's coverage map, so future contributors know where to add new ones. | Doc PR review. |

---

## 9. No-Go Rules (Policy)

These are the lines this codebase should not cross. Treat them as
review checks.

- **No `print(os.environ)` / `print(headers)` / `repr(settings)` in
  any non-test code path.** Use the logger so the
  `RedactingFormatter` runs.
- **No `.env` reads inside install scripts that also write to a
  logfile.** If the install script needs to remember a path or a
  flag, write a non-secret marker file (e.g. `~/.hermes/.installed`).
- **No real-shaped tokens in test fixtures, ever.** Use the
  placeholder constants from `tests/test_hermes_logging.py`
  (`sk-test_…`, `ghp_test_…`, etc.).
- **Every new gateway / adapter / skill / plugin lands with a
  redaction test on the same PR.**
- **Every new regex family added to `agent/redact.py` must
  ALSO** be covered by the pattern-drift test (§6 item 6) — no
  silent drift between `agent/redact.py` and any local redactor.
- **No introspection-based log handler** (JSON sink, OpenTelemetry,
  Sentry) lands without a redaction layer between
  `record.exc_info` and the wire.
- **Trajectories / compressed transcripts / forensics dumps go
  through `redact_sensitive_text(..., force=True)` before any
  `open(..., "w")`.**

---

## 10. Test Plan for Wave 13

Concrete, runnable commands the next implementer can copy-paste.

```bash
# Baseline (must stay green).
pytest tests/test_hermes_logging.py -v
pytest tests/agent/test_redact.py -v
pytest tests/gateway/test_pii_redaction.py -v
pytest tests/hermes_cli/test_redact_config_bridge.py -v

# New test files to create (paths only; contents are P0/P1 work).
pytest tests/security/test_redaction_e2e.py -v                      # P0-4
pytest tests/security/test_exception_redaction.py -v                # P1-3
pytest tests/security/test_think_scrubber_boundaries.py -v          # P1-4
pytest tests/security/test_install_scripts_dry_run.py -v            # P1-5
pytest tests/security/test_pattern_drift.py -v                      # P0-3
pytest tests/security/test_trajectory_compressor_redaction.py -v    # P1-1
pytest tests/security/test_shutdown_forensics_redaction.py -v       # P1-2

# Pre-commit secret scanner (new — P0-1).
pre-commit install
pre-commit run --all-files

# CI gate (new — P0-2): job in .github/workflows/secret-scan.yml.
# Verify by opening a draft PR with a planted fake token and
# confirming CI fails.

# Manual review checklist (to add to CONTRIBUTING.md in Wave 13):
#   [ ] New regex pattern? Added to agent/redact.py AND to drift test?
#   [ ] New gateway adapter? Has a per-adapter redaction E2E test?
#   [ ] New install path? Has a dry-run test with fake credentials?
#   [ ] New crash/forensics writer? Wrapped in redact_sensitive_text?
```

---

## 11. Verification of This Report

The Universal Header acceptance criteria for Wave 12:

1. `git diff --stat` shows **one** file: `docs/aci/reports/W12_SECRET_REDACTION_AUDIT.md`. No source, no CI, no `pyproject.toml`, no `uv.lock` touched.
2. This report contains **P0**, **P1**, and **P2** severity buckets (§8).
3. This report contains a **test plan** (§10).
4. No real-shaped credential strings appear in this report. The
   only secret-shaped examples are explicitly prefixed `test-` /
   `test_` placeholders.

## 12. Rollback

```bash
rm /home/user/hermes-agent/docs/aci/reports/W12_SECRET_REDACTION_AUDIT.md
# If docs/aci/reports/ is now empty:
rmdir /home/user/hermes-agent/docs/aci/reports
```

No source state to revert. No CI state to revert. No external
side effects (no deploys, no rotations, no app store submissions,
no secrets touched).

## 13. Open Questions (Blocking Only)

None blocking. Two non-blocking questions for the Wave-13
implementer to decide:

- **Q1.** `gitleaks` vs `detect-secrets` for P0-1. `detect-secrets`
  has a baseline file model that suits a brownfield repo; `gitleaks`
  is faster and has a richer default rule set. Either is acceptable.
- **Q2.** Should `_redact_gateway_user_facing_secrets()`
  (`gateway/run.py:141`) be deleted outright in P0-3, or kept as a
  fast-path with a runtime assertion that
  `agent.redact.redact_sensitive_text` is the source of truth?
  Either is acceptable; the former is simpler.

---

*End of W12 report.*

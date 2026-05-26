# W10 — Android Diagnostics

- **Wave**: 10 / Android diagnostics hardening
- **Builder**: Claude Code (`/builder`)
- **Date**: 2026-05-26
- **Status**: `escalated — not executed`
- **Reason**: Wave target sources are not present in this repository.

---

## 1. Status

This wave was routed to `echerd27-design/hermes-agent` but its
`ALLOWED FILES` list points exclusively at an Android client tree
(`apps/android/app/src/main/java/com/aci/hermes/**`) that does not exist
in `hermes-agent`. The wave is therefore reported as **not executed** and
escalated for re-routing to the correct ACI Hermes Android repository.

No source code was created or modified. The only artifact produced is
this report.

## 2. Repo reconnaissance evidence

Each negative-result command below is reproducible from the repo root
(`/home/user/hermes-agent`). All four returned zero matches at the time
of this report:

```
find . -type d -name android
find . -type f \( -name "*.kt" -o -name "*.kts" -o -name "*.java" -o -name "AndroidManifest.xml" \)
find . -type f -name "build.gradle*"
grep -rIl -E "(apps/android|com\.aci\.hermes)" .
```

Supporting observations:

- No `apps/` directory exists at the repo root.
- `recovered-agent-sources/from-hazmat-command/` and
  `recovered-agent-sources/from-hermes-agent/` do not contain any
  Android client sources either; they are agent / skill / doc snapshots.
- The repository's primary surface is the Python Hermes runtime (`cli.py`,
  `gateway/`, `hermes/`, `web/`, `ui-tui/`, `tools/`, `skills/`,
  `plugins/`). No Gradle, no `BuildConfig`, no `AndroidManifest.xml`.

## 3. Branch-name mismatch (recorded for the orchestrator)

- **Universal Header asked for branch**: `aci/wave-10-android-diagnostics`
- **Session-level harness branch**: `claude/charming-wright-2OEk6`

The session-level harness explicitly instructed development on
`claude/charming-wright-2OEk6`. Because this wave's premise is broken
(wrong repo / missing scaffolding), creating an `aci/wave-10-…` branch
inside `hermes-agent` would inject a misleading branch name into a repo
that has no Android sources to host. The harness branch is therefore
used, and this mismatch is logged here so the orchestrator can resolve
it when re-routing the wave.

## 4. What this wave was supposed to deliver

A mobile-only diagnostics surface inside the ACI Hermes Android app, so a
user without a developer machine can self-triage. Forward-looking spec
for the next builder (in the correct repo):

| Field | Source | Notes |
| ----- | ------ | ----- |
| Backend URL | `BuildConfig` / config repo | Host only; strip path, query, fragment. |
| Connection state | App-level network monitor | `idle` / `connecting` / `open` / `error`. |
| Last health check | `HealthChecker` cached result | Status code + ISO-8601 timestamp + latency ms. |
| App version | `BuildConfig.VERSION_NAME` / `VERSION_CODE` | Plus `BuildConfig.BUILD_TYPE`. |
| Mock mode | `BuildConfig` flag or local pref | Never read from network. |
| Last error | In-memory error sink | Exception class + sanitized message. No stack traces in UI. |
| Safe log buffer | Bounded ring buffer (e.g. 200 lines) | Every entry passes through `Redactor` before storage. |

UX expectations carried from the prompt:

- Diagnostics screen is read-only and does not initiate auth or network
  calls beyond the existing health check.
- Existing UI flows outside the diagnostics screen remain unchanged.
- A single "copy to clipboard" affordance copies the same redacted
  string the screen renders — never raw memory.

## 5. Redaction rules (carry-forward spec)

Centralize all rendering through a single `Redactor` helper so the
deny-list is the source of truth, exercised by unit tests.

### 5.1 Never render (drop entirely or replace with the literal `[redacted]`)

- HTTP `Authorization` header values
- Any string prefixed with `Bearer ` (case-insensitive)
- API keys / `X-Api-Key` / `X-Auth-Token` header values
- Refresh tokens, OAuth authorization codes, OAuth state nonces
- Session cookies, `Set-Cookie` values
- JWTs — any value matching the structural pattern
  `[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+` whose first segment
  begins with the standard `eyJ` header prefix
- Basic-auth `user:pass` strings inside URLs (`https://u:p@host/...`)
- Query-string secrets: `token=`, `access_token=`, `id_token=`,
  `refresh_token=`, `code=`, `key=`, `api_key=`, `apikey=`, `password=`,
  `secret=` — strip the entire `name=value` pair before display
- Push notification tokens (FCM / APNs)
- Device IDs, ANDROID_ID, IMEI, serial numbers, advertising IDs
- Personal data: email, phone, name, address, payment card numbers

### 5.2 Render in shortened form

Only when the value is **not** also in §5.1, and only when display value
aids debugging:

- Request IDs / trace IDs / span IDs → `first 4 + "…" + last 2`
- Account / tenant IDs → same shortened form

### 5.3 Render verbatim

- HTTP status codes
- Latency in milliseconds
- ISO-8601 timestamps
- Host portion of a URL (no path, no query)
- Exception class names (without messages that may carry data)
- `BuildConfig` flags (booleans / build type strings)

### 5.4 Test obligations

- Unit tests must assert that representative samples for every §5.1
  class are not present in the `Redactor` output.
- A property-style test should generate random JWT-shaped strings and
  confirm they are dropped.
- A "golden file" test should run a realistic log line through the
  redactor and assert byte-for-byte equality with an expected redacted
  output.

## 6. Acceptance criteria the receiving repo must meet

Mirrors the prompt's gates so the next builder does not have to
re-derive them:

- `./gradlew assembleDebug` succeeds on a clean checkout.
- `./gradlew testDebugUnitTest` succeeds and includes the `Redactor`
  tests described in §5.4.
- Diagnostics screen never displays any §5.1 value, including in error
  toasts, snackbars, or "copy" clipboard payloads.
- UI behavior outside the diagnostics screen is preserved (no changes
  to navigation, theming, or existing screens).
- Package name remains `com.aci.hermes`.
- No new dependencies in `apps/android/app/build.gradle.kts`. No
  changes to `apps/android/build.gradle.kts`.
- No edits to `pyproject.toml`, `uv.lock`, `README.md`, or any GitHub
  workflow.

## 7. Why tests were skipped here

The universal-header rule "Every change needs tests or a written reason
tests were skipped" applies. The reason: no executable code changed.
This wave produced one Markdown report and zero Android, Kotlin, or
Gradle artifacts. There is nothing to compile and nothing to unit-test.
`./gradlew assembleDebug` and `./gradlew testDebugUnitTest` were not run
because no Gradle project exists in this repository.

## 8. Rollback

No code changed. To roll back:

- Close the draft PR without merging, **or**
- If merged, revert the merge commit — the report file is the only
  artifact added.

## 9. Remaining risks

- **Re-routing risk**: until this wave is re-issued against the actual
  ACI Hermes Android repository, the mobile diagnostics surface remains
  un-hardened.
- **Spec drift**: §5's redaction list reflects the prompt's intent on
  2026-05-26. If the upstream ACI security policy already defines a
  stricter or different list, that policy supersedes §5.
- **Branch-name drift**: §3 records the harness vs. universal-header
  branch mismatch. If the orchestrator expects automation to find a
  branch literally named `aci/wave-10-android-diagnostics`, that
  automation will fail against this PR and must be updated or re-pointed.

## 10. PR summary block (paste-ready)

```
## Summary

- Wave 10 ("Harden Android diagnostics") was routed to hermes-agent, but
  hermes-agent has no Android sources: no apps/android/, no
  *.kt / *.kts / *.java / AndroidManifest.xml, no build.gradle* files.
- This PR is a docs-only escalation. It adds one file
  (docs/aci/reports/W10_ANDROID_DIAGNOSTICS.md) explaining the mismatch
  and carrying a forward spec for the next builder in the correct repo.
- No source code changes. No dependency changes. No FORBIDDEN files
  touched.

## Test plan

- [x] `git diff --stat origin/main..HEAD` shows exactly one added file
- [x] Secret-pattern grep on the report confirms no real tokens / JWTs
      / API keys were pasted (pattern names appear only as deny-list
      documentation, not as live secret values)
- [ ] N/A: ./gradlew assembleDebug — no Gradle project exists here
- [ ] N/A: ./gradlew testDebugUnitTest — no Gradle project exists here

## Out of scope

- Creating apps/android/ scaffolding (blocked by FORBIDDEN FILES +
  "no dependency changes" rule).
- Editing pyproject.toml, uv.lock, README.md, or any GitHub workflow.
- Merging this PR or marking it ready-for-review.
```

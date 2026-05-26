# W01 Android Audit Report

**Sprint:** W01 — Audit existing Android app for Jarvis Prime command center
**Branch:** `aci/jarvis-prime-01-android-audit` (branched from `origin/main`)
**Author/agent:** Claude Code (Opus, plan-mode-approved)
**Audit date:** 2026-05-26

---

## Executive verdict

The Android application target `apps/android/` **does not exist** in this
repository. There is no `AndroidManifest.xml`, no Gradle project, and no
Kotlin/Java source in any branch or in any commit reachable through
`git log --all`. The repository is the Python-based Hermes Agent codebase.

W01 therefore ships as a **documentation-only, greenfield audit**: it
records the absence with verification commands, restates the Jarvis Prime
global product rules that future Android work must obey, and lays down a
sprint-by-sprint file ownership map (W02 → W09) so subsequent PRs can
scaffold the app without colliding with each other.

No Android source code is created in W01.

---

## Changed files

| Path | Status |
|------|--------|
| `docs/aci/android/JARVIS_ANDROID_CURRENT_STATE_AUDIT.md` | new |
| `docs/aci/android/JARVIS_ANDROID_SCREEN_MAP.md` | new |
| `docs/aci/android/JARVIS_ANDROID_FILE_OWNERSHIP_MAP.md` | new |
| `docs/aci/reports/W01_ANDROID_AUDIT_REPORT.md` | new (this file) |

Confirmed by `git diff --stat origin/main...HEAD`. No files outside
`docs/aci/` are modified. None of the FORBIDDEN paths
(`apps/android/**`, `hermes_cli/**`, `skills/**`, `README.md`,
`pyproject.toml`, `uv.lock`, `.github/**`, `build.gradle*`,
`settings.gradle*`, package files) is touched.

---

## Tests run

**None.** Rationale:

- The four deliverables are markdown documents with no executable
  surface. There is no unit-testable or runnable code in this PR.
- The sprint header's build/test contract
  (`cd apps/android && ./gradlew assembleDebug` and `./gradlew
  testDebugUnitTest`) cannot be exercised because `apps/android/` does
  not exist yet. These commands would fail with "No such file or
  directory" and are recorded as the W02 acceptance contract instead.
- No Python tests are in scope: no Python files are modified.

If a future reviewer wants an artifact-style check, the verification
commands in `JARVIS_ANDROID_CURRENT_STATE_AUDIT.md` are reproducible
and will return identical output until `apps/android/` is scaffolded
in W02.

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Future PRs (W02+) diverge from the ownership map and create overlapping edits to shared files (`AndroidManifest.xml`, nav graph, version catalog). | Medium | Each W02–W09 PR description must cite `JARVIS_ANDROID_FILE_OWNERSHIP_MAP.md` and list which shared files it touches. PR reviewers should reject PRs that edit shared files outside their sprint's allowed list. |
| The recommended stack (Compose + Material 3 + DataStore + Room + OkHttp/Ktor) becomes stale by the time W02 begins. | Low | W02 owns the version pin via `libs.versions.toml`. This audit is decision-neutral on exact versions. |
| DI strategy (Hilt vs manual `AppContainer`) is left to W02; if W02 picks Hilt, some shared-file rules in the ownership map (specifically `di/AppContainer.kt`) become moot. | Low | Both layouts are covered in the ownership map. W02 selects one and updates the map in a follow-up if needed. |
| The sprint header references repo `A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent` but the active remote is `echerd27-design/hermes-agent`. If the Android app lives in the A-C-I org, this audit is the wrong target. | Medium | Recorded as an open question in `JARVIS_ANDROID_CURRENT_STATE_AUDIT.md`; user has confirmed the greenfield interpretation. If the A-C-I org repo turns out to contain an existing Android app, a follow-up W01b audit will be required. |
| Secrets leakage. | None | This PR adds no code, no env values, no fixtures, no screenshots. |

---

## Rollback plan

Single-step rollback. From the audit branch:

```bash
git rm docs/aci/android/JARVIS_ANDROID_CURRENT_STATE_AUDIT.md \
       docs/aci/android/JARVIS_ANDROID_SCREEN_MAP.md \
       docs/aci/android/JARVIS_ANDROID_FILE_OWNERSHIP_MAP.md \
       docs/aci/reports/W01_ANDROID_AUDIT_REPORT.md
git commit -m "revert: W01 audit"
git push origin aci/jarvis-prime-01-android-audit
```

No runtime impact: nothing is wired up to these documents. If the draft
PR has not been merged (and it will not be, per the sprint header), the
branch can simply be deleted: `git push origin --delete
aci/jarvis-prime-01-android-audit`.

---

## Collision report

Open-PR scan: only `main` and `aci/jarvis-prime-01-android-audit` exist
as branches at audit time. No other branch touches `docs/aci/**` or
`apps/android/**`. No collisions.

If the GitHub MCP tools are available at PR time, `mcp__github__list_pull_requests`
should be re-run to confirm no concurrent draft PRs touch the same
ALLOWED FILES. (The sprint header asks for `gh pr list --state open --limit
50`; the `gh` CLI is not available in this environment — the MCP equivalent
is used.)

---

## Draft PR summary (copy-paste body for `gh pr create --draft` or `mcp__github__create_pull_request`)

```
## W01: Audit existing Android app for Jarvis Prime command center

**Verdict:** No Android app exists in `apps/android/` today. This PR
ships a documentation-only, greenfield audit that records the absence
and lays down a sprint-by-sprint file ownership map for W02–W09.

### What this PR adds
- `docs/aci/android/JARVIS_ANDROID_CURRENT_STATE_AUDIT.md` — verdict,
  verification commands, item-by-item "NOT FOUND" findings, design
  rules carried forward (no Python in APK, no SMS/CallLog/always-on,
  no auto-notification prompt, mic only on tap).
- `docs/aci/android/JARVIS_ANDROID_SCREEN_MAP.md` — target Compose
  screens (Orchestrator, Tasks, Diagnostics, Settings, Voice, About),
  routes, ViewModels, permission triggers.
- `docs/aci/android/JARVIS_ANDROID_FILE_OWNERSHIP_MAP.md` — full
  greenfield tree under `apps/android/`, owning-PR per file, shared
  files and concurrency rules.
- `docs/aci/reports/W01_ANDROID_AUDIT_REPORT.md` — this report.

### What this PR does NOT do
- Does not create or modify anything under `apps/android/**`.
- Does not modify `hermes_cli/**`, `skills/**`, `README.md`,
  `pyproject.toml`, `uv.lock`, `.github/**`, or any Gradle/package
  file.
- Does not deploy, publish, change DNS, alter credentials, or move
  money.

### Tests
None run. Rationale documented in
`docs/aci/reports/W01_ANDROID_AUDIT_REPORT.md` (no executable code in
this PR; the Gradle build contract is N/A because `apps/android/`
does not exist yet).

### Risks & rollback
See `docs/aci/reports/W01_ANDROID_AUDIT_REPORT.md` sections "Risks"
and "Rollback plan".

### Status
**Draft.** Not for merge. W02 (scaffold `apps/android`) is the next
sprint and will reference this audit.
```

---

## Open questions (non-blocking)

- Should the W02 scaffold use Hilt or a manual `AppContainer`? Pending
  product-team preference. Both layouts are accommodated by this audit.
- Should the gateway HTTP client be Ktor or Retrofit + OkHttp? Deferred
  to W04.
- Confirm repository scope: this audit targeted
  `echerd27-design/hermes-agent`. If the Android app instead lives in
  `A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent`, a re-audit may be
  needed against that repo.

---

## Validation commands

The reviewer can re-run these from the repo root to confirm the audit:

```bash
git fetch origin main
git diff --stat origin/main...HEAD     # should show only the four docs/aci files
ls apps/android 2>&1                   # should report "No such file or directory"
find . -name AndroidManifest.xml -not -path './node_modules/*'   # no output
find . -maxdepth 3 -name "*.gradle*" -not -path './node_modules/*'  # no output
git log --all --diff-filter=A --name-only --pretty=format: | grep '^apps/android'  # no output
```

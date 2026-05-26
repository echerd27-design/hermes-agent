# W01 Android Audit Report

**Sprint:** W01 — Audit existing Android app for Jarvis Prime command center
**Branch:** `aci/jarvis-prime-01-android-audit` (branched from `origin/main`)
**Author/agent:** Claude Code (Opus, plan-mode-approved)
**Audit date:** 2026-05-26

---

## Executive verdict

On `origin/main`, **no Android application exists**: no `apps/android/`,
no `AndroidManifest.xml`, no Gradle module, no `MainActivity`,
`HermesService`, `OrchestratorScreen`, settings, diagnostics, task
repository, app container, theme, or navigation graph.

Across **open feature branches** there is a partial **Kotlin-source
pre-scaffold**: at least five PRs add files under
`apps/android/app/src/main/java/com/aci/hermes/...` using sub-packages
`com.aci.hermes.{model.jarvis, model, ui.jarvis.chat, ui.jarvis.voice}`.
None of those branches commits a Gradle build, an Android manifest, an
Application class, a `MainActivity`, a nav graph, or theme resources —
so even if all in-flight PRs merged today, `./gradlew assembleDebug`
would still fail because there is no Gradle module to invoke.

W01 ships as a **documentation-only, reality-corrected audit** that
records: the on-`main` absence, the in-flight pre-scaffold (with a full
collision map), the design rules (no Python in APK; no
SMS/CallLog/always-on; no auto-notification prompt; mic only on tap),
and a sprint-by-sprint file ownership map calibrated to the existing
package layout (`com.aci.hermes` root, `jarvis` sub-namespace).

**No Android source code is created in W01.**

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
  (`cd apps/android && ./gradlew assembleDebug` and
  `cd apps/android && ./gradlew testDebugUnitTest`) cannot be exercised
  because `apps/android/` does not exist yet. These commands would fail
  with "No such file or directory" and are recorded as the W02
  acceptance contract instead.
- No Python tests are in scope: no Python files are modified.

The verification commands in `JARVIS_ANDROID_CURRENT_STATE_AUDIT.md`
are reproducible by any reviewer and will return identical output
until `apps/android/` is scaffolded in W02.

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| In-flight PRs (W05 models, W09 chat/voice, W10 job-models) merge without W02 scaffolding the Gradle module — leaving the repo with dead Kotlin source that does not compile. | High | W01 documents this gap explicitly. Recommendation: hold the in-flight Android PRs until W02 lands the Gradle scaffold, OR have W02 land first as a thin foundation. |
| `JarvisTask*` namespace collision: `aci/jarvis-prime-05-android-models` defines `com.aci.hermes.model.jarvis.JarvisTaskCard`, while `aci/wave-10-android-job-models` defines `com.aci.hermes.model.JarvisTask` (plus `JarvisTaskStatus`). Both surface "task" semantics in overlapping shapes. | High | W01 surfaces the conflict. The two PR authors must reconcile before either merges. Options: collapse into a single `com.aci.hermes.model.jarvis.*` package, or carve a `task` vs `job` separation. W08 (Tasks + Room) cannot start until this is resolved. |
| Future PRs (W02+) diverge from the ownership map and create overlapping edits to shared files (`AndroidManifest.xml`, nav graph, version catalog). | Medium | Each W02+ PR description must cite `JARVIS_ANDROID_FILE_OWNERSHIP_MAP.md` and list which shared files it touches. PR reviewers should reject PRs that edit shared files outside their sprint's allowed list. |
| The recommended stack (Compose + Material 3 + DataStore + Room + OkHttp/Ktor) becomes stale by the time W02 begins. | Low | W02 owns the version pin via `libs.versions.toml`. This audit is decision-neutral on exact versions. |
| DI strategy (Hilt vs manual `AppContainer`) is left to W02. | Low | Both layouts are covered in the ownership map. W02 selects one and updates the map in a follow-up if needed. |
| The sprint header references repo `A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent` but the active remote is `echerd27-design/hermes-agent`. | Medium | Recorded as an open question. User confirmed auditing the active remote. If the A-C-I org repo turns out to contain a buildable Android app, a follow-up W01b audit will be required. |
| Audit-topic overlap with `aci/wave-10-android-launch-audit` (which also documents "no Android app exists"). | Low | W01 covers the command-center implementation map (files, packages, ownership, integration order). W10 covers launch readiness (signing, Play Store, publishing). The two are complementary; W01 explicitly defers those topics to W10. |
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
branch can simply be deleted:
`git push origin --delete aci/jarvis-prime-01-android-audit`.

---

## Collision report

### Direct ALLOWED-FILES collision check

`git diff --name-only origin/main...<branch>` was run against every
`origin/aci/*` remote. **No other branch touches** any of the four
ALLOWED FILES:

- `docs/aci/android/JARVIS_ANDROID_CURRENT_STATE_AUDIT.md`
- `docs/aci/android/JARVIS_ANDROID_SCREEN_MAP.md`
- `docs/aci/android/JARVIS_ANDROID_FILE_OWNERSHIP_MAP.md`
- `docs/aci/reports/W01_ANDROID_AUDIT_REPORT.md`

### Topic-overlap report (concurrent Android work)

Five open PRs touch `apps/android/**` or `docs/aci/reports/` with
Android scope. None of them edits W01's ALLOWED FILES; each is recorded
here so W01's ownership map accurately accommodates them.

| Branch | Title | Scope | Conflicts with W01? |
|--------|-------|-------|---------------------|
| `aci/jarvis-prime-05-android-models` | W05: Add Android Jarvis Prime command-center models | 7 main + 7 test files under `com.aci.hermes.model.jarvis.*`; doc `W05_ANDROID_MODELS_REPORT.md` | No file-name collision. Affects W01's package recommendation (forced root `com.aci.hermes`). |
| `aci/wave-10-android-job-models` | feat(android): JARVIS job-state Kotlin models (Wave 10) | 6 main + 5 test files under `com.aci.hermes.model.*`; doc `W10_ANDROID_JOB_MODELS.md` | No file-name collision with W01. **`JarvisTask*` namespace collision with W05** — surfaced as a risk. |
| `aci/jarvis-prime-09-chat-voice-ui` | W09: Add Jarvis Prime chat and safe voice capture UI | 14 main + 3 test files under `com.aci.hermes.ui.jarvis.{chat,voice}.*`; doc `W09_CHAT_VOICE_UI_REPORT.md` | No file-name collision. `VoiceCaptureScreen` and `MicPermissionState` design is consistent with W01's permission rules. |
| `aci/wave-10-android-launch-audit` | docs(aci): W10 Android launch audit | 1 doc `W10_ANDROID_LAUNCH_AUDIT.md` | No file-name collision. Topic-adjacent audit; W01 defers launch-readiness topics (signing, Play Store) to W10. |
| `aci/wave-10-android-approval-screen-plan` | docs(aci): W10 plan — Android owner-approval screen (no code) | 1 doc `W10_ANDROID_APPROVAL_SCREEN_PLAN.md` | No file-name collision. W01 includes the `approvals` route in its forward-looking screen map, owned by W10. |

### Critical inter-PR conflict (not W01's to resolve, but surfaced)

`aci/jarvis-prime-05-android-models` and `aci/wave-10-android-job-models`
both introduce "task" models in adjacent packages. They must not both
merge as-is; the two PR authors / reviewers need to reconcile namespaces
before either merges. W01 records the conflict in
`JARVIS_ANDROID_CURRENT_STATE_AUDIT.md §"Critical inter-PR conflicts"`.

### Build blocker (not W01's to resolve, but surfaced)

No branch commits Gradle, manifest, Application class, or `MainActivity`.
None of the in-flight Kotlin files compile today. **W02 (scaffold)
should be considered a blocker for every other Android sprint.**

---

## Draft PR summary (copy-paste body for `mcp__github__create_pull_request`)

```
## W01: Audit existing Android app for Jarvis Prime command center

**Verdict:** No Android app exists on `origin/main`. Five open feature
branches pre-scaffold Kotlin source under
`apps/android/app/src/main/java/com/aci/hermes/...` but none commits a
Gradle build, manifest, Application class, or MainActivity — the project
is not yet buildable.

This PR ships a documentation-only, reality-corrected audit and lays
down a sprint-by-sprint file ownership map for W02 onward, aligned
with the existing `com.aci.hermes` package convention.

### What this PR adds
- `docs/aci/android/JARVIS_ANDROID_CURRENT_STATE_AUDIT.md` — verdict,
  verification commands, item-by-item findings, design rules (no Python
  in APK; no SMS/CallLog/always-on; no auto-notification prompt; mic
  only on tap), full in-flight PR collision report.
- `docs/aci/android/JARVIS_ANDROID_SCREEN_MAP.md` — target Compose
  screens (Orchestrator, Chat, Tasks, Diagnostics, Settings, Voice,
  Approvals, About) with routes, ViewModels, and permission triggers.
- `docs/aci/android/JARVIS_ANDROID_FILE_OWNERSHIP_MAP.md` — full
  greenfield tree under `apps/android/`, in-flight file inventory by
  branch, owning-PR per file, shared files and concurrency rules.
- `docs/aci/reports/W01_ANDROID_AUDIT_REPORT.md` — this report.

### Key findings (must read)
- **W02 (scaffold Gradle module) is a blocker.** No in-flight PR
  commits a build, so nothing compiles yet.
- **`JarvisTask*` namespace conflict** between
  `aci/jarvis-prime-05-android-models` and
  `aci/wave-10-android-job-models`. The two PR authors must reconcile
  before either merges.
- **Package root is locked to `com.aci.hermes`** (matches in-flight
  PRs). Jarvis-Prime command-center surfaces live under
  `com.aci.hermes.{ui.jarvis,model.jarvis}`.
- W01 deliberately overlaps in topic with `aci/wave-10-android-launch-audit`
  (also concludes "no app exists") and complements it: W01 covers the
  implementation map, W10 covers launch readiness.

### What this PR does NOT do
- Does not create or modify anything under `apps/android/**`.
- Does not modify `hermes_cli/**`, `skills/**`, `README.md`,
  `pyproject.toml`, `uv.lock`, `.github/**`, or any Gradle/package file.
- Does not deploy, publish, change DNS, alter credentials, or move
  money.

### Tests
None run. Rationale documented in this file (no executable code in this
PR; the Gradle build contract is N/A because `apps/android/` does not
exist yet).

### Risks & rollback
See sections "Risks" and "Rollback plan" in
`docs/aci/reports/W01_ANDROID_AUDIT_REPORT.md`.

### Status
**Draft.** Not for merge. W02 (scaffold `apps/android` Gradle module)
is the next sprint and will reference this audit.
```

---

## Open questions (non-blocking)

- DI choice (Hilt vs manual `AppContainer`) — **W02 decision.**
- Gateway HTTP client (Retrofit + OkHttp vs Ktor) — **W04 decision.**
- Persistence (Room vs DataStore-Proto for tasks) — **W08 decision.**
- Application class name (`HermesApplication` recommended; product
  branding via `<application android:label="Jarvis Prime">`) — **W02
  decision.**
- `JarvisTask*` namespace conflict between W05 and W10 — **cross-PR
  resolution required before either merges.**
- Confirm repository scope: this audit targeted
  `echerd27-design/hermes-agent`. If the Android app is also being
  developed in `A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent`, a
  re-audit may be needed against that repo.

---

## Validation commands

Reviewer can re-run these from the repo root after `git fetch origin`:

```bash
git diff --stat origin/main...HEAD                            # only the four docs/aci files
ls apps/android 2>&1                                          # "No such file or directory"
find . -name AndroidManifest.xml -not -path './node_modules/*'  # no output
find . -maxdepth 3 -name "*.gradle*" -not -path './node_modules/*'  # no output
git log --all --diff-filter=A --name-only --pretty=format: | grep '^apps/android' | head
# (lists in-flight pre-scaffold files; confirms none on main)

# Confirm no Gradle scaffold on any branch:
for b in $(git branch -r | grep -v HEAD); do
  git ls-tree -r "$b" --name-only 2>/dev/null \
    | grep -E "^apps/android/.*(build\.gradle|settings\.gradle|AndroidManifest\.xml|gradlew$|libs\.versions\.toml)"
done                                                          # no output
```

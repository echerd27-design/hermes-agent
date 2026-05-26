# W10 — Android JARVIS Job Models

## Mission

Add Android-side Kotlin data models for JARVIS job status — jobs, tasks,
lifecycle states, verification gates, owner-approval requests, and
verification evidence — so later waves (repository, view-models, UI,
networking) can compose against a shared domain vocabulary instead of
re-defining shapes per surface.

This wave is intentionally model-only. No UI, no networking, no
persistence, no dependency changes.

## Branch and scope

- Branch: `aci/wave-10-android-job-models`.
- Allowed paths touched:
  - `apps/android/app/src/main/java/com/aci/hermes/model/**`
  - `apps/android/app/src/test/**`
  - `docs/aci/reports/W10_ANDROID_JOB_MODELS.md` (this file)
- Forbidden paths confirmed untouched: any UI under
  `com/aci/hermes/ui/**`, any `build.gradle.kts` (app or project),
  `pyproject.toml`, `uv.lock`, `README.md`.

## Files added

### Models — `apps/android/app/src/main/java/com/aci/hermes/model/`

| File | Shape |
| ---- | ----- |
| `JarvisJob.kt` | `data class JarvisJob` + `enum JarvisJobMode` (6 modes) |
| `JarvisTask.kt` | `data class JarvisTask` |
| `JarvisTaskStatus.kt` | `enum JarvisTaskStatus` (9 states) |
| `JarvisGateStatus.kt` | `data class JarvisGateStatus` + `enum JarvisGate` (8 gates) + `enum JarvisGateResult` (5 results) |
| `OwnerApprovalRequest.kt` | `data class OwnerApprovalRequest` + `enum OwnerApprovalReason` (12 reasons) + `enum OwnerApprovalStatus` (4 statuses) |
| `VerificationEvidence.kt` | `data class VerificationEvidence` + `enum VerificationEvidenceType` (8 types) |

### Tests — `apps/android/app/src/test/java/com/aci/hermes/model/`

| File | Coverage |
| ---- | -------- |
| `JarvisJobTest.kt` | defaults, `copy()`, equality, mode enum distinctness |
| `JarvisTaskTest.kt` | default empty lists, attach gates / evidence via copy, status enum completeness |
| `JarvisGateStatusTest.kt` | 8-gate completeness, 5-result completeness, null defaults, equality by result |
| `OwnerApprovalRequestTest.kt` | default `PENDING`, resolution copy, owner-gate enum completeness, `EXPIRED` presence |
| `VerificationEvidenceTest.kt` | `verified=false` default, verified-copy semantics, type enum completeness |

### Wave report

- `docs/aci/reports/W10_ANDROID_JOB_MODELS.md` (this file).

## Design notes

- **No serialization annotations.** The acceptance criterion specifies
  "Kotlin serialization compatible if project already uses it." The
  Android project skeleton does not exist yet (see "Remaining risks"),
  so no serialization library is declared. Models are pure-Kotlin data
  classes that can be annotated `@Serializable` (kotlinx) or
  `@JsonClass` (Moshi) by a future wave without changing field shapes.
- **No third-party imports.** Files import only stdlib types (`String`,
  `Long`, `Boolean`, `List`) and JUnit 4 (`org.junit.Test`,
  `org.junit.Assert.*`) in tests.
- **Timestamps are `Long` epoch milliseconds** instead of `java.time.*`
  or `kotlinx-datetime` to avoid pulling in a dep or making API-level
  assumptions ahead of the skeleton wave.
- **Enum vocabularies are sourced from existing docs** to keep the
  Android surface consistent with the operating-layer semantics:
  - `JarvisJobMode` — `docs/jarvis-prime-operating-system.md` §Modes.
  - `JarvisGate` — `docs/jarvis-verification-gates.md` §gate sections
    (Planning, Build, Review, Test, Security, Release, Owner Approval,
    Rollback).
  - `JarvisGateResult` — the doc's "pass, fail, or require owner
    approval" plus `SKIPPED` (explicitly allowed) and `PENDING`
    (not-yet-checked).
  - `OwnerApprovalReason` — union of owner-gated actions named in
    `docs/jarvis-prime-operating-system.md` §Owner Gates,
    `docs/jarvis-verification-gates.md` §Owner Approval Gate, and
    `docs/mobile-voice-development-workflow.md` §Owner Gates in Mobile
    Mode.

## Tests run

**None executed.** The stated VERIFY commands could not run on this
branch alone:

- `cd apps/android && ./gradlew testDebugUnitTest` — no `gradlew`
  wrapper, no `apps/android/app/build.gradle.kts`, no project-level
  `apps/android/build.gradle.kts`, no `settings.gradle.kts`.
- `cd apps/android && ./gradlew assembleDebug` — same root cause.

Pre-PR sanity checks that **were** run (results to be recorded at
commit time):

- `git diff --check` (whitespace and conflict-marker sanity).
- `grep -RIn 'TODO\|FIXME\|XXX' apps/android/app/src/` (expected empty
  in new files).
- `grep -RIn '@Serializable\|@JsonClass\|import kotlinx\|import com.squareup' apps/android/app/src/`
  (expected empty — confirms no serialization-lib references).
- `find apps/android docs/aci -type f | sort` (confirms only files
  inside the ALLOWED list were created).

## Remaining risks

1. **Blocker for VERIFY commands — Android skeleton missing.** The
   stated `./gradlew testDebugUnitTest` and `./gradlew assembleDebug`
   commands cannot pass until a separate wave creates the Android
   module skeleton. Per the NON-OVERLAP CONTRACT ("If you discover a
   required change outside allowed files, stop and write it in the
   wave report instead of editing it"), no skeleton files were added
   here. A subsequent wave must add:
   - `apps/android/settings.gradle.kts`
   - `apps/android/build.gradle.kts`
   - `apps/android/app/build.gradle.kts` (Android Gradle Plugin, Kotlin
     plugin, `testImplementation 'junit:junit:4.13.2'`)
   - `apps/android/gradle.properties`
   - `apps/android/gradle/wrapper/gradle-wrapper.properties`,
     `gradle-wrapper.jar`, `gradlew`, `gradlew.bat`
   - `apps/android/app/src/main/AndroidManifest.xml`
2. **Serialization deferral.** When a future wave picks
   `kotlinx.serialization` or Moshi, every data class can be annotated
   without shape changes; no migration is needed inside this wave.
3. **No runtime exercise.** Because no app skeleton exists, these
   models have not been instantiated by anything. Their JUnit 4 tests
   exercise data-class semantics and enum completeness but cannot run
   in CI until the skeleton wave lands.

## Rollback plan

The wave only adds new files; it edits none. To roll back fully:

```bash
rm -rf apps/android
rm -f docs/aci/reports/W10_ANDROID_JOB_MODELS.md
rmdir docs/aci/reports docs/aci 2>/dev/null || true
git checkout main -- .
```

Alternatively, revert the wave's single commit on the branch.

## PR summary (ready to paste)

> **Wave 10 — Android JARVIS job models.**
>
> Adds pure-Kotlin data classes and enums describing JARVIS jobs, tasks,
> task lifecycle, verification gates, owner-approval requests, and
> verification evidence under
> `apps/android/app/src/main/java/com/aci/hermes/model/`, plus JUnit 4
> unit tests under `apps/android/app/src/test/java/com/aci/hermes/model/`.
>
> No UI changes, no networking, no dependency changes, no serialization
> annotations. Forward-compatible with `kotlinx.serialization` or Moshi.
>
> **Tests not run:** `./gradlew testDebugUnitTest` and
> `./gradlew assembleDebug` cannot execute on this branch because the
> Android module skeleton (`build.gradle.kts`, wrapper, manifest) is
> not yet in the repo. A subsequent wave will add that skeleton; see
> "Remaining risks" in the wave report for the full file list.
>
> **Rollback:** delete `apps/android/` and the wave report file.
>
> Draft PR — not for merge.

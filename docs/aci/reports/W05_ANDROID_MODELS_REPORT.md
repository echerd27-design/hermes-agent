# W05 — Android Jarvis Prime Command-Center Models

## Mission

Add Android-side Kotlin data models for the Jarvis Prime command-center
surface — presence state, risk tier, task cards, approval cards, proof
records, memory records, and an event DTO — so later waves (gateway
client, repository, view-models, UI) can compose against a shared
domain vocabulary instead of redefining shapes per surface.

This wave is **model-only**. No UI, no networking, no persistence, no
dependency changes. The Android body is the Jarvis Prime control
surface; the brain stays in the Hermes/Jarvis backend.

## Branch and scope

- **Branch:** `aci/jarvis-prime-05-android-models` (created from
  `origin/main` @ `7b82077`).
- **PR:** opened as a draft titled `W05: Add Android Jarvis Prime
  command-center models`.
- **ALLOWED paths touched:**
  - `apps/android/app/src/main/java/com/aci/hermes/model/jarvis/**`
  - `apps/android/app/src/test/java/com/aci/hermes/model/jarvis/**`
  - `docs/aci/reports/W05_ANDROID_MODELS_REPORT.md` (this file)
- **FORBIDDEN paths confirmed untouched:**
  - `apps/android/app/src/main/java/com/aci/hermes/MainActivity.kt` —
    does not exist on `origin/main`; not created.
  - `apps/android/app/src/main/java/com/aci/hermes/ui/**` — none added.
  - `apps/android/AndroidManifest.xml` — none added.
  - `hermes_cli/**`, `skills/**`, `README.md`, `pyproject.toml`,
    `uv.lock`, `.github/**`, any Gradle file — none modified.

## Files added

### Production models — `apps/android/app/src/main/java/com/aci/hermes/model/jarvis/`

Package: `com.aci.hermes.model.jarvis`. No imports beyond Kotlin
stdlib. No serialization annotations.

| File | Shape |
| ---- | ----- |
| `JarvisPresenceState.kt` | `enum class JarvisPresenceState` (12 entries: `IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `WORKING`, `WAITING_FOR_APPROVAL`, `SERIOUS_ACTION_PENDING`, `CRITICAL_ACTION_PENDING`, `BLOCKED`, `WARNING`, `COMPLETE`, `OFFLINE`). |
| `JarvisRiskTier.kt` | `enum class JarvisRiskTier { NORMAL, SERIOUS, CRITICAL }`. |
| `JarvisTaskCard.kt` | `data class JarvisTaskCard` — id, title, summary, phase (String), riskTier, workerLabel, createdAtEpochMs, updatedAtEpochMs, nullable blockedReason / proofId, rollbackAvailable Boolean (default false). |
| `JarvisApprovalCard.kt` | `data class JarvisApprovalCard` (id, title, action, riskTier, impactSummary, rollbackSummary, requiresSecondConfirm / requiresExactPhrase Booleans default false, status default `PENDING`) + co-located `enum class JarvisApprovalStatus { PENDING, APPROVED, REJECTED, EXPIRED }`. |
| `JarvisProofRecord.kt` | `data class JarvisProofRecord` — id, taskId, action, evidenceSummary, timestampEpochMs, filesChanged / testsRun `List<String>` (default empty). |
| `JarvisMemoryRecord.kt` | `data class JarvisMemoryRecord` — id, title, summary, source, confidence (Double), editable / removable Booleans (default true). |
| `JarvisEventDto.kt` | `data class JarvisEventDto` — eventType, timestampEpochMs, message, payloadSummary, nullable taskId (default `null`). |

### Tests — `apps/android/app/src/test/java/com/aci/hermes/model/jarvis/`

JUnit 4 (`org.junit.Test`, `org.junit.Assert.*`). One test file per
production model. Each test file uses a private `sampleXxx()` builder
where helpful, mirroring the convention established in
`aci/wave-10-android-job-models`.

| File | Coverage |
| ---- | -------- |
| `JarvisPresenceStateTest.kt` | All 12 entries present, `values().size == 12`, set-equality with the expected set, `valueOf("IDLE")` round-trip, unknown name throws, entries distinct. |
| `JarvisRiskTierTest.kt` | 3 entries present, ordinal order `NORMAL < SERIOUS < CRITICAL`, `valueOf` round-trip. |
| `JarvisTaskCardTest.kt` | Default `blockedReason` and `proofId` are `null`, default `rollbackAvailable` is `false`; `copy()` preserves unedited fields; equality / `hashCode` contract; `riskTier` round-trip through `copy`; `blockedReason` and `proofId` persist when set. |
| `JarvisApprovalCardTest.kt` | Default `status == PENDING`, default confirm flags `false`; `copy(status = APPROVED)` transitions status without mutating the original; `JarvisApprovalStatus.values()` has 4 entries; equality. |
| `JarvisProofRecordTest.kt` | Default `filesChanged` / `testsRun` empty; populated lists preserve order through `copy`; equality. |
| `JarvisMemoryRecordTest.kt` | Default `editable` / `removable` true; `confidence` accepts boundary values 0.0 and 1.0 without exception; `copy` can flip editability; equality. |
| `JarvisEventDtoTest.kt` | Default `taskId` is `null`; `copy(taskId = ...)` populates without mutating original; equality. |

### Wave report

- `docs/aci/reports/W05_ANDROID_MODELS_REPORT.md` (this file).

## Design notes

- **Package convention.** All W05 models live in
  `com.aci.hermes.model.jarvis` (sub-package of W10's
  `com.aci.hermes.model`). The split keeps the command-center surface
  (cards, presence, events) physically separate from the job/task
  lifecycle vocabulary added by W10, and matches the allowed-files
  scope of this wave.
- **No serialization annotations.** Sprint rules forbid dependency
  changes, and `origin/main` carries no Kotlin module skeleton (no
  Gradle files declaring any serialization plugin). Models are pure-
  Kotlin data classes that a later wave can annotate with
  `@Serializable` (kotlinx) or `@JsonClass` (Moshi) without changing
  field shapes.
- **No third-party imports.** Files import only Kotlin stdlib types
  (`String`, `Long`, `Boolean`, `Double`, `List`) in production and
  JUnit 4 in tests.
- **Timestamps are `Long` epoch milliseconds**, with field-name suffix
  `EpochMs`. The sprint spec lists field names `createdAt`,
  `updatedAt`, `timestamp` without a type; we use the
  W10-consistent `*EpochMs` suffix to avoid pulling in
  `java.time.*` or `kotlinx-datetime` and to keep field names self-
  documenting alongside the W10 models.
- **`phase` is `String`.** The W05 spec lists `phase` but does not
  enumerate values. We keep it server-driven (`String`) so the
  command-center surface can render whatever the backend reports.
- **`confidence` is `Double`** (typical `0.0..1.0` range), not
  enforced at type level. Matches W10's "no value-validation in
  models" stance — validation belongs in a future view-model layer.
- **Booleans have safe defaults.** `rollbackAvailable`,
  `requiresSecondConfirm`, `requiresExactPhrase` default `false`
  (safer for risky actions). `editable`, `removable` default `true`
  (memory records are user-editable unless the brain explicitly locks
  them).
- **Nullable fields default to `null`.** `blockedReason`, `proofId`,
  `taskId` are `String?` with default `null`, matching W10's
  convention.
- **Enums declared `enum class`, all-caps entries.** Only
  `JarvisApprovalStatus` is co-located inside its data class file
  (`JarvisApprovalCard.kt`), mirroring W10's
  `OwnerApprovalRequest.kt` / `OwnerApprovalStatus` pattern.

## Conceptual overlap with `aci/wave-10-android-job-models`

W10 adds job/task lifecycle models at
`apps/android/app/src/main/java/com/aci/hermes/model/*.kt` (flat
`com.aci.hermes.model` package). W05 adds command-center cards under
`com.aci.hermes.model.jarvis`. The two waves share zero file paths and
zero filenames — they are sibling vocabularies:

| W10 (job lifecycle) | W05 (command-center surface) |
| ------------------- | ---------------------------- |
| `JarvisJob`, `JarvisTask`, `JarvisTaskStatus`, `JarvisGateStatus`, `OwnerApprovalRequest`, `VerificationEvidence` | `JarvisTaskCard`, `JarvisApprovalCard`, `JarvisPresenceState`, `JarvisRiskTier`, `JarvisProofRecord`, `JarvisMemoryRecord`, `JarvisEventDto` |

Merge order does not matter: each branch can land independently. A
future wave will likely unify them (e.g., have `JarvisTaskCard` carry
a `JarvisTask` reference, have `JarvisApprovalCard` carry an
`OwnerApprovalRequest` id), but that integration is deliberately
out-of-scope for both W05 and W10.

## Tests run

**`./gradlew assembleDebug` and `./gradlew testDebugUnitTest` were not
executed.** Same root cause documented in
`docs/aci/reports/W10_ANDROID_JOB_MODELS.md`: the Android module
skeleton does not exist on `origin/main`. There is no `gradlew`
wrapper, no `apps/android/settings.gradle.kts`, no
`apps/android/app/build.gradle.kts`, and no
`apps/android/app/src/main/AndroidManifest.xml`. Per the NON-OVERLAP
CONTRACT, none of those files are added here — they are FORBIDDEN
for W05 and were already filed as a follow-up wave by W10.

A subsequent wave (call it `aci/wave-XX-android-module-skeleton`)
must add:

- `apps/android/settings.gradle.kts`
- `apps/android/build.gradle.kts`
- `apps/android/app/build.gradle.kts` (Android Gradle Plugin, Kotlin
  plugin, `testImplementation 'junit:junit:4.13.2'`)
- `apps/android/gradle.properties`
- `apps/android/gradle/wrapper/gradle-wrapper.properties`,
  `gradle-wrapper.jar`, `gradlew`, `gradlew.bat`
- `apps/android/app/src/main/AndroidManifest.xml`

Once that wave lands, both W05 and W10 models become buildable and
unit-testable without changes.

### Pre-PR sanity checks that did run

| Check | Result |
| ----- | ------ |
| `git diff --check` | clean — no whitespace / conflict markers. |
| `grep -RIn 'TODO\|FIXME\|XXX' apps/android/app/src/main/java/com/aci/hermes/model/jarvis apps/android/app/src/test/java/com/aci/hermes/model/jarvis` | empty. |
| `grep -RIn '@Serializable\|@JsonClass\|import kotlinx\|import com.squareup' apps/android/app/src/main/java/com/aci/hermes/model/jarvis apps/android/app/src/test/java/com/aci/hermes/model/jarvis` | empty — confirms no serialization-lib references. |
| `git diff --stat origin/main` | only ALLOWED paths changed (see "Changed files" below). |
| Scope confirmation: `find apps/android docs/aci -type f` | only files under the ALLOWED list. |

## Changed files

```
apps/android/app/src/main/java/com/aci/hermes/model/jarvis/JarvisApprovalCard.kt
apps/android/app/src/main/java/com/aci/hermes/model/jarvis/JarvisEventDto.kt
apps/android/app/src/main/java/com/aci/hermes/model/jarvis/JarvisMemoryRecord.kt
apps/android/app/src/main/java/com/aci/hermes/model/jarvis/JarvisPresenceState.kt
apps/android/app/src/main/java/com/aci/hermes/model/jarvis/JarvisProofRecord.kt
apps/android/app/src/main/java/com/aci/hermes/model/jarvis/JarvisRiskTier.kt
apps/android/app/src/main/java/com/aci/hermes/model/jarvis/JarvisTaskCard.kt
apps/android/app/src/test/java/com/aci/hermes/model/jarvis/JarvisApprovalCardTest.kt
apps/android/app/src/test/java/com/aci/hermes/model/jarvis/JarvisEventDtoTest.kt
apps/android/app/src/test/java/com/aci/hermes/model/jarvis/JarvisMemoryRecordTest.kt
apps/android/app/src/test/java/com/aci/hermes/model/jarvis/JarvisPresenceStateTest.kt
apps/android/app/src/test/java/com/aci/hermes/model/jarvis/JarvisProofRecordTest.kt
apps/android/app/src/test/java/com/aci/hermes/model/jarvis/JarvisRiskTierTest.kt
apps/android/app/src/test/java/com/aci/hermes/model/jarvis/JarvisTaskCardTest.kt
docs/aci/reports/W05_ANDROID_MODELS_REPORT.md
```

## Risks

1. **Build verification deferred.** Until the module-skeleton wave
   lands, no automated check confirms that these files compile or
   that the tests pass. Mitigation: files are small, mechanical, and
   match W10's already-reviewed Kotlin conventions; manual review of
   syntax is straightforward.
2. **`*EpochMs` field-name suffix differs from the sprint spec
   verbatim.** Spec lists `createdAt` / `updatedAt` / `timestamp`. We
   chose the suffixed form to match W10 and to be self-documenting
   about units (ms vs s). If reviewers prefer the verbatim names, a
   trivial rename can be applied before the module-skeleton wave
   exercises the code.
3. **No dependency on W10 at the Kotlin level.** If both waves merge,
   `JarvisTaskCard` will not transitively know about
   `JarvisJob`/`JarvisTask`; a later integration wave is expected to
   add references (or a single unified vocabulary) once the lifecycle
   semantics stabilize.

## Rollback

Purely additive wave. To roll back:

```
git rm -r apps/android/app/src/main/java/com/aci/hermes/model/jarvis \
          apps/android/app/src/test/java/com/aci/hermes/model/jarvis \
          docs/aci/reports/W05_ANDROID_MODELS_REPORT.md
git commit -m "Revert W05 Android command-center models"
```

No other paths are touched, so removal restores the prior tree
exactly.

## Draft PR summary

> Adds Kotlin data models for the Android Jarvis Prime command-center
> surface (presence state, risk tier, task / approval cards, proof and
> memory records, event DTO) plus JUnit 4 tests. Model-only, no UI,
> manifest, Gradle, or dependency changes. Tests not executed because
> the Android module skeleton is not yet on `main`; this wave inherits
> the same blocker W10 already filed.

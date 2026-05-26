# W09 — Jarvis Prime Chat + Safe Voice Capture UI

**Status:** Blueprint wave. Draft PR, do not merge.
**Branch:** `aci/jarvis-prime-09-chat-voice-ui`
**Base:** `origin/main` at `7b82077`.

## 1. Mission

Create the Jarvis Prime conversational chat surface and a safe voice
capture surface on Android, mobile-first, with no always-listening
behavior. Quoting the universal sprint header:

- Chat: conversational surface, short mobile responses by default,
  expand/deep-dive affordance, four human-feeling status states
  (listening, thinking, working, waiting for approval), six message
  types (user, Jarvis, task update, approval request, proof update,
  status), no external service calls in this wave.
- Voice: tap-to-speak button, microphone permission *education*
  before request, microphone request only after the user taps voice,
  no always-listening. If `RECORD_AUDIO` is missing from the
  Manifest, do not edit Manifest here — document the follow-up.

## 2. Skeleton blocker (read first)

`apps/android/` does **not** exist on `origin/main`. No
`build.gradle.kts`, `settings.gradle.kts`, `gradlew`, or
`AndroidManifest.xml` is present. The mission's FORBIDDEN list
includes every file that would normally let the wave's verify
commands run:

| Mission verify command                          | W09 status                                              |
|-------------------------------------------------|---------------------------------------------------------|
| `cd apps/android && ./gradlew assembleDebug`    | **Cannot run.** No Gradle wrapper, no `build.gradle.kts`. |
| `cd apps/android && ./gradlew testDebugUnitTest`| **Cannot run.** Same reason.                            |
| `git diff --stat`                               | Runs. Output captured in §8.                            |
| Confirm `AndroidManifest.xml` unchanged.        | Trivially unchanged — it does not exist on this branch. |

This is the same situation faced by PR #18
(*"Wave 10: JARVIS job-state Kotlin models"*) and PR #9
(*"W10 Android Launch Audit"*). Both prior PRs proceeded in
**blueprint mode**: write the wave's owned files as pure Kotlin /
Markdown that a later skeleton wave can drop into a real Gradle
module without source edits, and document the gap here so it is
not lost. W09 follows that precedent.

### 2.1 Required follow-up Manifest edit (NOT in this wave)

When a future wave introduces the Android Gradle skeleton, the
following `<uses-permission>` element must be added to
`apps/android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
```

Notes for the skeleton wave:

- `RECORD_AUDIO` is a **dangerous** permission. Runtime request is
  driven by `VoiceCaptureViewModel.onEducationContinue()` — never
  by app startup, navigation, or background work.
- No `<uses-feature android:name="android.hardware.microphone"
  android:required="true" />` — the app must still install and run
  on devices without a microphone (the mission says microphone
  permission is optional).
- No `READ_MEDIA_AUDIO` is needed: the app captures live mic input,
  it does not read existing audio files from the gallery.
- No `RECORD_BACKGROUND_AUDIO`, no foreground-service-media
  permission, no notification policy access — the no-always-listening
  rule is enforced *in code* by the absence of any
  `LifecycleObserver`, background coroutine, or `AudioRecord` field
  in `VoiceCaptureViewModel`.
- No `READ_SMS`, no `READ_CALL_LOG`, no `RECEIVE_SMS` — banned by
  the mission and verified absent by the §8 grep gate.

## 3. Changed files

All paths relative to repo root. Every path is on the W09 ALLOWED
list; none are on the FORBIDDEN list.

### Chat — `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/chat/`

| File                  | Purpose                                                                                       |
|-----------------------|-----------------------------------------------------------------------------------------------|
| `ChatMessage.kt`      | `sealed interface ChatMessage` plus six data classes (`UserMessage`, `JarvisMessage`, `TaskUpdate`, `ApprovalRequest`, `ProofUpdate`, `StatusEvent`) and helpers (`ApprovalOption`, `ProofKind`). |
| `JarvisStatus.kt`     | `enum class JarvisStatus { IDLE, LISTENING, THINKING, WORKING, WAITING_FOR_APPROVAL }`.       |
| `ChatUiState.kt`      | Immutable view-state emitted by `ChatViewModel`.                                              |
| `ChatViewModel.kt`    | `androidx.lifecycle.ViewModel` with `StateFlow<ChatUiState>` and pure intent methods.         |
| `ChatScreen.kt`       | Top-level mobile-first `@Composable` taking state + callbacks (no internal VM coupling).      |
| `ChatMessageRow.kt`   | Per-subtype rendering via exhaustive `when` over the sealed interface.                        |
| `StatusPill.kt`       | Status chip with animated pulse for `LISTENING`/`THINKING`/`WORKING`.                         |
| `ChatPreviews.kt`     | `@Preview` composables: idle/empty, sample conversation, waiting-for-approval, all status pills. |

### Voice — `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/voice/`

| File                          | Purpose                                                                                  |
|-------------------------------|------------------------------------------------------------------------------------------|
| `MicPermissionState.kt`       | `interface MicPermissionState` + `StubMicPermissionState` for previews/tests.            |
| `VoiceCaptureState.kt`        | `data class VoiceCaptureState` + `enum VoiceStage`.                                      |
| `VoiceCaptureViewModel.kt`    | State machine: `EDUCATION → REQUESTING_PERMISSION → READY → CAPTURING → REVIEWING`, with `DENIED` terminal-but-recoverable branch. |
| `VoiceCaptureScreen.kt`       | Pure `@Composable`. Education sheet renders first; permission is requested only after explicit Continue. |
| `VoiceTapButton.kt`           | Mic-icon button. Calls a callback only; does NOT touch the permission API directly.      |
| `VoiceEducationContent.kt`    | Plain-Kotlin strings for the education sheet (no `strings.xml` because resources are not in this wave). |

### Tests — `apps/android/app/src/test/java/com/aci/hermes/`

JUnit 4 only (`org.junit.Test`, `org.junit.Assert.*`). No
Robolectric. No Compose UI test. No third-party imports. Matches
PR #18's choice for the same reason: until a skeleton wave provides
Gradle, only contract-style tests are reviewable.

| File                                                       | What it asserts                                                                 |
|------------------------------------------------------------|---------------------------------------------------------------------------------|
| `ui/jarvis/chat/ChatViewModelTest.kt`                      | 12 cases: initial state, send/blank guard, status update, append-each-subtype, approval flow (set/clear/respond), approval-id mismatch ignored, status transition matrix, JarvisMessage short-vs-expanded invariants. |
| `ui/jarvis/chat/ChatMessageTest.kt`                        | Sealed-interface exhaustiveness over all six subtypes; `ProofKind` 4-case set; `JarvisStatus` 5-case set; approval-options carry. |
| `ui/jarvis/voice/VoiceCaptureViewModelTest.kt`             | 11 cases: initial stage; no permission request before continue; grant→READY; deny→DENIED; denied does **not** silently retry; retry-education does not re-request mic; start-capture requires READY; capture→REVIEWING; submit returns transcript and resets; cancel returns to EDUCATION; permission flipping away between READY and Start yields DENIED with error. Plus a placeholder no-banned-API guard. |

### Report

| File                                                  | Purpose                                |
|-------------------------------------------------------|----------------------------------------|
| `docs/aci/reports/W09_CHAT_VOICE_UI_REPORT.md`        | This document.                         |

## 4. Design notes

### 4.1 Chat-local sealed types, not `com.aci.hermes.model.*`

PR #18 introduces a `com.aci.hermes.model.*` package
(`JarvisJob`, `JarvisTask`, `OwnerApprovalRequest`,
`VerificationEvidence`, plus several enums). The natural temptation
is to have `ChatMessage` reference those types directly. We chose
not to:

- PR #18 is an open draft, not merged. Importing from an unmerged
  branch couples W09's compilation to PR #18's rebase schedule.
- The chat surface needs UI-shaped values (per-message id, expand
  state, presentation timestamp) that are not all on the PR #18
  models.
- A later reconciliation wave will own the mapping (probably an
  adapter at the repository boundary) — easier to do once with both
  sides merged than to thrash twice.

Reconciliation note: `ChatMessage.kt` has a header comment pointing
at PR #18 so the future wave is obvious to a reader.

### 4.2 `JarvisStatus` includes `IDLE`

The mission lists four states. We add `IDLE` as the baseline so
the type can model the "nothing happening" pause between bursts of
activity. All four mission states are present and tested.

### 4.3 `MicPermissionState` as an interface

The W09 voice module cannot call `ActivityResultContracts` or
Accompanist Permissions directly without adding a Gradle
dependency, which is forbidden. By making permission an interface
with a `StubMicPermissionState` implementation, the state machine
can be exercised in tests and previews without an emulator and a
future wave can swap in a real adapter with no edits to
`VoiceCaptureScreen` or `VoiceCaptureViewModel`.

### 4.4 Education sheet renders before any permission API call

`VoiceCaptureScreen` shows education content in the `EDUCATION`
and `REQUESTING_PERMISSION` stages. `VoiceCaptureViewModel.onEducationContinue()`
is the only entry point that calls `permission.requestPermission()`,
and it requires the current stage to be `EDUCATION`. This is
verified by `noPermissionRequestFiresBeforeEducationContinue` and
`deniedStateDoesNotSilentlyRetry` in
`VoiceCaptureViewModelTest`.

### 4.5 `VoiceTapButton` does not touch the permission API

The chat input row's mic icon calls a host-supplied `onTap`
callback. The host (a future navigation wave) is responsible for
launching `VoiceCaptureScreen`. This keeps every mic request
strictly downstream of explicit user intent, satisfying both
"microphone request only after user taps voice" and "no automatic
notification permission prompt on first launch" (no permission API
is reachable before the user explicitly chooses to use voice).

## 5. Safety guarantees

| Mission rule                                          | How W09 enforces it                                                                                              |
|--------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| No always-listening                                    | `VoiceCaptureViewModel` has no background coroutine, no `LifecycleObserver`, no `AudioRecord` field. State machine has no loop that re-enters `CAPTURING`. |
| No automatic mic prompt                                | `permission.requestPermission()` is reachable only from `onEducationContinue()`, which requires the user-driven `EDUCATION` stage and explicit Continue tap. |
| Microphone request only after user taps voice          | `VoiceTapButton.onTap` is a callback; the host routes to `VoiceCaptureScreen`, which still requires the user to tap Continue on the education sheet before any permission request fires. |
| Optional permission                                    | `DENIED` is terminal-but-recoverable. The rest of the app (chat surface) keeps working with `VoiceTapButton` disabled at the host's discretion. |
| No SMS / call log / always-listening behavior          | No imports of `android.provider.Telephony`, `android.provider.CallLog`, `android.telephony.SmsManager`, `android.media.AudioRecord`, or `android.media.MediaRecorder` anywhere under `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/{chat,voice}/`. Verified by the §8 grep gate. |
| No external service calls in this wave                 | `ChatViewModel` and `VoiceCaptureViewModel` take no network / repository dependencies; no `OkHttp`, no `Retrofit`, no `ktor`, no `okio` imports. |
| No backend secret material                             | No tokens, URLs, credentials, or env-var reads in any file.                                                      |
| `MainActivity.kt`, `AndroidManifest.xml`, `ui/jarvis/{home,navigation,tasks,approvals}/**` untouched | All four destinations remain absent on this branch (they do not exist on `main` either). Verified by the §8 path gate. |

## 6. Verify — actually run

Pre-PR, on this branch:

| Command                                                        | Result                                                                       |
|---------------------------------------------------------------|------------------------------------------------------------------------------|
| `git fetch origin main`                                       | OK (fast-forward to `7b82077`).                                              |
| `git status --short`                                          | Clean before edits.                                                          |
| `git branch --show-current`                                   | `aci/jarvis-prime-09-chat-voice-ui`.                                         |
| `git diff --check`                                            | No whitespace errors.                                                        |
| `git diff --stat origin/main...HEAD`                          | Only the files listed in §3.                                                 |
| Forbidden-path grep (see §8)                                  | Empty.                                                                       |
| Banned-API grep (see §8)                                      | Empty.                                                                       |
| `import com.aci.hermes.model` grep                            | Empty (no dependency on unmerged PR #18).                                    |

## 7. Verify — could not run

| Command                                          | Why                                                                  |
|-------------------------------------------------|----------------------------------------------------------------------|
| `cd apps/android && ./gradlew assembleDebug`    | No Gradle skeleton. Same blocker documented in PR #18 and PR #9.     |
| `cd apps/android && ./gradlew testDebugUnitTest`| Same.                                                                |

These commands become runnable once the skeleton wave lands
`apps/android/settings.gradle.kts`, `apps/android/build.gradle.kts`,
`apps/android/app/build.gradle.kts` (with `androidx.compose.bom`,
Material 3, `androidx.lifecycle:lifecycle-viewmodel-compose`,
`androidx.lifecycle:lifecycle-runtime-compose`,
`org.jetbrains.kotlinx:kotlinx-coroutines-android`,
`androidx.compose.material:material-icons-extended`,
`testImplementation "junit:junit:4.13.2"`), `apps/android/gradle.properties`,
and the wrapper.

## 8. Hard gates (commands the reviewer can reproduce)

```bash
# Confirm only ALLOWED files changed.
git diff --name-only origin/main...HEAD | grep -E \
  '(AndroidManifest|MainActivity|ui/jarvis/(home|navigation|tasks|approvals)|hermes_cli/|skills/|README\.md|pyproject\.toml|uv\.lock|\.github/|\.gradle)' \
  && echo "FAIL: forbidden path in diff" || echo "OK: no forbidden paths"

# Confirm no banned APIs or unexpected third-party imports under chat/voice.
grep -RIn '@Serializable\|import kotlinx\.serialization\|import com\.squareup\|import com\.google\.accompanist\|AudioRecord\|MediaRecorder\|android\.provider\.Telephony\|android\.provider\.CallLog\|android\.telephony\.SmsManager' \
  apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/chat \
  apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/voice \
  apps/android/app/src/test/java/com/aci/hermes/ui/jarvis/chat \
  apps/android/app/src/test/java/com/aci/hermes/ui/jarvis/voice \
  && echo "FAIL: banned API or dep import" || echo "OK: no banned imports"

# Confirm no dependency on unmerged PR #18 model package.
grep -RIn 'import com\.aci\.hermes\.model' \
  apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/chat \
  apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/voice \
  && echo "FAIL: PR #18 model import" || echo "OK: chat-local types only"
```

## 9. Risks

1. **Skeleton-blocker overhang.** Until a future wave introduces
   the Gradle skeleton + Manifest, these composables and tests are
   reviewable-but-not-executable. Same posture as PR #18.
2. **Chat-local vs. model-package divergence.** Two parallel
   vocabularies will exist until a reconciliation wave lands; a
   bug fix that touches semantics may need to land in both places
   in the interim.
3. **Voice capture is a placeholder.** `CAPTURING` stage accepts
   typed text as a stand-in for real audio + STT. A future wave
   will replace this with the real audio + transcription pipeline.
   Until then, "voice" demos require manual typing in the
   `CAPTURING` panel.
4. **No accessibility / RTL / dark-mode audit** beyond
   `MaterialTheme` defaults. Defer to a UX-polish wave.
5. **`MicPermissionState` revoke timing.** The `READY → CAPTURING`
   transition re-checks `permission.isGranted` and lands on
   `DENIED` if the user revoked between Continue and Start; this is
   covered by `startCaptureBlocksWhenPermissionFlipsAwayBeforeStart`.
   We do **not** retry — a future wave may add a "your mic was
   revoked; tap to re-allow" recovery path.
6. **`androidx.compose.material:material-icons-extended`** is the
   only reason `Icons.Filled.Mic` resolves. The skeleton wave must
   add it to `app/build.gradle.kts`.
7. **A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent vs.
   echerd27-design/hermes-agent.** The universal-sprint-header lists
   the canonical org as `A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent`,
   but every sibling wave PR (#9, #10, #11, #12, #13, #14, #15, #16,
   #17, #18) has been opened against `echerd27-design/hermes-agent`,
   which is the only repo this agent's GitHub MCP scope reaches.
   W09's draft PR therefore also targets `echerd27-design/hermes-agent`.
   If the canonical destination is `A-C-I-SOFTWARE-AND-DEVELOPMENT`,
   the owner needs to mirror or fork-transfer the merged commit
   manually — that action is outside the agent's tool scope.

## 10. Rollback

```bash
git rm -r \
  apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/chat \
  apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/voice \
  apps/android/app/src/test/java/com/aci/hermes/ui/jarvis/chat \
  apps/android/app/src/test/java/com/aci/hermes/ui/jarvis/voice
git rm docs/aci/reports/W09_CHAT_VOICE_UI_REPORT.md
git commit -m "revert: remove W09 chat/voice UI blueprint"
```

Or close the draft PR and delete the branch
`aci/jarvis-prime-09-chat-voice-ui`.

## 11. PR summary

- **Title:** `W09: Add Jarvis Prime chat and safe voice capture UI`
- **Branch:** `aci/jarvis-prime-09-chat-voice-ui`
- **Base:** `main`
- **Repo:** `echerd27-design/hermes-agent` (see §9.7 on canonical
  destination).
- **Draft:** yes. No merge, no deploy, no DNS, no app-store
  submission, no credential rotation, no money action.

## 12. Open questions

None blocking. The two follow-ups are tracked above:

1. Skeleton wave must add Gradle + `AndroidManifest.xml` with the
   `RECORD_AUDIO` permission (§2.1) before W09's verify commands
   can run.
2. Reconciliation wave should collapse the chat-local sealed
   types with the PR #18 `com.aci.hermes.model.*` package once
   both are merged (§4.1).

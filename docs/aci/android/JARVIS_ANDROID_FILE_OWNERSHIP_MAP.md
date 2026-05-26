# Jarvis Prime — Android File Ownership Map (W01, reality-corrected)

**Status:** Forward-looking, aligned with in-flight feature branches.
`apps/android/` does not exist on `origin/main`. Several PRs (W05, W09,
W10) have pre-scaffolded Kotlin source files under
`apps/android/app/src/main/java/com/aci/hermes/...` but no Gradle module
has been committed by anyone yet.

This map assigns every file in the recommended greenfield layout to an
owning PR so W02 onward can run with minimal collisions.

**Rule of thumb:** if a file is not in your sprint's "owns" list, do not
create or edit it. Shared integration files (§"Shared files") are
edited by exactly one PR per sprint, named below.

**Source root:** `apps/android/app/src/main/java/com/aci/hermes/`
(matches the package convention already used by W05 / W09 / W10
in-flight PRs).

---

## In-flight file inventory (not in W01 scope)

The following files are already declared on open feature branches and
must not be created or modified by future PRs except by the branch that
owns them:

| Path | Owning branch / PR |
|------|---------------------|
| `apps/android/app/src/main/java/com/aci/hermes/model/jarvis/JarvisApprovalCard.kt` | `aci/jarvis-prime-05-android-models` (W05) |
| `apps/android/app/src/main/java/com/aci/hermes/model/jarvis/JarvisEventDto.kt` | W05 |
| `apps/android/app/src/main/java/com/aci/hermes/model/jarvis/JarvisMemoryRecord.kt` | W05 |
| `apps/android/app/src/main/java/com/aci/hermes/model/jarvis/JarvisPresenceState.kt` | W05 |
| `apps/android/app/src/main/java/com/aci/hermes/model/jarvis/JarvisProofRecord.kt` | W05 |
| `apps/android/app/src/main/java/com/aci/hermes/model/jarvis/JarvisRiskTier.kt` | W05 |
| `apps/android/app/src/main/java/com/aci/hermes/model/jarvis/JarvisTaskCard.kt` | W05 |
| `apps/android/app/src/test/java/com/aci/hermes/model/jarvis/Jarvis*Test.kt` (7 files) | W05 |
| `apps/android/app/src/main/java/com/aci/hermes/model/JarvisGateStatus.kt` | `aci/wave-10-android-job-models` |
| `apps/android/app/src/main/java/com/aci/hermes/model/JarvisJob.kt` | W10 (job models) |
| `apps/android/app/src/main/java/com/aci/hermes/model/JarvisTask.kt` | W10 (job models) — **conflicts in spirit with W05's `JarvisTaskCard`; resolve before either merges** |
| `apps/android/app/src/main/java/com/aci/hermes/model/JarvisTaskStatus.kt` | W10 (job models) |
| `apps/android/app/src/main/java/com/aci/hermes/model/OwnerApprovalRequest.kt` | W10 (job models) |
| `apps/android/app/src/main/java/com/aci/hermes/model/VerificationEvidence.kt` | W10 (job models) |
| `apps/android/app/src/test/java/com/aci/hermes/model/Jarvis*Test.kt` (5 files) | W10 (job models) |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/chat/ChatMessage.kt` | `aci/jarvis-prime-09-chat-voice-ui` (W09) |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/chat/ChatMessageRow.kt` | W09 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/chat/ChatPreviews.kt` | W09 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/chat/ChatScreen.kt` | W09 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/chat/ChatUiState.kt` | W09 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/chat/ChatViewModel.kt` | W09 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/chat/JarvisStatus.kt` | W09 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/chat/StatusPill.kt` | W09 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/voice/MicPermissionState.kt` | W09 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/voice/VoiceCaptureScreen.kt` | W09 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/voice/VoiceCaptureState.kt` | W09 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/voice/VoiceCaptureViewModel.kt` | W09 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/voice/VoiceEducationContent.kt` | W09 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/voice/VoiceTapButton.kt` | W09 |
| `apps/android/app/src/test/java/com/aci/hermes/ui/jarvis/chat/{ChatMessage,ChatViewModel}Test.kt` | W09 |
| `apps/android/app/src/test/java/com/aci/hermes/ui/jarvis/voice/VoiceCaptureViewModelTest.kt` | W09 |

**Critical gap:** none of these branches commits Gradle build files, the
manifest, an Application class, a `MainActivity`, the nav graph, theme
resources, or `libs.versions.toml`. Until those land (via the W02
sprint), every file in the table above is dead code that does not
compile.

---

## Greenfield layout (target after W02 + ongoing sprints)

```
apps/android/
├── settings.gradle.kts                                                          [W02]
├── build.gradle.kts (root)                                                      [W02]
├── gradle.properties                                                            [W02]
├── gradlew, gradlew.bat                                                         [W02]
├── gradle/
│   ├── wrapper/{gradle-wrapper.properties, gradle-wrapper.jar}                  [W02]
│   └── libs.versions.toml                                                       [W02, shared after]
└── app/
    ├── build.gradle.kts                                                         [W02, shared after]
    ├── proguard-rules.pro                                                       [W02]
    └── src/
        ├── main/
        │   ├── AndroidManifest.xml                                              [W02, shared after]
        │   ├── java/com/aci/hermes/
        │   │   ├── HermesApplication.kt                                         [W02, shared after]
        │   │   ├── MainActivity.kt                                              [W02, edited in W03 to host NavHost]
        │   │   ├── di/
        │   │   │   └── AppContainer.kt                                          [W02, shared after]
        │   │   ├── ui/
        │   │   │   ├── theme/{Color,Theme,Type}.kt                              [W02]
        │   │   │   ├── navigation/{JarvisNavGraph,JarvisRoutes}.kt              [W03, shared after]
        │   │   │   ├── components/                                              [any PR, leaf files]
        │   │   │   └── jarvis/
        │   │   │       ├── chat/                                                [W09, in flight]
        │   │   │       ├── voice/                                               [W09, in flight]
        │   │   │       ├── orchestrator/{OrchestratorScreen,OrchestratorViewModel,OrchestratorUiState}.kt   [W03]
        │   │   │       ├── tasks/{TasksScreen,TasksViewModel,TaskRepository}.kt                              [W08]
        │   │   │       ├── diagnostics/{DiagnosticsScreen,DiagnosticsViewModel,AboutScreen}.kt              [W07]
        │   │   │       ├── settings/{SettingsScreen,SettingsViewModel,SettingsRepository}.kt                [W06]
        │   │   │       └── approvals/{ApprovalScreen,ApprovalViewModel}.kt      [W10 planning → implementation TBD]
        │   │   ├── service/
        │   │   │   └── HermesService.kt                                         [W05-service (renumber if W05 is taken)]
        │   │   ├── data/
        │   │   │   ├── gateway/{GatewayClient,GatewayApi,GatewayConfig,RealGatewayClient}.kt                [W04]
        │   │   │   ├── mock/MockGatewayClient.kt                                                            [W04]
        │   │   │   ├── termux/TermuxBridge.kt                                                               [W04]
        │   │   │   ├── prefs/UserPreferencesDataStore.kt                                                    [W06]
        │   │   │   └── tasks/{JarvisDatabase,TaskDao}.kt                                                    [W08]
        │   │   └── model/
        │   │       ├── jarvis/                                                  [W05, in flight]
        │   │       └── (job-state models)                                       [W10 job-models, in flight — see collision note]
        │   └── res/values/{strings,colors,themes}.xml                           [W02, shared after]
        ├── test/java/com/aci/hermes/                                            [per-feature, in flight on W05/W09/W10]
        └── androidTest/java/com/aci/hermes/                                     [per-feature, TBD]
```

Notation: `[Wnn]` is the PR that initially creates the file.
`[Wnn, shared after]` means subsequent PRs may edit it only when their
sprint header allows that file; conflicts must be resolved sequentially.
`[Wnn, in flight]` means the file is already on an open feature branch.

**Note on `W05`:** the existing PR `aci/jarvis-prime-05-android-models`
already claims the "W05" label for **data models**. The `HermesService`
sprint above should be renumbered (e.g. W11 or a sub-letter like W05b)
to avoid clash. The label `W05-service` is used as a placeholder in
this document.

---

## Owning-PR summary (integration order)

| Sprint | Title (suggested) | Files owned (creates) | Notable edits to shared files |
|--------|-------------------|-----------------------|-------------------------------|
| W01 (this PR) | Audit existing Android app for Jarvis Prime command center | `docs/aci/android/*.md`, `docs/aci/reports/W01_*.md` | none |
| **W02 (BLOCKING for all other Android PRs)** | Scaffold `apps/android` Gradle module: root + app gradle, manifest, `HermesApplication`, `MainActivity` (placeholder), `di/AppContainer.kt`, `ui/theme/*`, `res/values/*`, Gradle wrapper, `libs.versions.toml` | All `[W02]` entries in the tree above | **creates the shared files** |
| W03 | Navigation + Orchestrator shell | `ui/navigation/{JarvisNavGraph,JarvisRoutes}.kt`, `ui/jarvis/orchestrator/*` | edits `MainActivity.kt` to host `NavHost`; appends an `orchestrator` route to the nav graph; adds strings; adds Compose deps to `libs.versions.toml` / `app/build.gradle.kts` if needed |
| W04 | Gateway + Mock + Termux data layer | `data/gateway/*`, `data/mock/*`, `data/termux/*`, mode enum | registers `GatewayClient` in `di/AppContainer.kt`; adds OkHttp/Ktor deps; ensures `<uses-permission android:name="INTERNET"/>` is present in the manifest |
| W05 (in flight, `aci/jarvis-prime-05-android-models`) | Domain models | `model/jarvis/*` (already committed on branch) | none — depends on W02 for the Gradle module to exist before tests can run |
| W05-service / W11 (TBD) | `HermesService` foreground worker | `service/HermesService.kt` | adds `<service>` to manifest; declares `FOREGROUND_SERVICE` + `FOREGROUND_SERVICE_DATA_SYNC` + `POST_NOTIFICATIONS`; wires into `di/AppContainer.kt` |
| W06 | Settings + DataStore | `ui/jarvis/settings/*`, `data/prefs/UserPreferencesDataStore.kt` | registers `SettingsRepository` in `di/AppContainer.kt`; adds `androidx.datastore:datastore-preferences` to `libs.versions.toml`; appends `settings` route; adds strings |
| W07 | Diagnostics + About | `ui/jarvis/diagnostics/*` | appends `diagnostics` and `about` routes; adds strings |
| W08 | Tasks + Room | `ui/jarvis/tasks/*`, `data/tasks/{JarvisDatabase,TaskDao}.kt` | registers `TaskRepository` + `JarvisDatabase` in `di/AppContainer.kt`; adds Room deps; appends `tasks` route; **must first reconcile the W05/W10 `JarvisTask*` collision** |
| W09 (in flight, `aci/jarvis-prime-09-chat-voice-ui`) | Chat + Voice UI | `ui/jarvis/chat/*`, `ui/jarvis/voice/*` (already committed on branch) | depends on W02 for the Gradle module; depends on W03 for navigation; appends `chat` and `voice` routes to the nav graph (W03 owns merge) |
| W10 (in flight, `aci/wave-10-android-job-models`) | Job-state models | `model/{JarvisJob,JarvisTask,JarvisTaskStatus,...}.kt` (already committed) | **conflicts with W05 `model/jarvis/JarvisTaskCard.kt` in spirit; reconcile before merging** |
| W10 (in flight, `aci/wave-10-android-launch-audit`) | Launch readiness audit | `docs/aci/reports/W10_ANDROID_LAUNCH_AUDIT.md` (docs only) | none |
| W10 (in flight, `aci/wave-10-android-approval-screen-plan`) | Approval screen plan | `docs/aci/reports/W10_ANDROID_APPROVAL_SCREEN_PLAN.md` (docs only) | none |

Sequential where shared files are edited. Where a sprint only adds new
leaf files under `ui/jarvis/<feature>/` or `data/<area>/`, it may run in
parallel with other leaf-only sprints, provided neither touches the
shared list below.

---

## Shared files (high-risk concurrency)

The following files are edited by multiple sprints. To avoid collisions:

1. **`apps/android/app/src/main/AndroidManifest.xml`** *(does not exist; W02 creates)*
   - W02 creates with: `INTERNET`, `ACCESS_NETWORK_STATE`, `MainActivity`,
     `HermesApplication`, base theme.
   - W04 ensures `INTERNET` is present (no-op if W02 added it).
   - W05-service / W11 adds `<service>` for `HermesService`, plus
     `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_DATA_SYNC`,
     `POST_NOTIFICATIONS`.
   - W09 (in flight) appends `<uses-permission android:name="RECORD_AUDIO"/>`
     when it lands. **Note:** the W09 branch does *not* currently include
     a manifest. The voice screen will not function until W02 creates
     the manifest and W09 (or a follow-up commit on the W09 branch) adds
     the `RECORD_AUDIO` declaration. **Coordinate this with the W09
     owner.**
   - **Never** add `READ_SMS`, `RECEIVE_SMS`, `SEND_SMS`, `READ_CALL_LOG`,
     `WRITE_CALL_LOG`, `PROCESS_OUTGOING_CALLS`, `BIND_VOICE_INTERACTION`
     or equivalent. Any PR proposing those must be rejected on review.

2. **`apps/android/app/src/main/java/com/aci/hermes/MainActivity.kt`** *(does not exist; W02 creates)*
   - W02 creates with a placeholder `setContent { HermesTheme { Text("Jarvis Prime") } }`.
   - W03 replaces the body with a `NavHost`. Subsequent PRs do not edit
     `MainActivity.kt`; they add routes via `JarvisNavGraph.kt`.

3. **`apps/android/app/src/main/java/com/aci/hermes/HermesApplication.kt`** *(does not exist; W02 creates)*
   - W02 creates as either `@HiltAndroidApp class HermesApplication : Application()`
     or a manual `AppContainer` host.
   - Subsequent PRs touch it only to register dependencies if the project
     uses manual DI; with Hilt, modules go in `di/` and the Application
     class stays untouched.

4. **`apps/android/app/src/main/java/com/aci/hermes/di/AppContainer.kt`** (manual-DI variant)
   - W02 creates with HTTP/JSON scaffolding.
   - W04, W05-service/W11, W06, W08 each register one repository or
     client. PRs must append to the bottom of the file, never reorder.

5. **`apps/android/app/src/main/java/com/aci/hermes/ui/navigation/JarvisNavGraph.kt`** *(does not exist; W03 creates)*
   - W03 creates with `orchestrator` route.
   - W06, W07, W08, W09, W10 each append exactly one
     `composable("<route>") { ... }` block.

6. **`apps/android/gradle/libs.versions.toml`** and **`apps/android/app/build.gradle.kts`** *(do not exist; W02 creates)*
   - W02 establishes the version catalog and the dependency block.
   - W04 (HTTP), W05-service / W11 (foreground service utils), W06
     (DataStore), W08 (Room) each add deps. Each PR appends in a clearly
     labeled block to minimize merge friction.

7. **`apps/android/app/src/main/res/values/strings.xml`** *(does not exist; W02 creates)*
   - W02 creates with app name + base strings.
   - Each feature PR appends its own `<string>` entries.

---

## What W01 itself must not touch concurrently

W01 modifies **only**:
- `docs/aci/android/JARVIS_ANDROID_CURRENT_STATE_AUDIT.md`
- `docs/aci/android/JARVIS_ANDROID_SCREEN_MAP.md`
- `docs/aci/android/JARVIS_ANDROID_FILE_OWNERSHIP_MAP.md`
- `docs/aci/reports/W01_ANDROID_AUDIT_REPORT.md`

W01 must not modify:
- Anything under `apps/android/**` (forbidden by sprint header).
- `hermes_cli/**`, `skills/**`, `README.md`, `pyproject.toml`, `uv.lock`.
- `.github/**`, any `build.gradle*`, any `settings.gradle*`, package
  files (`package.json`, `package-lock.json`).

Collision check at audit time: ran `git diff --name-only
origin/main...<branch>` across every `origin/aci/*` remote and confirmed
**no other branch touches** any of the four ALLOWED FILES above.

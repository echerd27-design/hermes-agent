# Jarvis Prime — Android Screen Map (W01, reality-corrected)

**Status:** `apps/android/` is absent on `origin/main`. Several open
feature branches pre-scaffold Compose surfaces under
`apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/...` without a
Gradle module to host them. This document defines the **target** screen
layout for the Jarvis Prime command center, aligned with the existing
in-flight package convention.

**Conventions (locked to match in-flight work):**
- Kotlin package root: **`com.aci.hermes`**
- Jarvis-Prime command-center UI sub-package: `com.aci.hermes.ui.jarvis.*`
- Source root: `apps/android/app/src/main/java/com/aci/hermes/`
- UI stack: Jetpack Compose + Material 3
- Navigation: Compose Navigation, single `NavHost` hosted by `MainActivity`
- State: per-screen `ViewModel` (Compose-aware `viewModel()` or Hilt),
  state held in a `data class` `<Screen>UiState`

---

## Route table

| Route | Screen | Purpose | Owning PR | Target source path |
|-------|--------|---------|-----------|---------------------|
| `orchestrator` | `OrchestratorScreen` | Home / command center. Shows agent status, gateway connection state, quick actions, recent activity feed. Entry point after launch. | W03 | `ui/jarvis/orchestrator/OrchestratorScreen.kt` |
| `chat` | `ChatScreen` | Conversational interface to the agent. **Already in flight on `aci/jarvis-prime-09-chat-voice-ui`** with `ChatScreen`, `ChatMessage`, `ChatMessageRow`, `ChatPreviews`, `ChatUiState`, `ChatViewModel`, `JarvisStatus`, `StatusPill`. | W09 (in flight) | `ui/jarvis/chat/ChatScreen.kt` (already declared) |
| `tasks` | `TasksScreen` | List + detail of long-running tasks (gateway jobs, scheduled runs). Backed by Room. Models partially in flight on W05/W10 branches. | W08 | `ui/jarvis/tasks/TasksScreen.kt` |
| `diagnostics` | `DiagnosticsScreen` | Build info, current mode, gateway health, connectivity, recent error log. Read-only. | W07 | `ui/jarvis/diagnostics/DiagnosticsScreen.kt` |
| `settings` | `SettingsScreen` | Mode toggle (mock/gateway/Termux), gateway URL, theme, voice opt-in, foreground service opt-in. Persisted via DataStore-Preferences. | W06 | `ui/jarvis/settings/SettingsScreen.kt` |
| `voice` | `VoiceCaptureScreen` (modal / bottom sheet) | Microphone capture. **Only** site that requests `RECORD_AUDIO`. **Already in flight on `aci/jarvis-prime-09-chat-voice-ui`** with `VoiceCaptureScreen`, `VoiceCaptureState`, `VoiceCaptureViewModel`, `MicPermissionState`, `VoiceTapButton`, `VoiceEducationContent`. | W09 (in flight) | `ui/jarvis/voice/VoiceCaptureScreen.kt` (already declared) |
| `approvals` | `ApprovalScreen` | Owner-approval surface for risky agent actions; planned by `aci/wave-10-android-approval-screen-plan`. | W10 (planning) | `ui/jarvis/approvals/ApprovalScreen.kt` (not yet created) |
| `about` | `AboutScreen` | Versions, attributions, links to docs. No network calls. | W07 (or merged into Diagnostics) | `ui/jarvis/diagnostics/AboutScreen.kt` |

`MainActivity` (created by W02) hosts the `NavHost`; the start
destination is `orchestrator`. There is no splash screen and no
onboarding gate. None of the routes above is wired today because the
nav graph (`JarvisNavGraph.kt`, W03) and `MainActivity` (W02) do not
exist yet.

---

## Per-screen specification

### OrchestratorScreen (W03 owns)
- **File:** `ui/jarvis/orchestrator/OrchestratorScreen.kt`
- **ViewModel:** `ui/jarvis/orchestrator/OrchestratorViewModel.kt`
- **State:** `ui/jarvis/orchestrator/OrchestratorUiState.kt`
- **Renders:**
  - Connection chip (Mock / Gateway connected / Gateway error / Termux).
    Should reuse `ui/jarvis/chat/StatusPill.kt` and `JarvisStatus.kt`
    from W09 if they are already merged.
  - Primary action button (e.g. "Open chat"), navigates to `chat`.
  - Quick-link tiles to Tasks, Diagnostics, Settings, Voice, Approvals.
  - Recent activity feed (last N agent turns, fed by `GatewayClient` or
    `MockGatewayClient`).
- **Consumes:** `GatewayClient` (W04), `SettingsRepository` (W06 — read
  current mode), `TaskRepository` (W08 — recent tasks).
- **Actions exposed:** `onOpenChat()`, `onStartGatewayService()`,
  `onStopGatewayService()`, `onTapVoice()` (navigates to `voice`),
  `onNavigate(route)`.
- **Permissions triggered:** none on render. `onStartGatewayService()`
  triggers a `POST_NOTIFICATIONS` request **only** on Android 13+ and
  **only** at that moment. `onTapVoice()` navigates to `voice`, which
  triggers `RECORD_AUDIO` only after the user confirms the modal.

### ChatScreen (W09 — in flight on `aci/jarvis-prime-09-chat-voice-ui`)
- **Files in flight:** `ui/jarvis/chat/{ChatScreen,ChatMessage,ChatMessageRow,ChatPreviews,ChatUiState,ChatViewModel,JarvisStatus,StatusPill}.kt`
- W01 does **not** redefine this screen; it is committed (pending merge)
  on the W09 branch. W01 records its existence and target route.
- **Permissions triggered:** none on render. Tapping the in-screen mic
  affordance navigates to the `voice` route (W09 already includes the
  mic-on-tap gate via `MicPermissionState`).

### TasksScreen (W08 owns)
- **File:** `ui/jarvis/tasks/TasksScreen.kt`
- **ViewModel:** `ui/jarvis/tasks/TasksViewModel.kt`
- **Repository:** `ui/jarvis/tasks/TaskRepository.kt` (or `data/tasks/`), backed by Room
  (`Task` entity, `TaskDao`, `JarvisDatabase`).
- **Model reuse decision (W08 to make):** the existing in-flight models
  (`com.aci.hermes.model.jarvis.JarvisTaskCard` from W05, and the
  conflicting `com.aci.hermes.model.JarvisTask` family from W10) must be
  reconciled before W08 begins. See the collision report in
  `JARVIS_ANDROID_CURRENT_STATE_AUDIT.md`.
- **Renders:** list of task rows (status, started_at, label), tap opens
  a detail composable via nested state.
- **Actions:** `onRefresh()`, `onCancelTask(id)`, `onClearCompleted()`.
- **Permissions triggered:** none.

### DiagnosticsScreen (W07 owns)
- **File:** `ui/jarvis/diagnostics/DiagnosticsScreen.kt`
- **ViewModel:** `ui/jarvis/diagnostics/DiagnosticsViewModel.kt`
- **Renders:** build version, application id, current mode, last
  gateway ping latency, last error message, OS version, locale.
- **Actions:** `onPingGateway()`, `onCopyDiagnosticsToClipboard()`.
- **Permissions triggered:** none.

### SettingsScreen (W06 owns)
- **File:** `ui/jarvis/settings/SettingsScreen.kt`
- **ViewModel:** `ui/jarvis/settings/SettingsViewModel.kt`
- **Repository:** `ui/jarvis/settings/SettingsRepository.kt`, backed by
  `data/prefs/UserPreferencesDataStore.kt` (Jetpack DataStore-Preferences).
- **Keys persisted:** `mode` (enum: `MOCK | GATEWAY | TERMUX`),
  `gatewayUrl` (String), `gatewayAuthToken` (String, securely stored —
  EncryptedSharedPreferences or DataStore + Tink, W06 decision),
  `themeMode` (`SYSTEM | LIGHT | DARK`), `voiceEnabled` (Boolean,
  default false), `foregroundServiceEnabled` (Boolean, default false).
- **Renders:** form rows; mode change triggers reconfigure of
  `GatewayClient` provider.
- **Actions:** `onModeChange(mode)`, `onGatewayUrlChange(url)`,
  `onSaveGatewayAuth(token)`, `onThemeChange(...)`, `onToggleVoice()`,
  `onToggleForegroundService()`.
- **Permissions triggered:** toggling `foregroundServiceEnabled` to
  `true` may request `POST_NOTIFICATIONS` (API 33+). Toggling
  `voiceEnabled` does **not** request `RECORD_AUDIO`; that request
  happens on first navigation to `voice`.

### VoiceCaptureScreen (W09 — in flight)
- **Files in flight:** `ui/jarvis/voice/{VoiceCaptureScreen,VoiceCaptureState,VoiceCaptureViewModel,MicPermissionState,VoiceTapButton,VoiceEducationContent}.kt`
- W01 does **not** redefine this screen. The design rule "mic permission
  only on user tap" is already implemented by `MicPermissionState` +
  `VoiceTapButton` on the W09 branch; W01 endorses it.

### ApprovalScreen (W10 — planning only)
- **Planning doc:** `docs/aci/reports/W10_ANDROID_APPROVAL_SCREEN_PLAN.md`
  (on `aci/wave-10-android-approval-screen-plan`).
- **File:** `ui/jarvis/approvals/ApprovalScreen.kt` (not yet created).
- **Permissions triggered:** none on render.

### AboutScreen (W07 owns)
- **File:** `ui/jarvis/diagnostics/AboutScreen.kt` (co-located with
  Diagnostics; promoted to its own folder later if it grows).
- **Renders:** Jarvis Prime banner, version (from `BuildConfig`), Hermes
  backend attribution, license links.

---

## Cross-cutting UI

- **Theme:** `ui/theme/Theme.kt`, `Color.kt`, `Type.kt`. Material 3 with
  dynamic color (Android 12+) and dark/light/system mode driven by
  `SettingsRepository`. Created by W02.
- **Navigation graph:** `ui/navigation/JarvisNavGraph.kt`, routes in
  `ui/navigation/JarvisRoutes.kt`. Created by W03; thereafter, each
  feature PR appends exactly one `composable("<route>") { ... }` block.
- **Reusable components:** `ui/components/` (generic) and
  `ui/jarvis/chat/StatusPill.kt`/`JarvisStatus.kt` (W09 already places
  these; future PRs may consume them). Each new PR may add components
  there; conflicts are rare because components are leaf files.

---

## Permission map (summary)

| Permission | Declared in manifest (target W02) | Requested at | Trigger UI | Required for app to work? |
|------------|-----------------------------------|--------------|------------|---------------------------|
| `INTERNET` | yes | install time (normal) | n/a | yes — but no runtime prompt |
| `ACCESS_NETWORK_STATE` | yes | install time | n/a | no |
| `POST_NOTIFICATIONS` (API 33+) | yes | user toggles "Foreground service" in Settings, or starts `HermesService` from Orchestrator | Settings toggle / Orchestrator action | no — mock mode works without it |
| `FOREGROUND_SERVICE` + `FOREGROUND_SERVICE_DATA_SYNC` | yes | install time | n/a | only if foreground service feature is enabled |
| `RECORD_AUDIO` | yes | user enters `VoiceCaptureScreen` and taps "Hold to talk" (W09 already implements this gate) | Voice modal | no — voice is optional |
| `READ_SMS` / `READ_CALL_LOG` / similar | **not declared** | never | n/a | **prohibited** |

The app must reach `OrchestratorScreen` and complete a mock-mode prompt
with zero runtime permissions granted. This is the W02 + W03 acceptance
check.

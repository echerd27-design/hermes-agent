# Jarvis Prime — Android Screen Map (W01, forward-looking)

**Status:** No Android app exists in `apps/android/` today. This document
defines the **target** Compose screens for the Jarvis Prime command
center so that subsequent PRs can be carved up without overlap.

**Conventions:**
- Package root: `com.aci.jarvisprime`
- Source root: `apps/android/app/src/main/kotlin/com/aci/jarvisprime/`
- UI stack: Jetpack Compose + Material 3
- Navigation: Compose Navigation, single `NavHost` hosted by `MainActivity`
- State: per-screen `ViewModel` (Compose-aware `viewModel()` or Hilt),
  state held in a `data class` `<Screen>State`

---

## Route table

| Route | Screen | Purpose | Owning PR | Source path |
|-------|--------|---------|-----------|-------------|
| `orchestrator` | `OrchestratorScreen` | Home / command center. Shows agent status, gateway connection state, quick actions, recent activity feed. Entry point after launch. | W03 | `feature/orchestrator/OrchestratorScreen.kt` |
| `tasks` | `TasksScreen` | List + detail of long-running tasks (gateway jobs, scheduled runs). Backed by Room. | W08 | `feature/tasks/TasksScreen.kt` |
| `diagnostics` | `DiagnosticsScreen` | Build info, current mode, gateway health, connectivity, recent error log. Read-only. | W07 | `feature/diagnostics/DiagnosticsScreen.kt` |
| `settings` | `SettingsScreen` | Mode toggle (mock/gateway/Termux), gateway URL, theme, voice opt-in, foreground service opt-in. Persisted via DataStore-Preferences. | W06 | `feature/settings/SettingsScreen.kt` |
| `voice` | `VoiceCaptureScreen` (modal / bottom sheet) | Microphone capture. **Only** site that requests `RECORD_AUDIO`. | W09 | `feature/voice/VoiceCaptureScreen.kt` |
| `about` | `AboutScreen` | Versions, attributions, links to docs. No network calls. | W07 (or merged into Diagnostics) | `feature/diagnostics/AboutScreen.kt` |

`MainActivity` hosts the `NavHost`; the start destination is
`orchestrator`. There is no splash screen and no onboarding gate.

---

## Per-screen specification

### OrchestratorScreen (W03 owns)
- **File:** `feature/orchestrator/OrchestratorScreen.kt`
- **ViewModel:** `feature/orchestrator/OrchestratorViewModel.kt`
- **State:** `feature/orchestrator/OrchestratorState.kt`
- **Renders:**
  - Connection chip (Mock / Gateway connected / Gateway error / Termux).
  - Primary action button (e.g. "Send a command"), opens a Compose input
    sheet that calls `GatewayClient.sendPrompt(...)`.
  - Quick-link tiles to Tasks, Diagnostics, Settings, Voice.
  - Recent activity feed (last N agent turns, fed by `GatewayClient` or
    `MockGatewayClient`).
- **Consumes:** `GatewayClient` (W04), `SettingsRepository` (W06 — read
  current mode), `TaskRepository` (W08 — recent tasks).
- **Actions exposed:** `onSendPrompt(text)`, `onStartGatewayService()`,
  `onStopGatewayService()`, `onTapVoice()` (navigates to `voice`),
  `onNavigate(route)`.
- **Permissions triggered:** none on render. `onStartGatewayService()`
  triggers a `POST_NOTIFICATIONS` request **only** on Android 13+ and
  **only** at that moment. `onTapVoice()` navigates to `voice`, which
  triggers `RECORD_AUDIO` only after the user confirms the modal.

### TasksScreen (W08 owns)
- **File:** `feature/tasks/TasksScreen.kt`
- **ViewModel:** `feature/tasks/TasksViewModel.kt`
- **Repository:** `feature/tasks/TaskRepository.kt`, backed by Room
  (`Task` entity, `TaskDao`, `JarvisDatabase`).
- **Renders:** list of `Task` rows (status, started_at, label), tap
  opens a detail composable in the same screen via nested state (no
  separate route).
- **Actions:** `onRefresh()`, `onCancelTask(id)`, `onClearCompleted()`.
- **Permissions triggered:** none.

### DiagnosticsScreen (W07 owns)
- **File:** `feature/diagnostics/DiagnosticsScreen.kt`
- **ViewModel:** `feature/diagnostics/DiagnosticsViewModel.kt`
- **Renders:** build version, application id, current mode, last
  gateway ping latency, last error message, OS version, locale.
- **Actions:** `onPingGateway()`, `onCopyDiagnosticsToClipboard()`.
- **Permissions triggered:** none.

### SettingsScreen (W06 owns)
- **File:** `feature/settings/SettingsScreen.kt`
- **ViewModel:** `feature/settings/SettingsViewModel.kt`
- **Repository:** `feature/settings/SettingsRepository.kt`, backed by
  `data/prefs/UserPreferencesDataStore.kt` (Jetpack DataStore-Preferences).
- **Keys persisted:** `mode` (enum: `MOCK | GATEWAY | TERMUX`),
  `gatewayUrl` (String), `gatewayAuthToken` (String, securely stored —
  see W06 note on EncryptedSharedPreferences or DataStore + Tink),
  `themeMode` (`SYSTEM | LIGHT | DARK`), `voiceEnabled` (Boolean,
  default false), `foregroundServiceEnabled` (Boolean, default false).
- **Renders:** form rows; mode change triggers reconfigure of
  `GatewayClient` provider.
- **Actions:** `onModeChange(mode)`, `onGatewayUrlChange(url)`,
  `onSaveGatewayAuth(token)`, `onThemeChange(...)`, `onToggleVoice()`,
  `onToggleForegroundService()`.
- **Permissions triggered:** toggling `foregroundServiceEnabled` to
  `true` is the first place that may request `POST_NOTIFICATIONS` (API
  33+). Toggling `voiceEnabled` does **not** request `RECORD_AUDIO`;
  that request happens on first navigation to `voice`.

### VoiceCaptureScreen (W09 owns)
- **File:** `feature/voice/VoiceCaptureScreen.kt`
- **ViewModel:** `feature/voice/VoiceCaptureViewModel.kt`
- **Renders:** modal sheet / dialog with a "Hold to talk" button and
  level meter. Only requests `RECORD_AUDIO` when the user taps the
  capture button for the first time.
- **Behavior on denial:** shows a polite empty state with a "Re-request
  permission" affordance; no crash, no nav block. The rest of the app
  remains functional.
- **Permissions triggered:** `RECORD_AUDIO`, on user tap, exactly once
  per session unless previously granted.

### AboutScreen (W07 owns)
- **File:** `feature/diagnostics/AboutScreen.kt` (co-located with
  Diagnostics; promoted to its own folder later if it grows).
- **Renders:** Jarvis Prime banner, version (from `BuildConfig`), Hermes
  backend attribution, license links.

---

## Cross-cutting UI

- **Theme:** `ui/theme/Theme.kt`, `Color.kt`, `Type.kt`. Material 3 with
  dynamic color (Android 12+) and dark/light/system mode driven by
  `SettingsRepository`.
- **Navigation graph:** `ui/navigation/JarvisNavGraph.kt`, routes in
  `ui/navigation/JarvisRoutes.kt`. Owned by W03 initially; shared file
  rule applies thereafter (see ownership map).
- **Reusable components:** `ui/components/` — chips, status pills, empty
  states, error banners. Each PR may add components there; conflicts are
  rare because components are leaf files.

---

## Permission map (summary)

| Permission | Declared in manifest | Requested at | Trigger UI | Required for app to work? |
|------------|----------------------|--------------|------------|---------------------------|
| `INTERNET` | yes | install time (normal) | n/a | yes — but no runtime prompt |
| `ACCESS_NETWORK_STATE` | yes | install time | n/a | no |
| `POST_NOTIFICATIONS` (API 33+) | yes | user toggles "Foreground service" in Settings, or starts `HermesService` from Orchestrator | Settings toggle / Orchestrator action | no — mock mode works without it |
| `FOREGROUND_SERVICE` + `FOREGROUND_SERVICE_DATA_SYNC` | yes | install time | n/a | only if foreground service feature is enabled |
| `RECORD_AUDIO` | yes | user enters `VoiceCaptureScreen` and taps "Hold to talk" | Voice modal | no — voice is optional |
| `READ_SMS` / `READ_CALL_LOG` / similar | **not declared** | never | n/a | **prohibited** |

The app must reach `OrchestratorScreen` and complete a mock-mode prompt
with zero runtime permissions granted. This is a W02 acceptance check.

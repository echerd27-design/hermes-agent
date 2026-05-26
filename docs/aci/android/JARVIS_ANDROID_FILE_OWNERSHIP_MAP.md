# Jarvis Prime — Android File Ownership Map (W01)

**Status:** Forward-looking. No Android source exists today. This map
assigns every file in the recommended greenfield layout to an owning PR
so that W02–W09 can run with minimal collisions.

**Rule of thumb:** if a file is not in your sprint's "owns" list, do not
create or edit it. Shared integration files (§"Shared files") are
edited by exactly one PR per sprint, named below.

---

## Greenfield layout

```
apps/android/
├── settings.gradle.kts                                   [W02]
├── build.gradle.kts                                      [W02]
├── gradle.properties                                     [W02]
├── gradlew                                               [W02]
├── gradlew.bat                                           [W02]
├── gradle/
│   ├── wrapper/gradle-wrapper.properties                 [W02]
│   ├── wrapper/gradle-wrapper.jar                        [W02]
│   └── libs.versions.toml                                [W02, shared after]
└── app/
    ├── build.gradle.kts                                  [W02, shared after]
    ├── proguard-rules.pro                                [W02]
    └── src/
        ├── main/
        │   ├── AndroidManifest.xml                       [W02, shared after]
        │   ├── kotlin/com/aci/jarvisprime/
        │   │   ├── JarvisPrimeApplication.kt             [W02, shared after]
        │   │   ├── MainActivity.kt                       [W02, edited in W03]
        │   │   ├── di/
        │   │   │   └── AppContainer.kt                   [W02, shared after]
        │   │   ├── ui/
        │   │   │   ├── theme/
        │   │   │   │   ├── Color.kt                      [W02]
        │   │   │   │   ├── Theme.kt                      [W02]
        │   │   │   │   └── Type.kt                       [W02]
        │   │   │   ├── navigation/
        │   │   │   │   ├── JarvisNavGraph.kt             [W03, shared after]
        │   │   │   │   └── JarvisRoutes.kt               [W03, shared after]
        │   │   │   └── components/                       [any PR, leaf files]
        │   │   ├── feature/
        │   │   │   ├── orchestrator/
        │   │   │   │   ├── OrchestratorScreen.kt         [W03]
        │   │   │   │   ├── OrchestratorViewModel.kt      [W03]
        │   │   │   │   └── OrchestratorState.kt          [W03]
        │   │   │   ├── tasks/
        │   │   │   │   ├── TasksScreen.kt                [W08]
        │   │   │   │   ├── TasksViewModel.kt             [W08]
        │   │   │   │   ├── TaskRepository.kt             [W08]
        │   │   │   │   ├── Task.kt                       [W08]
        │   │   │   │   ├── TaskDao.kt                    [W08]
        │   │   │   │   └── JarvisDatabase.kt             [W08]
        │   │   │   ├── diagnostics/
        │   │   │   │   ├── DiagnosticsScreen.kt          [W07]
        │   │   │   │   ├── DiagnosticsViewModel.kt       [W07]
        │   │   │   │   └── AboutScreen.kt                [W07]
        │   │   │   ├── settings/
        │   │   │   │   ├── SettingsScreen.kt             [W06]
        │   │   │   │   ├── SettingsViewModel.kt          [W06]
        │   │   │   │   └── SettingsRepository.kt         [W06]
        │   │   │   └── voice/
        │   │   │       ├── VoiceCaptureScreen.kt         [W09]
        │   │   │       └── VoiceCaptureViewModel.kt      [W09]
        │   │   ├── service/
        │   │   │   └── HermesService.kt                  [W05]
        │   │   ├── data/
        │   │   │   ├── gateway/
        │   │   │   │   ├── GatewayClient.kt              [W04]
        │   │   │   │   ├── GatewayApi.kt                 [W04]
        │   │   │   │   ├── GatewayConfig.kt              [W04]
        │   │   │   │   └── RealGatewayClient.kt          [W04]
        │   │   │   ├── mock/
        │   │   │   │   └── MockGatewayClient.kt          [W04]
        │   │   │   ├── termux/
        │   │   │   │   └── TermuxBridge.kt               [W04]
        │   │   │   └── prefs/
        │   │   │       └── UserPreferencesDataStore.kt   [W06]
        │   │   └── model/
        │   │       └── Mode.kt                           [W04]
        │   └── res/
        │       ├── values/
        │       │   ├── strings.xml                       [W02, shared after]
        │       │   ├── colors.xml                        [W02]
        │       │   └── themes.xml                        [W02]
        │       └── mipmap-*/                             [W02]
        ├── test/
        │   └── kotlin/com/aci/jarvisprime/               [owning PR per feature]
        └── androidTest/
            └── kotlin/com/aci/jarvisprime/               [owning PR per feature]
```

Notation: `[Wnn]` is the PR that initially creates the file. `[Wnn,
shared after]` means after creation, subsequent PRs may edit it only if
their sprint header allows that file in ALLOWED FILES; conflicts must
be resolved sequentially, never concurrently.

---

## Owning-PR summary (integration order)

| Sprint | Title (suggested) | Files owned (creates) | Allowed edits to shared files |
|--------|-------------------|-----------------------|-------------------------------|
| W01 | Audit existing Android app for Jarvis Prime command center | `docs/aci/android/*.md`, `docs/aci/reports/W01_*.md` | none |
| W02 | Scaffold `apps/android` (Gradle + Compose + Manifest skeleton + Theme + AppContainer + empty MainActivity) | All `[W02]` entries above | creates the shared files |
| W03 | Navigation + Orchestrator shell | `ui/navigation/*`, `feature/orchestrator/*` | edits `MainActivity.kt` to host `NavHost`; appends an `orchestrator` route to `JarvisNavGraph.kt`; adds strings to `res/values/strings.xml`; adds Compose deps to `libs.versions.toml` / `app/build.gradle.kts` if needed |
| W04 | Gateway + Mock + Termux data layer | `data/gateway/*`, `data/mock/*`, `data/termux/*`, `model/Mode.kt` | registers `GatewayClient` in `di/AppContainer.kt`; adds OkHttp/Ktor deps to `libs.versions.toml`; adds `<uses-permission android:name="android.permission.INTERNET"/>` to `AndroidManifest.xml` if not already there |
| W05 | HermesService (foreground) | `service/HermesService.kt` | adds `<service>` entry to `AndroidManifest.xml`; declares `FOREGROUND_SERVICE` + `FOREGROUND_SERVICE_DATA_SYNC` + `POST_NOTIFICATIONS`; wires service start/stop into `di/AppContainer.kt` |
| W06 | Settings + DataStore | `feature/settings/*`, `data/prefs/UserPreferencesDataStore.kt` | registers `SettingsRepository` in `di/AppContainer.kt`; adds `androidx.datastore:datastore-preferences` to `libs.versions.toml`; appends `settings` route to `JarvisNavGraph.kt`; adds strings to `res/values/strings.xml` |
| W07 | Diagnostics + About | `feature/diagnostics/*` | appends `diagnostics` and `about` routes to `JarvisNavGraph.kt`; adds strings to `res/values/strings.xml` |
| W08 | Tasks + Room | `feature/tasks/*` | registers `TaskRepository` + `JarvisDatabase` in `di/AppContainer.kt`; adds Room deps to `libs.versions.toml`; appends `tasks` route to `JarvisNavGraph.kt`; adds strings |
| W09 | Voice capture (mic permission on tap) | `feature/voice/*` | appends `voice` route to `JarvisNavGraph.kt`; adds `<uses-permission android:name="android.permission.RECORD_AUDIO"/>` to `AndroidManifest.xml`; adds strings |

Strictly sequential where shared files are edited. Where a sprint only
adds new leaf files (e.g. `feature/<x>/*`), it may run in parallel with
other sprints that also only add leaf files, provided neither touches
the shared list below.

---

## Shared files (high-risk concurrency)

The following files are edited by multiple sprints. To avoid collisions:

1. **`apps/android/app/src/main/AndroidManifest.xml`**
   - W02 creates with: `INTERNET`, `ACCESS_NETWORK_STATE`, `MainActivity`,
     `JarvisPrimeApplication`, base theme.
   - W04 may add `INTERNET` if missing (no-op if W02 added it).
   - W05 adds `<service>` for `HermesService`, plus
     `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_DATA_SYNC`,
     `POST_NOTIFICATIONS`.
   - W09 adds `RECORD_AUDIO`.
   - **Never** add `READ_SMS`, `RECEIVE_SMS`, `SEND_SMS`, `READ_CALL_LOG`,
     `WRITE_CALL_LOG`, `PROCESS_OUTGOING_CALLS`,
     `BIND_VOICE_INTERACTION` or equivalent. Any PR proposing those must
     be rejected on review.

2. **`apps/android/app/src/main/kotlin/com/aci/jarvisprime/MainActivity.kt`**
   - W02 creates with a placeholder `setContent { JarvisPrimeTheme { Text("Jarvis Prime") } }`.
   - W03 replaces the body with a `NavHost`. Subsequent PRs do not edit
     `MainActivity.kt`; they add routes via `JarvisNavGraph.kt`.

3. **`apps/android/app/src/main/kotlin/com/aci/jarvisprime/JarvisPrimeApplication.kt`**
   - W02 creates as either `@HiltAndroidApp class JarvisPrimeApplication : Application()` or a manual `AppContainer` host.
   - Subsequent PRs touch it only to register their feature's
     dependencies if the project uses manual DI; with Hilt, modules go
     in `di/` and `Application.kt` stays untouched.

4. **`apps/android/app/src/main/kotlin/com/aci/jarvisprime/di/AppContainer.kt`** (manual-DI variant only)
   - W02 creates with just `okHttp`/`json` scaffolding.
   - W04, W05, W06, W08 each register one repository or client. PRs must
     append to the bottom of the file, never reorder.

5. **`apps/android/app/src/main/kotlin/com/aci/jarvisprime/ui/navigation/JarvisNavGraph.kt`**
   - W03 creates with `orchestrator` route.
   - W06, W07, W08, W09 each append exactly one `composable("<route>") { ... }` block.

6. **`apps/android/gradle/libs.versions.toml`** and **`apps/android/app/build.gradle.kts`**
   - W02 establishes the version catalog and the dependency block.
   - W04 (HTTP), W05 (foreground service utils, if any), W06 (DataStore),
     W08 (Room) each add their deps. Each PR must append in a clearly
     labeled block to minimize merge friction.

7. **`apps/android/app/src/main/res/values/strings.xml`**
   - W02 creates with app name + base strings.
   - Each feature PR appends its own `<string>` entries. Conflicts are
     trivial to resolve manually.

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

A collision check at the time of audit (`git branch -a` and the open-PR
list) found no concurrent work touching `docs/aci/**` or `apps/android/**`.

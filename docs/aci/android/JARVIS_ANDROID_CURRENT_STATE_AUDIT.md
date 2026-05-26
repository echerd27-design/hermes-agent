# Jarvis Prime — Android Current-State Audit (W01)

**Audit date:** 2026-05-26
**Repository:** `echerd27-design/hermes-agent`
**Audit branch:** `aci/jarvis-prime-01-android-audit`
**Audit scope:** Inspect `apps/android/` and document existing Android app
state for the Jarvis Prime command center implementation map.

---

## Verdict

> **No Android application is present in this repository.**
>
> The path `apps/android/` does not exist on `HEAD`, on `origin/main`, or in
> any commit reachable through `git log --all`. There are zero
> `AndroidManifest.xml` files, zero Gradle build files, and zero Kotlin or
> Java source files anywhere in the working tree. W01 therefore proceeds as
> a **greenfield audit**: it records what is currently absent, restates the
> global product rules that must shape the future app, and ships a forward-
> looking file-ownership map so subsequent PRs (W02 onward) can scaffold
> the app without overlapping work.
>
> **No Android source code is created in W01.** This deliverable is
> documentation only.

---

## Verification commands

The verdict was reached by running these read-only checks from the repo
root. Future reviewers can re-run them to confirm the audit was honest.

```text
$ ls -la /home/user/hermes-agent/apps/ 2>&1
ls: cannot access '/home/user/hermes-agent/apps/': No such file or directory

$ find . -maxdepth 4 -type d -name android -o -type d -name kotlin -o -type d -name java
(no output)

$ find . -name AndroidManifest.xml -not -path './node_modules/*'
(no output)

$ find . -maxdepth 3 -name "*.gradle*" -not -path './node_modules/*'
(no output)

$ git ls-tree -r origin/main --name-only | grep -E "^apps/|AndroidManifest|\.kt$|build\.gradle"
(no output)

$ git log --all --diff-filter=A --name-only --pretty=format: | grep -E "^apps/android"
(no output)
```

Cross-checked branches: `main` and `aci/jarvis-prime-01-android-audit`
are the only branches with content; neither contains an Android app.

The repository is a Python-based Hermes Agent codebase with surfaces at
`agent/`, `gateway/`, `tui_gateway/`, `ui-tui/`, `web/`, `website/`,
`hermes_cli/`, `skills/`, `tools/`, and `plugins/`. None of these is an
Android client.

---

## Item-by-item finding (the 10 mission targets)

The sprint header asked for exact files responsible for ten components.
Every one is **NOT FOUND** because the app does not exist. Searches run:

| # | Target | Search performed | Result |
|---|--------|------------------|--------|
| 1 | App package, stack, screens, services, repositories, models, navigation, settings, diagnostics, mock mode, gateway mode, Termux mode | `ls apps/android`, `find . -name 'build.gradle*'`, `find . -name AndroidManifest.xml` | NOT FOUND — no app exists |
| 2a | `MainActivity` | `grep -rn "class MainActivity"` (whole repo) | NOT FOUND |
| 2b | `HermesService` | `grep -rn "class HermesService"` (whole repo) | NOT FOUND |
| 2c | `OrchestratorScreen` | `grep -rn "OrchestratorScreen\|fun OrchestratorScreen"` (whole repo) | NOT FOUND |
| 2d | Settings (screen + repository) | `grep -rni "SettingsScreen\|SettingsRepository\|DataStore"` (whole repo) | NOT FOUND |
| 2e | Diagnostics | `grep -rni "DiagnosticsScreen\|Diagnostic"` (whole repo, Kotlin scope) | NOT FOUND |
| 2f | Task repository | `grep -rni "TaskRepository\|TaskDao"` (whole repo) | NOT FOUND |
| 2g | App container / DI | `grep -rni "AppContainer\|@HiltAndroidApp"` (whole repo) | NOT FOUND |
| 2h | Theme | `find . -path '*/ui/theme/*.kt'` | NOT FOUND |
| 2i | Navigation | `grep -rni "NavHost\|rememberNavController"` (whole repo) | NOT FOUND |
| 3a | Notification permission behavior | `grep -rn "POST_NOTIFICATIONS"` (whole repo) | NOT FOUND — **N/A** (see design rule §"Permissions") |
| 3b | Foreground service usage | `grep -rn "startForegroundService\|foregroundServiceType"` (whole repo) | NOT FOUND |
| 3c | Microphone | `grep -rn "RECORD_AUDIO\|AudioRecord\|SpeechRecognizer"` (whole repo) | NOT FOUND |
| 3d | SMS / Call-log absence | `grep -rn "SmsManager\|Telephony.Sms\|CallLog"` (whole repo) | NOT FOUND — confirmed absent |
| 4 | Launch blockers | (no app to launch) | NOT FOUND |
| 5 | Recommended folder structure | (see §"Greenfield layout") | DOCUMENTED |
| 6 | File ownership map | (see `JARVIS_ANDROID_FILE_OWNERSHIP_MAP.md`) | DOCUMENTED |
| 7 | Integration order | (see ownership map) | DOCUMENTED |
| 8 | What must not be touched concurrently | (see §"Concurrency rules") | DOCUMENTED |
| 9 | Build/test commands | (see §"Build/test contract") | DOCUMENTED |
| 10 | Auto-notification prompt at startup | `grep -rn "POST_NOTIFICATIONS"` (whole repo) | NOT FOUND — **the answer is "no, because the app does not exist yet."** Recorded as a design rule for W02. |

---

## Design rules carried forward (Jarvis Prime global product rules)

These rules come from the sprint header and the CLAUDE.md project
instructions. They apply to every future Android PR (W02 onward) and
must be cited in PR descriptions when relevant.

### Identity & runtime split
- Product-facing name is **Jarvis Prime**. The Hermes name may persist in
  backend, runtime, and package identifiers for compatibility (e.g. the
  foreground service may be called `HermesService` in code if it
  preserves backend semantics).
- Android is the **body / control surface**, not the full AI brain.
- The AI brain stays in the Hermes/Jarvis backend (Python gateway, agent
  loop, skills, plugins). **No Python runtime is embedded inside the APK.**
- **No gateway-side secrets are stored in Android.** The app holds only
  client-side configuration (gateway URL, mock toggle, theme) and short-
  lived auth tokens issued by the gateway.

### Permissions (the non-negotiables)
- **No automatic notification permission prompt on first launch.**
  `POST_NOTIFICATIONS` is requested lazily, only when the user enables a
  feature that requires posting notifications (e.g. starts the
  `HermesService` foreground worker from the UI).
- **Microphone permission only after the user taps voice.** No
  pre-emptive `RECORD_AUDIO` request at app start, splash, or onboarding.
- **No SMS, Call Log, or always-listening behavior.** The manifest will
  not declare `READ_SMS`, `RECEIVE_SMS`, `SEND_SMS`, `READ_CALL_LOG`,
  `WRITE_CALL_LOG`, `PROCESS_OUTGOING_CALLS`, `BIND_VOICE_INTERACTION`,
  or any equivalent.
- **Optional permissions must be optional.** Each Jarvis Prime screen
  must render usable empty/disabled state when its associated permission
  is denied. The app must boot and reach the Orchestrator home with zero
  runtime permissions granted.

### Surfaces (mock / gateway / Termux)
- The app must support three runtime modes, selectable in Settings:
  - **Mock mode** — uses an in-process `MockGatewayClient` with canned
    responses. Default for fresh installs and CI.
  - **Gateway mode** — talks to the Hermes gateway over HTTPS. Gateway URL
    is user-configurable; bearer/JWT issued by the gateway, not embedded
    at build time.
  - **Termux mode** — bridges to a locally running Hermes via the Termux
    intent surface, for users who run the Hermes Python runtime on the
    same device.
- Mode selection lives in `feature/settings/`. Routing of API calls based
  on mode lives in `data/gateway/` with a single `GatewayClient` interface
  and three implementations.

### Launch flow
- `MainActivity` boots to the Orchestrator route directly. No mandatory
  onboarding wall, no permission gauntlet, no required gateway
  configuration. Empty/mock state must work out of the box.
- `HermesService` is **not** started in `MainActivity.onCreate`. It is
  started only when the user explicitly enables the gateway connection
  from the Orchestrator or Settings.

---

## Build/test contract

Once W02 scaffolds the project, the following commands MUST work from
the repo root. Future PRs are responsible for keeping them green.

```bash
cd apps/android && ./gradlew assembleDebug
cd apps/android && ./gradlew testDebugUnitTest
```

W01 itself does **not** run these — `apps/android/` does not exist yet,
so they would fail with "No such file or directory". This is the
documented "skipped tests" justification for the W01 PR.

---

## Concurrency rules (what must not be touched concurrently)

W01 only modifies files under `docs/aci/android/` and `docs/aci/reports/`.
There are no concurrent Android source edits to coordinate.

For W02 onward, see `JARVIS_ANDROID_FILE_OWNERSHIP_MAP.md` for the
sprint-by-sprint owning-PR map and the list of shared integration files
(`AndroidManifest.xml`, the Application class, the nav graph,
`libs.versions.toml`, `app/build.gradle.kts`, `res/values/strings.xml`).

---

## Open questions (non-blocking)

- DI choice: Hilt vs manual `AppContainer`. Recorded as a W02 decision;
  the ownership map covers both layouts.
- Gateway HTTP client: Retrofit + OkHttp, Ktor client, or hand-rolled
  `HttpUrlConnection`. Recorded as a W04 decision.
- Persistence for tasks: Room vs DataStore-Proto. Recorded as a W08
  decision; Room is the default recommendation.

None of these block W01.

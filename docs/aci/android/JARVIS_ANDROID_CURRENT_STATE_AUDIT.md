# Jarvis Prime — Android Current-State Audit (W01)

**Audit date:** 2026-05-26
**Repository:** `echerd27-design/hermes-agent`
**Audit branch:** `aci/jarvis-prime-01-android-audit`
**Audit scope:** Inspect `apps/android/` on `origin/main` and across all
open feature branches; document existing Android app state for the
Jarvis Prime command center implementation map.

---

## Verdict

> **On `origin/main`: no Android application exists.** `apps/android/` is
> absent. There is no `AndroidManifest.xml`, no Gradle build, no
> `JarvisPrimeApplication`/`MainActivity`/`HermesService`, no theme, no
> navigation graph, no theme resources, no version catalog, no Gradle
> wrapper, no `gradlew`.
>
> **On open feature branches: a pre-scaffold of Kotlin source files is in
> flight, but no Gradle scaffold has landed.** At least five open PR
> branches add files under `apps/android/app/src/main/java/com/aci/hermes/...`
> and `apps/android/app/src/test/java/com/aci/hermes/...`. **None of them
> commits `build.gradle*`, `settings.gradle*`, `AndroidManifest.xml`, a
> Gradle wrapper, or `libs.versions.toml`.** Consequently, even after all
> in-flight PRs merge to `main`, `./gradlew assembleDebug` would still
> fail — the project simply does not have a buildable Android module yet.
>
> W01 therefore lands as a **documentation-only, reality-corrected
> audit**: it records what is currently absent on `main`, what is in
> flight on feature branches (collision-mapped), the design rules that
> must shape all future Android work, and a sprint-by-sprint ownership
> map for the missing pieces.
>
> **No Android source code is created in W01.** This deliverable is
> documentation only.

---

## Verification commands

Reproducible from the repo root. Run after `git fetch origin`.

```text
$ ls -la /home/user/hermes-agent/apps/ 2>&1
ls: cannot access '/home/user/hermes-agent/apps/': No such file or directory
# → confirms HEAD and origin/main have no apps/

$ git ls-tree -r origin/main --name-only | grep -E "^apps/|AndroidManifest|\.kt$|build\.gradle"
# → no output

$ git log --all --diff-filter=A --name-only --pretty=format: | grep '^apps/android'
# (lists files added on feature branches; none on main)

# Check that no branch has committed the Gradle scaffold:
$ for b in $(git branch -r | grep -v HEAD); do
    git ls-tree -r "$b" --name-only 2>/dev/null \
      | grep -E "^apps/android/.*(build\.gradle|settings\.gradle|AndroidManifest\.xml|gradlew$|libs\.versions\.toml)"
  done
# → no output anywhere
```

The repository is the Python-based Hermes Agent codebase. Surfaces:
`agent/`, `gateway/`, `tui_gateway/`, `ui-tui/`, `web/`, `website/`,
`hermes_cli/`, `skills/`, `tools/`, `plugins/`. None is an Android client.

---

## Concurrent work — in-flight Android PRs (collision map)

Discovered on 2026-05-26 by fetching every `aci/*` branch and diffing
against `origin/main`. These PRs are open and pre-scaffold Kotlin source
without a build system:

| Branch (PR title) | Package(s) introduced | Files added (count) | Owns these paths |
|-------------------|-----------------------|---------------------|------------------|
| `aci/jarvis-prime-05-android-models` — *W05: Add Android Jarvis Prime command-center models* | `com.aci.hermes.model.jarvis` | 7 main + 7 test + 1 report | `apps/android/app/src/main/java/com/aci/hermes/model/jarvis/` (JarvisApprovalCard, JarvisEventDto, JarvisMemoryRecord, JarvisPresenceState, JarvisProofRecord, JarvisRiskTier, JarvisTaskCard) |
| `aci/wave-10-android-job-models` — *feat(android): JARVIS job-state Kotlin models (Wave 10)* | `com.aci.hermes.model` (no `jarvis` subpackage) | 6 main + 5 test + 1 report | `apps/android/app/src/main/java/com/aci/hermes/model/` (JarvisGateStatus, JarvisJob, JarvisTask, JarvisTaskStatus, OwnerApprovalRequest, VerificationEvidence) |
| `aci/jarvis-prime-09-chat-voice-ui` — *W09: Add Jarvis Prime chat and safe voice capture UI* | `com.aci.hermes.ui.jarvis.chat`, `com.aci.hermes.ui.jarvis.voice` | 14 main + 3 test + 1 report | `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/{chat,voice}/` (ChatScreen + ChatMessage + ChatViewModel + Status pill + VoiceCaptureScreen + MicPermissionState + VoiceCaptureViewModel + VoiceTapButton + VoiceEducationContent) |
| `aci/wave-10-android-launch-audit` — *docs(aci): W10 Android launch audit* | (docs only) | 1 doc | `docs/aci/reports/W10_ANDROID_LAUNCH_AUDIT.md` |
| `aci/wave-10-android-approval-screen-plan` — *docs(aci): W10 plan — Android owner-approval screen (no code)* | (docs only) | 1 doc | `docs/aci/reports/W10_ANDROID_APPROVAL_SCREEN_PLAN.md` |

### Critical inter-PR conflicts that W01 surfaces

1. **`JarvisTask*` namespace collision between W05 and W10-job-models.**
   - `aci/jarvis-prime-05-android-models` defines `com.aci.hermes.model.jarvis.JarvisTaskCard`.
   - `aci/wave-10-android-job-models` defines `com.aci.hermes.model.JarvisTask`, `JarvisTaskStatus` (in the parent `com.aci.hermes.model` package).
   - Both have similar semantics ("a Jarvis task") but live in different sub-packages with overlapping responsibilities (status, risk, lifecycle). If both merge as-is, there will be two parallel `Task` models in the same module with no unified type.
   - **Resolution recommendation:** consolidate before either merges. Either:
     - move W10's `JarvisJob`/`JarvisTask`/`JarvisTaskStatus` into `com.aci.hermes.model.jarvis` to share package with W05, or
     - reframe W10's models as "job/gate" vocabulary (`JarvisJob`, `OwnerApprovalRequest`, `VerificationEvidence`) and drop the `JarvisTask*` overlap, deferring to W05's `JarvisTaskCard`.
   - This decision is **not** W01's to make; W01 surfaces it.

2. **No build, no compilation possible.** None of the four code-bearing
   branches above has committed `apps/android/build.gradle*`,
   `apps/android/settings.gradle*`, `apps/android/app/build.gradle*`,
   `apps/android/app/src/main/AndroidManifest.xml`, a Gradle wrapper, or
   `libs.versions.toml`. **Until the W02 scaffold sprint lands, none of
   these in-flight Kotlin files actually compiles.** Test files in
   `apps/android/app/src/test/...` are likewise dead until the scaffold
   exists.

3. **No `MainActivity`, no `JarvisPrimeApplication`, no `HermesService`,
   no nav graph, no theme.** The Compose surfaces on `aci/jarvis-prime-09-chat-voice-ui`
   are leaf screens that no `NavHost` yet hosts. Wiring them is W03's job.

4. **W10 audit overlap.** `docs/aci/reports/W10_ANDROID_LAUNCH_AUDIT.md`
   already documents "no Android app exists" from a launch-readiness
   angle. W01 differs in scope: W01 produces the **command-center
   implementation map** (files, packages, ownership, integration order),
   not the launch-readiness checklist. The two are complementary; W01
   defers signing-key, Play-Store, and publishing topics to W10.

### Direct file-name collisions with W01's ALLOWED FILES

None. The four ALLOWED FILES (`docs/aci/android/JARVIS_ANDROID_CURRENT_STATE_AUDIT.md`,
`JARVIS_ANDROID_SCREEN_MAP.md`, `JARVIS_ANDROID_FILE_OWNERSHIP_MAP.md`,
`docs/aci/reports/W01_ANDROID_AUDIT_REPORT.md`) are written by this
branch only.

---

## Item-by-item finding (the 10 mission targets)

| # | Target | Status on `origin/main` | Status across all branches |
|---|--------|--------------------------|-----------------------------|
| 1 | App package, stack, screens, services, repositories, models, navigation, settings, diagnostics, mock mode, gateway mode, Termux mode | absent | partial pre-scaffold under `com.aci.hermes.*` on five branches; no buildable module |
| 2a | `MainActivity` | NOT FOUND | NOT FOUND on any branch |
| 2b | `HermesService` (the foreground service) | NOT FOUND | NOT FOUND on any branch |
| 2c | `OrchestratorScreen` | NOT FOUND | NOT FOUND on any branch (W09 ships `ChatScreen`, not `OrchestratorScreen`) |
| 2d | Settings (screen + repository) | NOT FOUND | NOT FOUND on any branch |
| 2e | Diagnostics | NOT FOUND | NOT FOUND on any branch |
| 2f | Task repository | NOT FOUND | NOT FOUND on any branch; only data-class models (W05 `JarvisTaskCard`, W10 `JarvisTask`) — no Room, no DAO, no repository |
| 2g | App container / DI | NOT FOUND | NOT FOUND on any branch — no `Application` class, no Hilt, no manual `AppContainer` |
| 2h | Theme | NOT FOUND | NOT FOUND on any branch — no `ui/theme/*.kt`, no `res/values/themes.xml` |
| 2i | Navigation | NOT FOUND | NOT FOUND on any branch — no `NavHost`, no nav graph |
| 3a | Notification permission behavior | N/A (no manifest) | N/A — no manifest committed on any branch |
| 3b | Foreground service usage | N/A | N/A |
| 3c | Microphone | NOT REQUESTED at startup (no startup code exists) | W09 ships `MicPermissionState.kt` + `VoiceCaptureScreen.kt` that gate mic on user action — design-rule-compliant |
| 3d | SMS / Call-log absence | absent (no manifest, no code) | absent across all branches |
| 4 | Launch blockers | (no app to launch) | (no app to build) |
| 5 | Recommended folder structure | (see §"Recommended layout" + `JARVIS_ANDROID_FILE_OWNERSHIP_MAP.md`) | DOCUMENTED, aligned with `com.aci.hermes.*` package already in flight |
| 6 | File ownership map | (see `JARVIS_ANDROID_FILE_OWNERSHIP_MAP.md`) | DOCUMENTED |
| 7 | Integration order | (see ownership map) | DOCUMENTED |
| 8 | What must not be touched concurrently | (see ownership map §"Shared files") | DOCUMENTED |
| 9 | Build/test commands | (would fail today) | (would still fail after all in-flight PRs merge — no Gradle) |
| 10 | Auto-notification prompt at startup | N/A (no startup code) | N/A across all branches — design rule recorded for W02 |

---

## Design rules carried forward (Jarvis Prime global product rules)

These rules come from the sprint header and the CLAUDE.md project
instructions. They apply to every future Android PR (W02 onward) and
must be cited in PR descriptions when relevant.

### Identity & runtime split
- Product-facing name is **Jarvis Prime**.
- The Hermes name persists in the **Kotlin package root** (`com.aci.hermes`)
  for compatibility with in-flight work already on feature branches.
  Jarvis-Prime command-center surfaces live in sub-packages under
  `com.aci.hermes.{ui.jarvis,model.jarvis,service.jarvis,data.jarvis}`.
  Do **not** rename the root package — doing so would force collateral
  changes to every open Android PR.
- Android is the **body / control surface**, not the full AI brain.
- The AI brain stays in the Hermes/Jarvis backend (Python gateway, agent
  loop, skills, plugins). **No Python runtime is embedded inside the APK.**
- **No gateway-side secrets are stored in Android.** The app holds only
  client-side configuration (gateway URL, mock toggle, theme) and
  short-lived auth tokens issued by the gateway.

### Permissions (the non-negotiables)
- **No automatic notification permission prompt on first launch.**
  `POST_NOTIFICATIONS` is requested lazily, only when the user enables a
  feature that requires posting notifications (e.g. starts the
  `HermesService` foreground worker from the UI).
- **Microphone permission only after the user taps voice.** No
  pre-emptive `RECORD_AUDIO` request at app start, splash, or onboarding.
  The W09 PR's `MicPermissionState` + `VoiceCaptureScreen` already
  implement this pattern; W01 endorses that design.
- **No SMS, Call Log, or always-listening behavior.** The manifest (once
  it exists) must not declare `READ_SMS`, `RECEIVE_SMS`, `SEND_SMS`,
  `READ_CALL_LOG`, `WRITE_CALL_LOG`, `PROCESS_OUTGOING_CALLS`,
  `BIND_VOICE_INTERACTION`, or equivalent.
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

### Launch flow
- `MainActivity` (W02 scaffold owns its creation) boots to the
  Orchestrator route directly. No mandatory onboarding wall, no
  permission gauntlet, no required gateway configuration. Empty/mock
  state must work out of the box.
- `HermesService` (W05 service sprint owns) is **not** started in
  `MainActivity.onCreate`. It is started only when the user explicitly
  enables the gateway connection from the Orchestrator or Settings.

---

## Recommended layout (high-level — full tree in `JARVIS_ANDROID_FILE_OWNERSHIP_MAP.md`)

Package root: **`com.aci.hermes`** (matching in-flight PRs).
Source root: `apps/android/app/src/main/java/com/aci/hermes/`.

```
apps/android/                                # ← entire Gradle module is MISSING; W02 scaffold owns it
├── settings.gradle.kts
├── build.gradle.kts (root)
├── gradle.properties
├── gradle/
│   ├── wrapper/{gradle-wrapper.properties, gradle-wrapper.jar}
│   └── libs.versions.toml
├── gradlew, gradlew.bat
└── app/
    ├── build.gradle.kts
    ├── proguard-rules.pro
    └── src/
        ├── main/
        │   ├── AndroidManifest.xml          # ← MISSING, W02 owns
        │   ├── java/com/aci/hermes/
        │   │   ├── HermesApplication.kt     # @HiltAndroidApp or manual AppContainer host
        │   │   ├── MainActivity.kt
        │   │   ├── di/                      # DI surface
        │   │   ├── ui/
        │   │   │   ├── theme/               # Theme.kt, Color.kt, Type.kt
        │   │   │   ├── navigation/          # JarvisNavGraph.kt, JarvisRoutes.kt
        │   │   │   ├── components/
        │   │   │   └── jarvis/              # ← W09 already places Compose screens here
        │   │   │       ├── chat/            # W09 in flight
        │   │   │       ├── voice/           # W09 in flight
        │   │   │       ├── orchestrator/    # W03 to add
        │   │   │       ├── tasks/           # W08 to add
        │   │   │       ├── diagnostics/     # W07 to add
        │   │   │       └── settings/        # W06 to add
        │   │   ├── service/
        │   │   │   └── HermesService.kt
        │   │   ├── data/
        │   │   │   ├── gateway/             # GatewayClient + Mock + Termux
        │   │   │   └── prefs/               # UserPreferencesDataStore
        │   │   └── model/                   # ← W05 + W10 in flight here (collision)
        │   │       └── jarvis/              # W05 in flight
        │   └── res/values/{strings,colors,themes}.xml
        ├── test/java/com/aci/hermes/        # ← W05/W09/W10 already pre-place tests here
        └── androidTest/java/com/aci/hermes/
```

Stack recommendation (to be pinned by W02): Kotlin + Jetpack Compose +
Material 3, Compose Navigation, DataStore-Preferences, Room (for tasks),
OkHttp/Retrofit or Ktor (W04 picks one), Coroutines + Flow. DI strategy
(Hilt vs manual `AppContainer`) is a W02 decision; both layouts are
supported by the file map.

---

## Build/test contract

Once W02 scaffolds the module, the following commands MUST work from the
repo root. **Today they all fail** because `apps/android/` has no
`gradlew` and no build files.

```bash
cd apps/android && ./gradlew assembleDebug
cd apps/android && ./gradlew testDebugUnitTest
```

W01 itself does not run these. This is the documented "skipped tests"
justification for the W01 PR.

---

## Concurrency rules (what must not be touched concurrently)

W01 modifies **only** the four files under `docs/aci/android/` and
`docs/aci/reports/W01_ANDROID_AUDIT_REPORT.md`. There are no concurrent
edits to those files on any other branch (verified with
`git diff --name-only origin/main...<branch>` across all `aci/*` remotes).

For W02 onward, see `JARVIS_ANDROID_FILE_OWNERSHIP_MAP.md` for the
sprint-by-sprint owning-PR map and the list of shared integration files
(`AndroidManifest.xml`, the Application class, the nav graph,
`libs.versions.toml`, `app/build.gradle.kts`, `res/values/strings.xml`).

---

## Open questions (non-blocking for W01, blocking for W02)

- DI choice: Hilt vs manual `AppContainer`. **W02 decision.**
- Gateway HTTP client: Retrofit + OkHttp vs Ktor client. **W04 decision.**
- Persistence: Room vs DataStore-Proto for tasks. **W08 decision.**
- Application class name: `HermesApplication` (matches package root) vs
  `JarvisPrimeApplication` (matches product name). **W02 decision.**
  Recommendation: `HermesApplication` for code-side, with product
  branding via `<application android:label="Jarvis Prime">` in the
  manifest.
- `JarvisTask*` namespace conflict between W05 and W10 (see §"Concurrent
  work"). **Cross-PR resolution required before either merges.**
- Confirm the repository scope: the sprint header references
  `A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent`, but the active remote
  is `echerd27-design/hermes-agent`. Recorded for owner confirmation;
  user has approved auditing the active remote.

None of these block W01's documentation-only deliverable.

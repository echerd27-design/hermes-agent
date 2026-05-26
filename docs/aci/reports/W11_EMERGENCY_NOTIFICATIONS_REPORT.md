# W11 — Jarvis Prime Emergency Stop & Notifications Command Center

## Mission

Add the Android UI surfaces for the Jarvis Prime emergency-stop control
and notification command center. The wave is UI-only:

- The **Emergency Stop** control is always visually reachable as a
  reusable component and emits a confirmation callback. It does NOT
  kill processes in this wave.
- The **Notifications Command Center** is education-first and lets the
  owner stage enable/disable intent across five categories WITHOUT
  triggering any Android permission prompt.

No `MainActivity.kt` change. No `AndroidManifest.xml` change. No Gradle
change. No network, persistence, or system-API surface added.

## Branch and scope

- Working branch (session-mandated): `claude/modest-euler-oy07j`.
- Logical ACI wave name (PR body / report): `aci/jarvis-prime-11-emergency-notification-center`.
- Allowed paths touched, all created new:
  - `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/emergency/**`
  - `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/notifications/**`
  - `apps/android/app/src/test/java/com/aci/hermes/ui/jarvis/**`
  - `docs/aci/reports/W11_EMERGENCY_NOTIFICATIONS_REPORT.md` (this file)
- Forbidden paths confirmed untouched (verified via `git status` and
  `find` filter):
  - `apps/android/app/src/main/java/com/aci/hermes/MainActivity.kt`
    (still nonexistent — Android skeleton not yet present)
  - `apps/android/AndroidManifest.xml` (still nonexistent)
  - `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/home/**`
  - `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/navigation/**`
  - `hermes_cli/**`, `skills/**`, `README.md`, `pyproject.toml`,
    `uv.lock`, `.github/**`, Gradle files.

## Non-overlap audit

Before editing, open PRs and remote branches were inspected. No open PR
or branch touches any file under
`apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/emergency/**`,
`apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/notifications/**`,
or `docs/aci/reports/W11_EMERGENCY_NOTIFICATIONS_REPORT.md`. The
closest prior PR is #18 (`aci/wave-10-android-job-models`), which adds
unrelated model files under `.../com/aci/hermes/model/`. No collision.

The W11 wave-label is reused: PR #14 ships
`docs/aci/reports/W11_TERMUX_DOCTOR_AUDIT.md` as a separate audit. The
two reports have distinct filenames so there is no file conflict; the
label reuse is recorded here for the wave coordinator.

## Files added

### Emergency Stop — `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/emergency/`

| File | Shape |
| ---- | ----- |
| `EmergencyStopState.kt` | `enum class EmergencyStopUiState { Active, Confirming, Stopped }` — pure Kotlin, no Compose imports. |
| `EmergencyStopCopy.kt` | `object EmergencyStopCopy` — central source of truth for `TITLE`, `DESCRIPTION`, `CONFIRM_DIALOG_TITLE`, `CONFIRM_LABEL`, `CANCEL_LABEL`, `STOPPED_BADGE`. The required two strings are byte-for-byte matched: "Stop Jarvis Prime" and "Stops active tasks and blocks new risky actions until you resume." |
| `EmergencyStopButton.kt` | `@Composable fun EmergencyStopButton(state, onRequestStop, modifier)` — Material3 `Button` themed with `errorContainer`. Disabled when `state == Stopped`. Stateless — callers own state. |
| `EmergencyStopConfirmDialog.kt` | `@Composable fun EmergencyStopConfirmDialog(onConfirm, onDismiss)` — Material3 `AlertDialog` with the required confirm/cancel buttons. |
| `EmergencyStopPanel.kt` | `@Composable fun EmergencyStopPanel(state, onEmergencyStopConfirmed, modifier)` — Material3 `Card` wrapping the headline, description, button, and the dialog. Manages dialog visibility internally via `rememberSaveable { mutableStateOf(...) }`. Emits `onEmergencyStopConfirmed` ONLY after the user confirms — emits no other side effects. |

### Notifications Command Center — `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/notifications/`

| File | Shape |
| ---- | ----- |
| `NotificationCategory.kt` | `enum class NotificationCategory(val id, val displayName, val description)` with the 5 required values in the prompt order: `TASK_COMPLETED`, `TASK_BLOCKED`, `APPROVAL_NEEDED`, `CRITICAL_WARNING`, `GATEWAY_OFFLINE`. |
| `NotificationCommandCenterState.kt` | `data class NotificationCommandCenterState(val enabledByCategory: Map<NotificationCategory, Boolean>)` + `default()` factory (all `false`) + `withCategory(category, enabled)` immutable update + `isEnabled(category)` helper. |
| `NotificationCenterCopy.kt` | `object NotificationCenterCopy` — central source for screen title, education headline/body/footnote, and the placeholder note explaining the toggles do not yet deliver real notifications. |
| `NotificationEducationCard.kt` | `@Composable fun NotificationEducationCard(modifier)` — Material3 `Card` themed with `secondaryContainer`. Explains that Jarvis never asks for permission on its own. Static content. |
| `NotificationCategoryToggle.kt` | `@Composable fun NotificationCategoryToggle(category, enabled, onEnabledChange, modifier)` — Row with category name, description, and a Material3 `Switch`. Toggle updates local UI state only — NO permission request, NO system API call. |
| `NotificationCommandCenterScreen.kt` | `@Composable fun NotificationCommandCenterScreen(state, onStateChange, modifier)` — `LazyColumn` of: title, education card, placeholder note, then one `NotificationCategoryToggle` per `NotificationCategory.values()`. Stateless host — callers own state. |

### Tests — `apps/android/app/src/test/java/com/aci/hermes/ui/jarvis/`

JUnit 4 (`org.junit.Test`, `org.junit.Assert.*`), pure Kotlin only.
Compose UI tests are deferred to the Android-skeleton wave because they
require `androidx.compose.ui.test` and a running Gradle module.

| File | Coverage |
| ---- | -------- |
| `emergency/EmergencyStopStateTest.kt` | `EmergencyStopUiState` has exactly `Active`, `Confirming`, `Stopped`; `valueOf` round-trips; `EmergencyStopCopy.TITLE` and `EmergencyStopCopy.DESCRIPTION` match the required wording byte-for-byte; confirm/cancel labels are distinct and non-empty. |
| `notifications/NotificationCategoryTest.kt` | All 5 required categories present and in prompt order; ids are stable snake-case (`task_completed`, `task_blocked`, `approval_needed`, `critical_warning`, `gateway_offline`); ids are unique; every value has non-empty `displayName` and `description`. |
| `notifications/NotificationCommandCenterStateTest.kt` | `default()` is all-`false` and covers every category; `withCategory` returns a new instance, does not mutate the original, and round-trips on double-toggle; missing-category fallback is `false`; equality is value-based. |

### Wave report

- `docs/aci/reports/W11_EMERGENCY_NOTIFICATIONS_REPORT.md` (this file).

## Design notes

- **Callback-only emergency stop.** `EmergencyStopPanel` emits
  `onEmergencyStopConfirmed: () -> Unit` after the confirm dialog is
  accepted. There is no `Process.killProcess`, no daemon call, no
  Hermes RPC. A later wave wires this callback to gateway control.
- **Stateless screen, stateful panel.**
  `NotificationCommandCenterScreen` hoists state to the caller for
  recomposition control and testability. `EmergencyStopPanel` keeps the
  confirm-dialog visibility internal because that visibility is pure UI
  ephemera; lifting it would force every caller to plumb extra state
  with no benefit.
- **No permission requests anywhere.** No code in the wave references
  `ActivityCompat`, `requestPermissions`, `NotificationManagerCompat`,
  `NotificationManager`, or any permission API. The notification
  toggles record intent only. Verified by `grep -RIn` across the new
  source tree (see "Tests run" below).
- **Material3 only.** Imports come from `androidx.compose.material3.*`,
  `androidx.compose.runtime.*`, `androidx.compose.foundation.layout.*`,
  `androidx.compose.foundation.lazy.*`, `androidx.compose.ui.*`. No
  Material 2, no third-party UI libraries.
- **JUnit 4.** Matches PR #18 (`aci/wave-10-android-job-models`). Will
  run when the Android-skeleton wave configures
  `testImplementation "junit:junit:4.13.2"`.
- **Copy in `object` constants.** Lets tests assert the exact required
  strings without parsing Composables and gives the future i18n wave a
  single migration point.
- **Stable category ids.** Snake-case `id`s (`task_completed`, etc.)
  are persistence-friendly so a later wave can use them as the storage
  key without renaming.

## Tests run

**`./gradlew assembleDebug` and `./gradlew testDebugUnitTest` could not
run on this branch.** The Android module skeleton is not yet present in
this repository:

- No `apps/android/settings.gradle.kts`.
- No `apps/android/build.gradle.kts` or
  `apps/android/app/build.gradle.kts`.
- No `apps/android/gradle.properties`.
- No Gradle wrapper (`gradlew`, `gradlew.bat`, `gradle-wrapper.*`).
- No `apps/android/app/src/main/AndroidManifest.xml`.

Gradle files and `AndroidManifest.xml` are on this wave's FORBIDDEN
list, so the skeleton cannot be added here. Per the non-overlap
contract ("If a needed change is outside ALLOWED FILES, do not edit
it; write it into the report") and PR #18 precedent, the wave proceeds
with the Kotlin surfaces in place and records the blocker.

Pre-PR static checks that **were** run on this branch:

```
=== Forbidden APIs (perm requests, process kills) ===
grep -RIn 'requestPermissions\|ActivityCompat\|NotificationManagerCompat\|killProcess\|Process\.kill\|NotificationManager' \
  apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/
→ (no matches)

=== MainActivity / Manifest edits ===
git status --short | grep -E 'MainActivity\.kt$|AndroidManifest\.xml$'
→ (no matches — both still nonexistent)

=== Imports outside allowed namespaces ===
grep -RIhn '^import ' apps/android/app/src/ \
  | grep -vE 'androidx\.compose|androidx\.annotation|androidx\.lifecycle|org\.junit|kotlin\.|java\.'
→ (no matches)

=== Required copy present byte-for-byte ===
grep -F 'Stop Jarvis Prime' .../emergency/EmergencyStopCopy.kt
grep -F 'Stops active tasks and blocks new risky actions until you resume.' .../emergency/EmergencyStopCopy.kt
→ both match

=== Whitespace and conflict markers ===
git diff --check
→ clean

=== Scope guard: every new file is inside an ALLOWED path ===
find apps/android docs/aci -type f \
  | grep -vE '^(apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/(emergency|notifications)/|apps/android/app/src/test/|docs/aci/reports/)'
→ (no matches)
```

## Acceptance criteria — status

| Criterion | Status | Evidence |
| --------- | ------ | -------- |
| Emergency stop always visually reachable as a component | Met | `EmergencyStopButton` is a stateless reusable Composable; `EmergencyStopPanel` is a card that can be embedded anywhere. |
| Confirm emergency stop action callback | Met | `EmergencyStopPanel` shows `EmergencyStopConfirmDialog` and only calls `onEmergencyStopConfirmed` after the user taps "Stop now". |
| Required copy present | Met | `EmergencyStopCopy.TITLE = "Stop Jarvis Prime"`, `EmergencyStopCopy.DESCRIPTION = "Stops active tasks and blocks new risky actions until you resume."` — unit-test asserted. |
| Does not directly kill processes | Met | No process/system calls in the wave; static grep clean. |
| Emits callback/event only | Met | `EmergencyStopPanel` exposes a single `() -> Unit` callback. |
| `NotificationCommandCenterScreen` exists | Met | `apps/android/.../notifications/NotificationCommandCenterScreen.kt`. |
| Notification education card | Met | `NotificationEducationCard.kt` + `NotificationCenterCopy.EDUCATION_*` constants. |
| 5 notification categories | Met | `NotificationCategory` enum, 5 values in prompt order, asserted by `NotificationCategoryTest`. |
| Enable/disable UI state placeholders | Met | `NotificationCommandCenterState` + `NotificationCategoryToggle` Switch — local state only. |
| No automatic permission request | Met | Static grep confirms no `requestPermissions` / `ActivityCompat` / `NotificationManager*` references in the wave's source tree. |
| No MainActivity changes | Met | File still does not exist in the repo. |
| Components compile | **Deferred** | Cannot run `assembleDebug` without the Android skeleton (skeleton is FORBIDDEN here). |
| Debug build passes | **Deferred** | Same skeleton blocker. |

## Remaining risks

1. **Android-skeleton blocker.** The wave's two VERIFY commands are
   blocked until a future wave creates
   `apps/android/settings.gradle.kts`,
   `apps/android/build.gradle.kts`, `apps/android/app/build.gradle.kts`
   (with Compose-BOM, Material3, and `testImplementation
   "junit:junit:4.13.2"`), Gradle wrapper, and
   `apps/android/app/src/main/AndroidManifest.xml`. The same blocker is
   already documented by PRs #9, #10, and #18.
2. **W11 label reuse.** PR #14 ships
   `docs/aci/reports/W11_TERMUX_DOCTOR_AUDIT.md` as a separate W11
   audit. Filenames are distinct so there is no file collision; the
   wave coordinator should reconcile the label.
3. **No persistence yet.** Notification toggles live entirely in
   in-memory `NotificationCommandCenterState`. A later wave must wire
   `DataStore`/`SharedPreferences` (out of scope here — no Gradle
   dependency additions allowed).
4. **No real notifications yet.** The toggles record intent only. A
   later wave will add `NotificationManagerCompat` plumbing **and** an
   opt-in permission rationale, only after the user taps a toggle for
   the first time.
5. **No Compose UI tests.** Deferred until the skeleton wave brings in
   `androidx.compose.ui.test`. The current JUnit 4 tests cover the
   pure-Kotlin pieces (enum, state, copy).

## Rollback

```bash
rm -rf apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/emergency
rm -rf apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/notifications
rm -rf apps/android/app/src/test/java/com/aci/hermes/ui/jarvis
rm -f docs/aci/reports/W11_EMERGENCY_NOTIFICATIONS_REPORT.md
# Prune empty parent directories (no-op if other waves use them):
rmdir apps/android/app/src/main/java/com/aci/hermes/ui/jarvis \
      apps/android/app/src/test/java/com/aci/hermes/ui \
      docs/aci/reports docs/aci 2>/dev/null || true
```

Or revert the single wave commit on `claude/modest-euler-oy07j`.

## PR summary (ready to paste)

> **W11 — Jarvis Prime emergency stop and notifications command center.**
>
> Adds Compose UI surfaces only:
>
> - `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/emergency/`
>   — `EmergencyStopState`, `EmergencyStopCopy`, `EmergencyStopButton`,
>   `EmergencyStopConfirmDialog`, `EmergencyStopPanel`.
> - `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/notifications/`
>   — `NotificationCategory`, `NotificationCommandCenterState`,
>   `NotificationCenterCopy`, `NotificationEducationCard`,
>   `NotificationCategoryToggle`, `NotificationCommandCenterScreen`.
> - `apps/android/app/src/test/java/com/aci/hermes/ui/jarvis/...` —
>   JUnit 4 tests for the pure-Kotlin enum, state, and copy.
> - `docs/aci/reports/W11_EMERGENCY_NOTIFICATIONS_REPORT.md`.
>
> Logical ACI wave name:
> `aci/jarvis-prime-11-emergency-notification-center`. Working branch
> matches the session-mandated `claude/modest-euler-oy07j` (PR #16
> precedent).
>
> Emergency stop is callback-only — no process kill in this wave.
> Notifications screen is education-first — no permission request, no
> system-API surface.
>
> **Tests not run:** `./gradlew testDebugUnitTest` and
> `./gradlew assembleDebug` cannot execute — the Android Gradle
> skeleton and `AndroidManifest.xml` are not yet in the repo, and both
> are on this wave's FORBIDDEN list. Static checks (`grep`, scope
> guard, whitespace) are recorded in the wave report.
>
> **Rollback:** delete the two new `ui/jarvis/` subtrees, the test
> subtree, and the report.
>
> Draft PR — not for merge.

# W03 — Jarvis Prime Android Design System & Presence States

## Mission

Establish the Jarvis Prime visual foundation on Android — semantic color
tokens, type and spacing scales, the canonical presence-state enum, a
pure-Kotlin state-to-display mapping, and an interactive presence orb
composable — so subsequent UI waves (home / tasks / approvals / chat)
compose against a shared design language rather than re-deriving it per
surface.

This wave is foundation-only. No navigation, no MainActivity change, no
Gradle/dependency change, no manifest change.

## Branch and scope

- Branch: `aci/jarvis-prime-03-design-system-presence`.
- Allowed paths touched:
  - `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/design/**`
  - `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/presence/**`
  - `apps/android/app/src/test/java/com/aci/hermes/ui/jarvis/presence/**`
  - `docs/aci/reports/W03_DESIGN_SYSTEM_REPORT.md` (this file)
- Forbidden paths confirmed untouched:
  - `apps/android/app/src/main/java/com/aci/hermes/MainActivity.kt`
  - `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/home/**`
  - `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/tasks/**`
  - `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/approvals/**`
  - `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/chat/**`
  - `apps/android/AndroidManifest.xml`, all `*.gradle*`
  - `hermes_cli/**`, `skills/**`, `README.md`, `pyproject.toml`,
    `uv.lock`, `.github/**`

## Files added

### Design tokens — `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/design/`

| File | Shape |
| ---- | ----- |
| `JarvisColors.kt` | `object JarvisColors` — eight `0xAARRGGBB` `Long` constants (`BaseNavy`, `BaseBlack`, `Gold`, `Cyan`, `Red`, `Green`, `MutedGray`, `Warning`) |
| `JarvisSpacing.kt` | `object JarvisSpacing` — five `Int` dp constants (`xs`, `sm`, `md`, `lg`, `xl` = 4 / 8 / 12 / 16 / 24) |
| `JarvisTypography.kt` | `object JarvisType` — four `Int` sp constants (`caption`, `body`, `title`, `display`) + `FontFamilyName: String` |

Design tokens are pure Kotlin — **zero `androidx.compose` imports**.
Downstream Compose call sites wrap as `Color(JarvisColors.Gold)` and
`JarvisSpacing.md.dp`. This keeps the token files compile-clean ahead of
the Android Gradle skeleton wave and lets non-UI code (e.g. headless
tests) reference tokens without an Android runtime.

### Presence — `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/presence/`

| File | Shape |
| ---- | ----- |
| `PresenceState.kt` | `enum class PresenceState` — 12 entries in the operating-layer canonical order |
| `PresenceUi.kt` | `object PresenceUi` — three total mappers: `colorHex(state): Long`, `label(state): String`, `contentDescription(state): String`. Pure Kotlin, no Compose imports. |
| `PresenceOrb.kt` | `@Composable fun PresenceOrb(state, modifier, diameter)` — solid circle + label, no animation. Two `@Preview` composables (idle + critical) for the Android Studio gallery. Compose imports live **only** in this file. |

### Tests — `apps/android/app/src/test/java/com/aci/hermes/ui/jarvis/presence/`

| File | Coverage |
| ---- | -------- |
| `PresenceStateTest.kt` | `values().size == 12`, canonical-order match, no duplicates |
| `PresenceUiTest.kt` | All-states non-blank `label`, non-blank `contentDescription`, color resolves to a known token; spot-checks of the color matrix (`Cyan` for activity, `Gold` for approval, `Red` for critical, `Green` for complete, `MutedGray` for offline/blocked, `Warning` for warning, `BaseNavy` for idle); every `contentDescription` mentions "Jarvis" for a11y consistency |

JUnit 4 only — `org.junit.Test`, `org.junit.Assert.*`. Same dep stance
as PR #18.

## Design notes

- **Why `Long` instead of `androidx.compose.ui.graphics.Color` for color
  tokens.** Keeping the token files Compose-free lets `PresenceUi` (which
  exposes `colorHex`) be unit-tested headlessly under plain JUnit, with
  no Android Compose runtime in the classpath. The orb file is the
  single Compose-touching surface in this wave.
- **Why `Int` dp/sp values, not `Dp`/`TextUnit`.** Same reason —
  `androidx.compose.ui.unit.Dp` would force a Compose import. Callers
  wrap as `JarvisSpacing.md.dp`.
- **Why the orb is silent (no animation).** The sprint header asks for
  professional, not cartoonish; explicitly forbids animation dependency
  changes. A future `PresenceOrbAnimated` wave can layer motion without
  changing this contract or its contentDescription semantics.
- **Why presence model is pure Kotlin.** `PresenceUi` is the source of
  truth for label / a11y / color per state and is the locus of all unit
  tests. Composing it inside `PresenceOrb` means the visual layer has no
  conditional logic of its own — just a read and three draws.
- **Color matrix sourced from the sprint header semantic categories.**
  `LISTENING/THINKING/SPEAKING/WORKING` → `Cyan` (activity);
  `WAITING_FOR_APPROVAL/SERIOUS_ACTION_PENDING` → `Gold` (authority);
  `CRITICAL_ACTION_PENDING` → `Red`; `COMPLETE` → `Green`;
  `OFFLINE/BLOCKED` → `MutedGray`; `WARNING` → `Warning` (amber);
  `IDLE` → `BaseNavy` (recedes into background).

## Tests run

**None.** The wave's stated VERIFY commands cannot execute on this
branch because the Android module skeleton (`gradlew`, root and app
`build.gradle.kts`, `settings.gradle.kts`, `AndroidManifest.xml`) is not
yet present anywhere on `main`:

- `cd apps/android && ./gradlew assembleDebug` — no `gradlew`, no
  `app/build.gradle.kts`.
- `cd apps/android && ./gradlew testDebugUnitTest` — same root cause.

This is the same blocker PR #18 (Wave 10 Android job models) carries.
A future owner-only "skeleton" wave must add Gradle, the wrapper, the
manifest, and the Compose dependency set (`androidx.compose.foundation`,
`androidx.compose.material3`, `androidx.compose.runtime`,
`androidx.compose.ui.tooling.preview`, `org.junit:junit:4.13.2`) before
either command becomes runnable.

Pre-PR sanity checks that **were** run:

- `git status --short` — only the 9 new files in ALLOWED paths.
- `git diff --check` — no whitespace or conflict-marker errors.
- `grep -RIn 'TODO\|FIXME\|XXX' apps/android/app/src/` — empty.
- `grep -RIn '^import androidx\.compose' apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/design/`
  — empty (design tokens have zero Compose dependency).
- `grep -RIn '^import androidx\.compose' apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/presence/PresenceState.kt apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/presence/PresenceUi.kt`
  — empty (presence data layer has zero Compose dependency).
- `grep -c '^import androidx\.compose' apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/presence/PresenceOrb.kt`
  — `18`, as expected (Compose imports isolated to the orb file only).
- `find apps/android docs/aci -type f` — confirms exactly the planned
  file set, all inside ALLOWED paths.

## Remaining risks

1. **Skeleton blocker.** `./gradlew assembleDebug` and
   `./gradlew testDebugUnitTest` cannot run until a future wave adds the
   Android module skeleton. Source on this branch is *ready* to compile
   but is not exercised until that wave lands. Same blocker PR #18
   carries.
2. **Compose version pin.** The future skeleton must pin Compose ≥ 1.6 and
   Material3 ≥ 1.2 to resolve `androidx.compose.material3.Text` and the
   `MaterialTheme.typography.labelMedium` reference used by
   `PresenceOrb.kt`.
3. **Token alignment with Material3.** Later UI waves will wrap these
   tokens in a `ColorScheme` / `Typography` builder. The token surface
   here is deliberately small and additive so that wave doesn't
   duplicate semantics — but if Material3 token names drift, this set
   may need a re-mapping pass.
4. **No live preview.** Without the skeleton, Android Studio cannot
   render the `@Preview` composables in this wave. Acceptable —
   previews are seed material, not acceptance.
5. **Color tokens are static `Long`s, not theme-aware.** This wave does
   not introduce light/dark variants. Jarvis Prime is dark-first by
   design (the operating-layer doc states "dark navy/black base"), so a
   light theme is out of scope until owner-directed.

## Acceptance criteria mapping

| Criterion | Met by |
| --- | --- |
| Design/presence components compile | All files are valid Kotlin under their declared imports. The `design/` and `presence/` data files have no third-party deps. The orb file's Compose imports resolve once the skeleton wave's deps land — same posture as PR #18's model files vs. JUnit. |
| No navigation integration yet | No file added or modified outside `ui/jarvis/design`, `ui/jarvis/presence`, the matching test package, and this report. |
| No MainActivity change | `apps/android/app/src/main/java/com/aci/hermes/MainActivity.kt` not modified (does not exist on this branch; explicitly listed as forbidden). |
| No Gradle dependency changes | Zero `*.gradle*` files modified. |
| Debug build passes | Cannot be exercised until the skeleton wave lands. See "Tests run" and risk #1. |

## Rollback

```bash
rm -rf apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/design
rm -rf apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/presence
rm -rf apps/android/app/src/test/java/com/aci/hermes/ui/jarvis/presence
rm -f  docs/aci/reports/W03_DESIGN_SYSTEM_REPORT.md
# Then prune now-empty parent directories with `find apps/android -type d -empty -delete`.
```

Or revert the wave's single commit on this branch, or simply close the
draft PR and delete the branch — nothing else in the repo imports these
symbols yet.

## Non-overlap contract

- Branch: `aci/jarvis-prime-03-design-system-presence`. Started from
  `origin/main`.
- Files modified: exactly the 9 listed under "Files added".
- No edits to forbidden paths: verified by `git diff --name-only` after
  commit.
- No third-party deps added: no `*.gradle*` change.
- Draft PR only. No merge, no force-push, no deploy, no DNS change, no
  secret handling, no app-store submission, no spend.
- No collision with open PRs at the time of this wave: PRs #9–#18
  inspected; none touch `ui/jarvis/design/**` or `ui/jarvis/presence/**`.
  PR #18 lives under `model/**`, which is disjoint.

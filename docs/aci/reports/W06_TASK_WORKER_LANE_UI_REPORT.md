# W06 — Jarvis Prime Task Card + Worker Lane UI

## Mission

Wave 06 of the ACI sprint program. Ship reusable Jetpack Compose UI components that give the operator a glanceable read on what Jarvis Prime is doing — a card per task and a 7-stage worker-lane visualization — without wiring anything into navigation.

This wave is UI-only and additive. No backend, no navigation, no MainActivity edit, no Gradle change.

## Logical branch

Logical wave branch: `aci/jarvis-prime-06-task-worker-lane-ui`.

The harness assigned this session to `claude/gifted-babbage-4J9Ru` and pushes are restricted to that branch. The PR is opened from the harness branch; the PR body calls out the divergence so reviewers can map it back to the wave plan. Precedent: PR #16 used the same pattern.

## Skeleton-missing blocker (CRITICAL)

`apps/android/` does not exist on `origin/main` as of this commit. There is no Gradle skeleton:

- no `apps/android/build.gradle.kts`
- no `apps/android/settings.gradle.kts`
- no `apps/android/gradlew` / wrapper
- no `apps/android/app/src/main/AndroidManifest.xml`

PR #9 (W10 audit) confirmed the same fact. PR #18 (W10 models) ships Kotlin files under `apps/android/` without the skeleton and acknowledges in its body that `./gradlew assembleDebug` and `./gradlew testDebugUnitTest` cannot run on its branch.

**This wave follows that posture:**

- Ship code under allowed paths so a future skeleton wave can compile it.
- Document why VERIFY commands are skipped.
- Run static substitute checks as the compensating control.

A subsequent wave must add `apps/android/settings.gradle.kts`, `apps/android/build.gradle.kts`, `apps/android/app/build.gradle.kts`, `apps/android/gradle.properties`, the Gradle wrapper, and `apps/android/app/src/main/AndroidManifest.xml` before W06 and W10 VERIFY commands can be exercised.

## Allowed / forbidden compliance

Allowed paths (and only these) were touched:

- `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/tasks/**`
- `apps/android/app/src/test/java/com/aci/hermes/ui/jarvis/tasks/**`
- `docs/aci/reports/W06_TASK_WORKER_LANE_UI_REPORT.md`

Forbidden paths — verified absent or untouched:

- `apps/android/app/src/main/java/com/aci/hermes/MainActivity.kt` — not present.
- `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/{home,approvals,chat,memory,proof}/**` — not present.
- `apps/android/AndroidManifest.xml` — not present.
- `hermes_cli/**`, `skills/**`, `README.md`, `pyproject.toml`, `uv.lock`, `.github/**`, Gradle files — untouched.

`find apps/android -type f ! -path 'apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/tasks/*' ! -path 'apps/android/app/src/test/java/com/aci/hermes/ui/jarvis/tasks/*'` returns empty.

## Files added (21)

Production sources — `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/tasks/`:

| File | Purpose |
|---|---|
| `TaskPhase.kt` | Enum: 7 product phases (Intake, Planning, In progress, Review, Verifying, Published, Blocked). |
| `RiskTier.kt` | Enum: LOW, MODERATE, HIGH, CRITICAL with `displayLabel` and `severity`. |
| `WorkerLabel.kt` | Enum: 7 productized worker names (Planner, Navigator, Editor, Executor, Reviewer, Verifier, Publisher) + `pipeline` companion. |
| `WorkerLaneStageState.kt` | Sealed class: `Pending`, `Active`, `Done`, `Blocked(reason)`, `Skipped`. |
| `WorkerLaneUiState.kt` | Wrapper holding 7 ordered stages with constructor invariants. |
| `TaskCardUiState.kt` | View-model data class consumed by `JarvisTaskCard`. |
| `JarvisTasksTheme.kt` | Maps `RiskTier` / `WorkerLaneStageState` to Material 3 color roles. |
| `JarvisTaskCard.kt` | Top-level card composable + `@Preview` over the sample provider. |
| `JarvisWorkerLane.kt` | 7-stage horizontal pipeline composable + previews. |
| `TaskPhaseBadge.kt` | Phase chip composable + previews. |
| `RiskTierBadge.kt` | Risk chip composable + previews. |
| `BlockedReasonPanel.kt` | Blocked reason + unblock guidance composable + previews. |
| `EmptyTasksState.kt` | Empty-state placeholder composable + preview. |
| `JarvisTaskSampleData.kt` | 4 sample `TaskCardUiState` instances + `PreviewParameterProvider`. |

Test sources — `apps/android/app/src/test/java/com/aci/hermes/ui/jarvis/tasks/`:

| File | Asserts |
|---|---|
| `TaskPhaseTest.kt` | 7 values, non-blank labels, `BLOCKED` exists. |
| `RiskTierTest.kt` | 4 tiers, severity `[0,1,2,3]` ascending and unique, labels end with "risk". |
| `WorkerLabelTest.kt` | `pipeline` is exactly the 7 productized labels in product order; `order == index`; labels distinct; labels in the productized allowlist. |
| `WorkerLaneUiStateTest.kt` | `allPending()` is correct; constructor rejects wrong length and out-of-order stages; accepts canonical order; carries `Blocked` reason. |
| `JarvisTaskSampleDataTest.kt` | 4 entries, unique ids, blocked-reason / unblock-guidance consistency, published task has all stages Done, planning task has only Planner active, preview provider enumerates all. |
| `JarvisCopyGuardTest.kt` | Forbidden names (Claude, Codex, OpenHuman, HyperAgent, AutoGen, LangGraph, CrewAI, Paperclip) absent from sample data; "Jarvis Prime"/"Jarvis" present; worker labels productized. |

Report:

- `docs/aci/reports/W06_TASK_WORKER_LANE_UI_REPORT.md` (this file).

## Copy compliance

- All user-facing strings say "Jarvis Prime" or "Jarvis."
- Worker labels are exactly the productized set: `Planner, Navigator, Editor, Executor, Reviewer, Verifier, Publisher`.
- Forbidden names (case-insensitive) scanned in production and test sources: `Claude`, `Codex`, `OpenHuman`, `HyperAgent`, `AutoGen`, `LangGraph`, `CrewAI`, `Paperclip` — **0 hits.**
- Static guard test (`JarvisCopyGuardTest`) re-asserts these invariants at the data level.

## Design notes

- **Material 3 only.** All color comes from `MaterialTheme.colorScheme.*` via `JarvisTasksTheme.kt` (`riskTierContainer`, `riskTierOnContainer`, `stageContainer`, `stageOnContainer`). Zero `Color(0x…)` literals.
- **No PR #18 model dependency.** UI-layer types (`TaskPhase`, `RiskTier`, `WorkerLabel`, `WorkerLaneStageState`, `WorkerLaneUiState`, `TaskCardUiState`) live entirely inside `tasks/`. PR #18 separately introduces `com.aci.hermes.model.*` types; we don't import from there because that package isn't on `main` yet and importing would couple this PR to #18's merge order. A future adapter wave can bridge the two layers once both have landed.
- **No navigation integration.** The card and lane are pure composables with optional click callbacks; nothing references a `NavController`, `MainActivity`, or any route.
- **Backend-free.** Sample data lives in-memory; previews render against it.
- **JUnit 4 only** in tests, matching PR #18. No Robolectric, no Compose test rule, no `kotlin.test` — those would require the missing Gradle skeleton plus AGP test deps.

## Verification

| # | Command | Result |
|---|---|---|
| 1 | `git diff --name-only origin/main...HEAD` | Only allowed paths listed (`apps/android/app/src/{main,test}/java/com/aci/hermes/ui/jarvis/tasks/**` + this report). |
| 2 | `git diff --check` | **PASS** — clean. |
| 3 | `grep -RIEn 'Claude\|Codex\|OpenHuman\|HyperAgent\|AutoGen\|LangGraph\|CrewAI\|Paperclip' apps/android/app/src/{main,test}/java/com/aci/hermes/ui/jarvis/tasks` | **PASS** — 0 hits. |
| 4 | `grep -RIn 'Jarvis' apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/tasks \| wc -l` | **PASS** — 21 hits. |
| 5 | `grep -RIn 'Color(0x' apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/tasks` | **PASS** — 0 hits. |
| 6 | `grep -RIn 'import com.aci.hermes.model' apps/android/app/src/{main,test}/java/com/aci/hermes/ui/jarvis/tasks` | **PASS** — 0 hits. |
| 7 | `test -f apps/android/build.gradle.kts \|\| echo "skeleton missing"` | Prints `skeleton missing` — documented blocker. |
| 8 | `cd apps/android && ./gradlew assembleDebug` | **SKIPPED** — `gradlew` does not exist; skeleton blocker (see above). |
| 9 | `cd apps/android && ./gradlew testDebugUnitTest` | **SKIPPED** — same reason. |

Commands 1–6 plus a manual read of every file are the compensating control for this wave, identical to PR #18's posture.

## Risks

- **R1 — Cannot compile here.** No Gradle skeleton exists. Mitigation: minimal surface; Material 3 stable APIs only; no Hilt / coroutines / Flow; no third-party imports.
- **R2 — Package layout may shift** when a skeleton wave lands. Mitigation: root package mirrors PR #18 (`com.aci.hermes.…`).
- **R3 — Tests cannot execute.** Mitigation: invariants are inspectable; sample-data + enum tests are equivalent to typed assertions; static greps cover copy + dependency rules.
- **R4 — Branch-name divergence** between the logical wave branch and the harness-assigned branch. Mitigation: PR body calls it out, citing PR #16 precedent.
- **R5 — PR #18 may re-shape models** post-merge. W06 stays self-contained to avoid coupling; a future adapter wave can bridge if needed.

## Rollback

```bash
rm -rf apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/tasks
rm -rf apps/android/app/src/test/java/com/aci/hermes/ui/jarvis/tasks
rm    docs/aci/reports/W06_TASK_WORKER_LANE_UI_REPORT.md
git add -A && git commit -m "revert(W06): roll back task card + worker lane UI"
```

No skeleton or shared files are touched — rollback is fully local to this wave.

## Open questions

None blocking. Two follow-up waves are pre-implied by this work:

1. A skeleton wave (`build.gradle.kts` + AGP + Compose BOM + wrapper + `AndroidManifest.xml`) to unblock both W06 and W10 VERIFY commands.
2. An adapter wave (if/when PR #18 merges) to bridge `com.aci.hermes.model.*` and the UI-layer view-model types defined here.

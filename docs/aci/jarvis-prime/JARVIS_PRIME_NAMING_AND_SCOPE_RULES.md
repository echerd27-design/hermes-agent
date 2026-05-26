# Jarvis Prime Naming and Scope Rules

## Purpose

This is the hard-rule reference doc for Jarvis Prime. It defines canonical names, forbidden paths, naming patterns, scope walls, and the anti-pattern list that any reviewer can reject a PR for on sight.

This doc is companion to `JARVIS_PRIME_MASTER_BUILD_SPEC.md` and `JARVIS_PRIME_LAUNCH_WAVE_MAP.md` in the same directory.

## 1. Canonical names

| Surface | Canonical name | Where it appears | Where it must NOT appear |
| --- | --- | --- | --- |
| Product (user-facing) | **Jarvis Prime** | Android UI copy, push notifications, voice responses, app-store listing, marketing, onboarding, support copy. | n/a — this is the user-facing name. |
| Runtime / package / Python module | **Hermes** | `hermes_cli/**`, `hermes/**`, `tui_gateway/**`, `gateway/**`, Python imports, pyproject metadata, internal logs, dev CLI, dev tooling, repo identifier. Hermes is allowed to remain in code identifiers for package compatibility. | Android UI copy. Push notification text. Voice responses. App-store listing. Marketing. |
| Council subsystem | **AOS Council** | `.claude/agents/`, `skills/aos-enterprise-council/`, council routing in `docs/aos-jarvis-agent-routing.md`. The 9 runnable subagents listed by file name in `docs/aos-jarvis-agent-routing.md`. | n/a — this is the canonical name for the council. |
| Android app id namespace | `com.aci.hermes` (package-id convention already established by the in-flight Kotlin models PR) | `apps/android/app/build.gradle.kts`, Kotlin imports. | n/a — internal package id, not user-visible. |
| Event namespace | `aci.` prefix on every gateway event family. | Gateway events, runtime logs, Android event handlers. | Anywhere outside the gateway event bus. |

## 2. Forbidden paths

Any one of these in a diff is rejected on sight by any reviewer. The canonical Android module is `apps/android/` and only `apps/android/`. The repository contains exactly one Android module.

- `mobile/jarvis-prime-android/**` — explicitly forbidden by the W00 sprint header.
- `android/` at repo root — even though the recovered rule doc at `recovered-agent-sources/from-hazmat-command/rules/android-mobile-and-release-surface.md` references this path, that doc is recovered from a different project (a Capacitor app). The canonical path for this project is `apps/android/`.
- `JarvisPrimeAndroid/**` — any directory of this shape is rejected.
- `apps/jarvis-prime-android/**` — second Android module under a different name.
- `apps/android-v2/**`, `apps/android-new/**`, `apps/android-legacy/**` — any parallel Android module of any name. The repository contains exactly one Android module.
- Any embedded Python runtime, Termux APK bundle, or sideload-Python scheme inside the APK. The Android app does not host the AI brain.
- Manifest entries that activate `READ_SMS`, `READ_CALL_LOG`, accessibility services, or foreground-always-listening behavior in Phase 1.
- Any path that stores a gateway-side secret (token, signing key, API key, password) inside the APK. Includes `apps/android/app/src/main/res/values/strings.xml`, BuildConfig fields, asset files, or local properties checked into the tree.

## 3. Naming patterns

### Do

- Gateway event names: lower-snake under the `aci.` namespace. Examples: `aci.task.created`, `aci.approval.requested`, `aci.proof.decision`, `aci.estop.fired`.
- Kotlin model classes for app-facing data: `Jarvis*` prefix. Examples: `JarvisJob`, `JarvisTask`, `JarvisGateStatus`, `OwnerApprovalRequest`, `VerificationEvidence`. This convention is already established by the in-flight job-state models PR.
- Python module names under `hermes_cli/jarvis_prime/**`: lower-snake. Examples: `surfaces.py`, `specialists.py`, `verification.py`, `review_packets.py`, `ledger.py`.
- Doc filenames under `docs/aci/jarvis-prime/`: `SCREAMING_SNAKE.md` for the master spec, wave map, and naming rules. Wave reports under `docs/aci/reports/` use `W<NN>_TITLE.md`.
- Branch names: `aci/wave-<NN>-<short-slug>` for canonical waves listed in `JARVIS_PRIME_LAUNCH_WAVE_MAP.md`. Session-assigned `claude/*` branches are also allowed when the session harness mandates them; the W00 report records both names so the wave identity is preserved.

### Don't

- Don't rename existing Python identifiers like `hermes_cli` to `jarvis_cli`, or `tui_gateway` to `jarvis_gateway`. The W00 sprint header is explicit: "Hermes can remain only for backend/runtime/package compatibility." Mass renames break every importer and every downstream dependent without product benefit.
- Don't invent new agent names that are not in `skills/aos-enterprise-council/registry/AOS_AGENT_REGISTRY_COMPLETE.md`. The `CLAUDE.md` rule applies: "The 5 registry files are the source of truth — never improvise a council member that isn't in" the registry.
- Don't change the canonical 9-agent active council without owner sign-off. The 9 agents are listed in `docs/aos-jarvis-agent-routing.md`.
- Don't use "JARVIS" (all caps) in user-facing copy. The internal `JARVIS Prime Runtime` identifier is allowed inside backend code and developer docs; user-facing copy reads "Jarvis Prime".
- Don't shorten "Jarvis Prime" to "Jarvis" in user-facing copy. The product name is "Jarvis Prime".
- Don't introduce a new event namespace (for example, `jp.*` or `jarvis.*`). All gateway events use the `aci.` prefix.

## 4. Scope walls

Re-statement of the universal-header non-overlap contract plus the owner-only walls from `AGENTS.md` and the recovered Android rule. These walls are enforced by the Permission Kernel (see `JARVIS_PRIME_MASTER_BUILD_SPEC.md` section 2.8) and by reviewer judgment at PR time.

1. **Branch isolation.** Every wave works on the branch named in its sprint header. Cross-branch edits are out of scope.
2. **Allowed-files isolation.** Every wave touches only files listed in its sprint header. A change that needs a file outside the list is written into the wave report, not committed.
3. **No merge to main from a wave PR.** Every wave PR opens as draft. Merge is owner-only.
4. **No deploy, no publish, no DNS change, no app-store submission, no money action, no credential rotation from any wave.** These cross the owner-only walls. The Permission Kernel emits an `aci.approval.requested` event with critical tier; the owner approves in-app or out-of-band.
5. **No secrets in code, logs, docs, tests, fixtures, screenshots, or reports.** Placeholder token shapes (`xoxb-...`, `xapp-...`, `sk-...`) are allowed in documentation that explains setup; real tokens are never checked in.
6. **No force push to `main`.** No branch deletion on `main`. No mass file deletion across the repo.
7. **No skipping hooks.** No `--no-verify`, `--no-gpg-sign`, or hook-bypass flags. When a hook fails, fix the underlying issue.
8. **No second Android module.** Section 2 is exhaustive.
9. **No store submission inside any wave.** Including W30, which is the launch readiness review only. Store submission is a separate owner-only action after W30 passes.

## 5. Anti-patterns rejected on sight

This list is drawn from the recovered Android rule doc at `recovered-agent-sources/from-hazmat-command/rules/android-mobile-and-release-surface.md` and extended with W00-specific items.

- A commit that adds `vercel --prod`, `firebase deploy --only`, `eas submit`, `fastlane`, `gradlew bundleRelease` upload, or any other production-promote tooling without explicit owner approval recorded as `aci.approval.responded` at critical tier.
- A change to `vercel.json` that flips production routing without owner sign-off recorded in the proof history.
- A second Android module under any name (see section 2 for the exhaustive forbidden-path list).
- An Android module that embeds a Python runtime, ships a Termux APK as an asset, or schemes to sideload a Python interpreter at first launch.
- Calling the user-facing product "Hermes" or "JARVIS" in UI copy, voice, notifications, or app-store metadata.
- Storing a gateway secret, signing key, API token, or owner credential in the APK or in any file under `apps/android/**`.
- A new Android permission with no justifying code path. Every permission needs a feature that uses it; the feature cites the file path in the PR description.
- An Android-visible change that has not been walked on the live dev server, an emulator, or a built APK. If the change has not been verified end-to-end, the PR must say "I did not test on device" in the description rather than implying success.
- An automatic notification permission prompt on first launch. The system dialog is gated by the Notifications Command Center (see `JARVIS_PRIME_MASTER_BUILD_SPEC.md` section 5).
- A microphone permission request that fires before the owner taps the voice capture button.
- A release note that promises a future feature. Release notes are facts about what shipped; future commitments live in the wave map.
- A Capacitor or React Native dependency upgrade with no smoke test note.
- A council member invocation that names an agent not in `skills/aos-enterprise-council/registry/AOS_AGENT_REGISTRY_COMPLETE.md`.
- A rename of `hermes_cli` to `jarvis_cli` (or any equivalent mass rename of a Python package). Hermes remains in backend code identifiers; see section 3 "Don't".
- A wave PR that does not cite the spec section it satisfies and the wave id from `JARVIS_PRIME_LAUNCH_WAVE_MAP.md`.
- A wave PR that touches files outside its sprint-header allowed-files list. The needed change is written into the wave report instead.
- A wave PR that lands without a verification command, without a tests-run record, without a risks section, without a rollback plan, and without a draft PR summary.

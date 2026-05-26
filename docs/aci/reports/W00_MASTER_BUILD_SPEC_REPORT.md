# W00 — Master Build Spec Report

## 1. Mission

Create the master Jarvis Prime build specification that unifies product identity, architecture, Android screen map, risk and approval tiers, permission rules, gateway event contract, build-wave sequence, and launch definition into one launch-ready contract. Docs-only sprint. No source code changed.

## 2. Universal-header / non-overlap contract

- Branch worked on: `claude/inspiring-mayer-7gxea` (session-assigned development branch per the session harness).
- Sprint-header logical branch: `aci/jarvis-prime-00-master-build-spec` (recorded; not used as the actual push target because the session harness assigns its own branch).
- Base: `origin/main` at `7b8207740064b67901845696d8979a2662f6c29f`.
- `git fetch origin main`, `git status --short`, `git branch --show-current` run before any edit.
- Allowed files (all four created in this wave):
  - `docs/aci/jarvis-prime/JARVIS_PRIME_MASTER_BUILD_SPEC.md`
  - `docs/aci/jarvis-prime/JARVIS_PRIME_LAUNCH_WAVE_MAP.md`
  - `docs/aci/jarvis-prime/JARVIS_PRIME_NAMING_AND_SCOPE_RULES.md`
  - `docs/aci/reports/W00_MASTER_BUILD_SPEC_REPORT.md`
- Forbidden files (none touched): `apps/android/**`, `hermes_cli/**`, `skills/**`, `README.md`, `pyproject.toml`, `uv.lock`, `.github/**`, `build.gradle*`, `settings.gradle*`, package files.
- No merge to `main`. Draft PR only.
- No deploys. No publishes. No DNS changes. No app-store submission. No credential changes. No money actions.
- No secrets in code, logs, docs, tests, screenshots, fixtures, or this report.

## 3. Changed files

Exactly four files, all new. All four inside the allowed-files list.

```
A  docs/aci/jarvis-prime/JARVIS_PRIME_MASTER_BUILD_SPEC.md
A  docs/aci/jarvis-prime/JARVIS_PRIME_LAUNCH_WAVE_MAP.md
A  docs/aci/jarvis-prime/JARVIS_PRIME_NAMING_AND_SCOPE_RULES.md
A  docs/aci/reports/W00_MASTER_BUILD_SPEC_REPORT.md
```

## 4. What was done

- **JARVIS_PRIME_MASTER_BUILD_SPEC.md** — primary spec. Covers the eight numbered topics from the sprint header: product identity (Jarvis Prime user-facing, Hermes backend, Android body), architecture (nine components: Android app, gateway, runtime, build governor, native engineer, memory tree, context engine, permission kernel, proof history), Android screen map (eleven screens with consumed and emitted gateway events), risk and approval tiers (normal, serious, critical), permission rules (no startup notification prompt, education first, no SMS or call log or always-listening in Phase 1), event contract overview (six `aci.*` event families), build waves summary (cross-link to the wave map), launch definition (eleven items).
- **JARVIS_PRIME_LAUNCH_WAVE_MAP.md** — wave sequence W00 to W30. Part A is the in-flight PR reconciliation table mapping each currently open ACI PR to its canonical wave slot without renaming any PR. Part B is the canonical wave sequence with id, name, branch family, dependencies, allowed-files surface, parallel-safe siblings, integration-only flag, and owner-gate flag for every wave.
- **JARVIS_PRIME_NAMING_AND_SCOPE_RULES.md** — hard-rule reference. Canonical names, forbidden paths (exhaustive Android second-module list), naming patterns (do and don't), scope walls (nine), anti-patterns rejected on sight.
- **W00_MASTER_BUILD_SPEC_REPORT.md** — this report.

## 5. What was not done

- No source files were created or modified. No file under `hermes_cli/`, `apps/android/`, `gateway/`, `tui_gateway/`, `agent/`, `skills/`, `.claude/`, `.github/`, `scripts/`, `tests/`, or any other source tree.
- No `apps/android/` skeleton was created. That is W08 in the launch wave map, and W08 is an owner-gate wave.
- No in-flight PR was renamed, renumbered, force-pushed, closed, or merged. The reconciliation table in `JARVIS_PRIME_LAUNCH_WAVE_MAP.md` Part A is the bridge between current PR labels and the canonical wave slots; the PRs keep their current titles and branch names.
- No existing top-level Jarvis doc was modified. The master spec cross-links `docs/jarvis-prime-operating-system.md`, `docs/jarvis-verification-gates.md`, `docs/aos-jarvis-agent-routing.md`, `docs/memory-and-personality-policy.md`, `docs/mobile-voice-development-workflow.md`, `docs/slack-mobile-command-policy.md`, `docs/jarvis-code-operator-workflow.md`, and `docs/claude-codex-handoff-workflow.md`, but does not modify them.
- No `AGENTS.md` change. No `CLAUDE.md` change. No `README.md` change.

## 6. Current-state vs spec gaps

The spec is the contract; the current repo state has gaps the spec deliberately commits to closing in later waves.

- **`apps/android/` does not exist on `origin/main` or on the working branch.** Only the recovered Android rule doc at `recovered-agent-sources/from-hazmat-command/rules/android-mobile-and-release-surface.md` and its mirror under `skills/aos-enterprise-council/rules/` reference Android paths. The spec declares `apps/android/` as the canonical and only-legal Android path; the W08 wave creates the module skeleton, and W08 is an owner-gate wave.
- **Repo identifier mismatch.** The W00 sprint header says `A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent`. The working clone, the configured GitHub MCP scope, and the actual `origin` remote all point at `echerd27-design/hermes-agent`. This wave is docs-only and is not blocked by the mismatch, but owner reconciliation (rename, transfer, or fork) is needed before any later wave runs into push-permission issues. Tracked in section 12 as a blocking open question.
- **Branch name mismatch.** The W00 sprint header says `aci/jarvis-prime-00-master-build-spec`. The session harness assigns `claude/inspiring-mayer-7gxea` as the development branch. The actual push target is `claude/inspiring-mayer-7gxea`; the draft PR title is "W00: Jarvis Prime master build spec" so the wave identity is preserved in the PR title.
- **Wave-number collisions in in-flight PRs.** Two PRs share the W05 label; three PRs share the W10 label. Reconciliation is via the table in `JARVIS_PRIME_LAUNCH_WAVE_MAP.md` Part A. No in-flight PR is renamed by W00.

## 7. Verification

Verification is structural, not behavioral, because this is a docs-only sprint.

Commands run (or to be run) before opening the draft PR:

```
git fetch origin main
git status --short
git branch --show-current
git diff --stat origin/main...HEAD
git diff -- docs/aci/jarvis-prime/
git diff --name-only origin/main...HEAD
find docs/aci -type f
grep -RIn 'TODO\|FIXME\|XXX' docs/aci/
```

Expected results:

- `git diff --stat` shows exactly four added files, zero deleted, zero modified, total ~ 600 added lines.
- `git diff --name-only` returns exactly the four allowed paths and no path outside the allowed list.
- `find docs/aci -type f` returns exactly the four allowed paths.
- `grep -RIn 'TODO\|FIXME\|XXX' docs/aci/` returns empty.
- A secret-shaped-string grep over the four files (`grep -RIn 'sk-\|xoxb-\|xapp-\|ghp_\|github_pat_\|password\|api_key\|API_KEY' docs/aci/`) returns only the placeholder examples in section 3 of the naming and scope rules doc, which are documented as placeholder shapes used to forbid storing real tokens.

## 8. Tests run

None. This is a docs-only sprint. There is no source-code test to run. This is stated explicitly rather than as a skipped-test reason, per the universal-header rule "Every change needs validation or a clear skipped-test reason."

Structural verification (section 7) is the validation for this wave.

## 9. Risks

1. **Spec drift.** A later wave silently contradicts a §6 event name, a §3 architecture rule, or a §5 permission rule.
   - Mitigation: every later wave PR description must cite the spec sections it satisfies and the wave id from the wave map. Reviewers reject PRs that do not cite.
2. **Wave-map staleness.** In-flight PRs are merged out of order or with edited labels, and Part A of the wave map drifts.
   - Mitigation: Part A is a living table. On each merge or close of an in-flight PR, the row is updated. The W29 documentation polish wave includes a Part A audit.
3. **Owner-gate ambiguity.** W08, W23, W28, and W30 are owner-gate waves. If the owner-approval mechanism (in-app exact-phrase confirmation, biometric, nonce) is not delivered before W08, those gates have no in-app surface.
   - Mitigation: the Approvals screen is W16 and its plan is already drafted as a precursor (the W10-approval-screen plan PR). W08 itself is owner-gate via an out-of-band signal (e.g. signed-off PR description) until W16 lands. The W30 review re-checks every gate.
4. **Repo identifier reconciliation.** The W00 sprint header and the actual remote disagree on owner. Future pushes may fail or land in the wrong fork.
   - Mitigation: section 12 surfaces this as a blocking open question. The owner reconciles before any push that depends on the sprint-header identifier.
5. **Cross-link rot.** The master spec cross-links several top-level Jarvis docs by relative path. If any of those docs is renamed or moved by a future wave, the links rot.
   - Mitigation: any wave that renames or moves a top-level Jarvis doc must update the cross-links in the master spec in the same PR. This is recorded in the W29 documentation polish wave.

## 10. Rollback

This wave only adds new files; it modifies none. Rollback is a clean delete.

```
git rm docs/aci/jarvis-prime/JARVIS_PRIME_MASTER_BUILD_SPEC.md
git rm docs/aci/jarvis-prime/JARVIS_PRIME_LAUNCH_WAVE_MAP.md
git rm docs/aci/jarvis-prime/JARVIS_PRIME_NAMING_AND_SCOPE_RULES.md
git rm docs/aci/reports/W00_MASTER_BUILD_SPEC_REPORT.md
rmdir docs/aci/jarvis-prime docs/aci/reports docs/aci 2>/dev/null || true
git commit -m "revert: remove W00 master build spec"
```

Or close the draft PR without merging. No runtime state, no migration, no external service was touched, so the rollback has no downstream impact.

## 11. Draft PR summary

- Title: `W00: Jarvis Prime master build spec`.
- Base: `main`.
- Head: `claude/inspiring-mayer-7gxea`.
- Draft: yes. Not for merge.
- Body links to the three spec docs and to this report.
- Verification commands repeated in the PR body.
- Marked as docs-only.

## 12. Open questions (blocking)

1. **Repo identifier reconciliation.** Sprint header says `A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent`. Working clone, MCP scope, and `origin` remote are `echerd27-design/hermes-agent`. Owner decides: rename the GitHub repo to the sprint-header identifier, transfer the repo to a new owner, fork into a new org, or update the sprint header to match the current remote. This is blocking only for waves that depend on a specific owner identifier in CI or signing; W00 is not blocked.
2. **W08 Android-skeleton owner-gate.** Before any Android wave can land, the owner must approve: the canonical app id (`com.aci.hermes` is the convention already used by the in-flight Kotlin models PR; owner confirms or chooses a different id), the gradle plugin version pin, and the keystore custody plan placeholder (full keystore engineering is W28).
3. **In-flight PR canonical-slot confirmation.** The reconciliation table in `JARVIS_PRIME_LAUNCH_WAVE_MAP.md` Part A maps each current PR label to the canonical W00 slot. Owner confirms the mapping is correct before any in-flight PR is merged; the canonical-slot column does not rename any committed PR but does govern which wave that PR is treated as having delivered.

# Jarvis Prime Launch Wave Map

## Purpose

This document is the canonical wave sequence from W00 to W30 for the Jarvis Prime launch. It defines, for every wave, the wave id, the wave name, the branch family, the dependencies that must merge first, the allowed-files surface, the parallel-safe siblings, the integration-only flag, and the owner-gate flag.

It also reconciles the in-flight ACI PRs (which were opened before W00 landed and use ad-hoc wave numbers) against this canonical sequence, without renaming any committed PR.

The master spec is `JARVIS_PRIME_MASTER_BUILD_SPEC.md` in the same directory. The naming and scope rules are in `JARVIS_PRIME_NAMING_AND_SCOPE_RULES.md`. The W00 report lives at `docs/aci/reports/W00_MASTER_BUILD_SPEC_REPORT.md`.

## Part A — In-flight PR reconciliation

These PRs were opened before W00 landed. They use ad-hoc wave numbers (with two W05s and three W10s). The canonical wave slot in the right column is the slot this PR satisfies in the W00 sequence. **No in-flight PR is renamed or renumbered by W00.** The reconciliation table is the bridge; reviewers cross-reference the canonical slot when merging.

| PR title (current) | Current head branch | Current wave label | Canonical W00 slot | Notes |
| --- | --- | --- | --- | --- |
| aci/wave-04: surface adapter contract for JARVIS Prime turn results | `claude/hopeful-goodall-yvKgC` | W04 | **W01** | Surface adapters and the `JarvisTurn` shape are backend contract; canonical W01. |
| feat(jarvis-prime): deterministic specialist activation matrix | `claude/awesome-goldberg-zrzaA` | W07 | **W02** | Specialist activation matrix is backend contract; canonical W02. |
| feat(jarvis): add local verification packet helpers (ACI Wave 05) | `aci/wave-05-verification-packet` | W05 (a) | **W03a** | Verification packet evidence shape. |
| aci(wave-05): review packet schema for Codex reviewer tasks | `aci/wave-05-review-packet-schema` | W05 (b) | **W03b** | Review packet schema. Parallel-safe with W03a; same canonical wave, different files. |
| Wave 08: jarvis_prime append-only decision ledger helper | `aci/wave-08-decision-ledger` | W08 | **W03c** | Decision-ledger primitive. Parallel-safe with W03a and W03b. |
| docs(aci): W11 Termux + doctor install audit (read-only) | `aci/wave-11-termux-doctor-audit` | W11 | **W25 (audit)** | Audit is a precursor to W25; the reconciliation lands inside the W25 wave. |
| ACI W12: Dependency & Supply-Chain Posture Review (report only) | `aci/wave-12-dependency-review` | W12 | **W26 (audit)** | Audit is a precursor to W26. |
| docs(aci): W10 Android launch audit | `aci/wave-10-android-launch-audit` | W10 (a) | **W08 (audit)** | Android-skeleton audit. Precursor to the skeleton itself. |
| docs(aci): W10 plan — Android owner-approval screen (no code) | `aci/wave-10-android-approval-screen-plan` | W10 (b) | **W16 (plan)** | Approval-screen plan. Precursor to the Approvals screen wave. |
| feat(android): JARVIS job-state Kotlin models (Wave 10) | `aci/wave-10-android-job-models` | W10 (c) | **W10** | Job-state models. Already on the canonical W10 slot. Needs W08 to land first. |

Update rule for Part A: when an in-flight PR merges or is closed, flip its row to "merged" or "retired" and link the canonical wave it landed under.

## Part B — Canonical wave sequence

Every wave row carries: id, name, branch family, dependencies, allowed-files surface (high-level — exact lists are written in each wave's sprint header), parallel-safe siblings, integration-only flag, owner-gate flag.

### W00 — Master Build Spec

- Branch family: `aci/jarvis-prime-00-master-build-spec`.
- Dependencies: none.
- Allowed: `docs/aci/jarvis-prime/**`, `docs/aci/reports/W00_*`.
- Parallel-safe siblings: none.
- Integration-only: no.
- Owner-gate: no.
- Outcome: this spec, the wave map, the naming and scope rules, and the W00 report.

### W01 — Surface adapter contract

- Branch family: `aci/wave-01-surface-adapters`.
- Dependencies: W00.
- Allowed: `hermes_cli/jarvis_prime/__init__.py`, `hermes_cli/jarvis_prime/surfaces.py`, `tests/test_jarvis_prime_surfaces.py`, `docs/aci/reports/W01_*`.
- Parallel-safe siblings: W02, W03a, W03b, W03c.
- Integration-only: no.
- Owner-gate: no.
- Reconciles: PR titled "aci/wave-04: surface adapter contract for JARVIS Prime turn results".

### W02 — Specialist activation matrix

- Branch family: `aci/wave-02-specialist-activation`.
- Dependencies: W00.
- Allowed: `hermes_cli/jarvis_prime/__init__.py`, `hermes_cli/jarvis_prime/specialists.py`, `tests/test_jarvis_prime_specialists.py`, `docs/aci/reports/W02_*`.
- Parallel-safe siblings: W01, W03a, W03b, W03c.
- Integration-only: no.
- Owner-gate: no.
- Reconciles: PR titled "feat(jarvis-prime): deterministic specialist activation matrix".

### W03 — Backend evidence primitives (three parallel sub-waves)

- W03a — Verification packet helpers. Branch family: `aci/wave-03a-verification-packet`. Allowed: `hermes_cli/jarvis_prime/verification.py`, `tests/test_jarvis_prime_verification.py`, `docs/aci/reports/W03a_*`. Reconciles: PR titled "feat(jarvis): add local verification packet helpers (ACI Wave 05)".
- W03b — Review packet schema. Branch family: `aci/wave-03b-review-packet-schema`. Allowed: `hermes_cli/jarvis_prime/review_packets.py`, `tests/test_jarvis_prime_review_packets.py`, `docs/aci/reports/W03b_*`. Reconciles: PR titled "aci(wave-05): review packet schema for Codex reviewer tasks".
- W03c — Decision ledger. Branch family: `aci/wave-03c-decision-ledger`. Allowed: `hermes_cli/jarvis_prime/ledger.py`, `tests/test_jarvis_prime_ledger.py`, `docs/aci/reports/W03c_*`. Reconciles: PR titled "Wave 08: jarvis_prime append-only decision ledger helper".
- Dependencies for all three: W00.
- Parallel-safe siblings: W01, W02, and each other.
- Integration-only: no.
- Owner-gate: no.

### W04 — Memory Tree backend

- Branch family: `aci/wave-04-memory-tree`.
- Dependencies: W01, W03a, W03c.
- Allowed: `hermes_cli/jarvis_prime/memory/**` (new), `tests/test_jarvis_prime_memory_*`, `docs/aci/reports/W04_*`.
- Parallel-safe siblings: W06.
- Integration-only: no.
- Owner-gate: no.

### W05 — Context Engine backend

- Branch family: `aci/wave-05-context-engine`.
- Dependencies: W02, W04.
- Allowed: `hermes_cli/jarvis_prime/context.py` or `hermes_cli/jarvis_prime/context/**`, `tests/test_jarvis_prime_context_*`, `docs/aci/reports/W05_*`.
- Parallel-safe siblings: W06.
- Integration-only: no.
- Owner-gate: no.

### W06 — Permission Kernel backend

- Branch family: `aci/wave-06-permission-kernel`.
- Dependencies: W01, W03c.
- Allowed: `hermes_cli/jarvis_prime/kernel.py` or `hermes_cli/jarvis_prime/kernel/**`, `tests/test_jarvis_prime_kernel_*`, `docs/aci/reports/W06_*`.
- Parallel-safe siblings: W04, W05.
- Integration-only: no.
- Owner-gate: no.

### W07 — Gateway event-bus extensions

- Branch family: `aci/wave-07-gateway-event-bus`.
- Dependencies: W01 through W06.
- Allowed: `tui_gateway/**`, `hermes_cli/web_server.py`, `gateway/**`, `tests/test_gateway_aci_events.py`, `docs/aci/reports/W07_*`.
- Parallel-safe siblings: none.
- Integration-only: yes.
- Owner-gate: no.

### W08 — Android module skeleton

- Branch family: `aci/wave-08-android-skeleton`.
- Dependencies: W07.
- Allowed: `apps/android/**` (skeleton only — `settings.gradle.kts`, `build.gradle.kts`, `gradle.properties`, gradle wrapper, `apps/android/app/build.gradle.kts`, `apps/android/app/src/main/AndroidManifest.xml`, minimum `MainActivity.kt`), `docs/aci/reports/W08_*`.
- Parallel-safe siblings: none.
- Integration-only: yes.
- Owner-gate: yes (app id selection, package id permanence on Play; see the W08 audit reconciliation).
- Blocks: W09, W10, W11 through W23.

### W09 — Android networking and auth

- Branch family: `aci/wave-09-android-networking-auth`.
- Dependencies: W08, W07.
- Allowed: `apps/android/app/src/main/java/com/aci/hermes/net/**`, `apps/android/app/src/main/java/com/aci/hermes/auth/**`, `apps/android/app/src/test/java/com/aci/hermes/net/**`, `docs/aci/reports/W09_*`.
- Parallel-safe siblings: W10.
- Integration-only: no.
- Owner-gate: no.

### W10 — Android job-state models

- Branch family: `aci/wave-10-android-job-models`.
- Dependencies: W08.
- Allowed: `apps/android/app/src/main/java/com/aci/hermes/model/**`, `apps/android/app/src/test/java/com/aci/hermes/model/**`, `docs/aci/reports/W10_*`.
- Parallel-safe siblings: W09.
- Integration-only: no.
- Owner-gate: no.
- Reconciles: PR titled "feat(android): JARVIS job-state Kotlin models (Wave 10)" (already drafted; needs W08 to land first).

### W11 through W21 — One wave per Android screen

Screen order matches `JARVIS_PRIME_MASTER_BUILD_SPEC.md` section 3:

| Wave | Screen | Branch family | Parallel-safe with |
| --- | --- | --- | --- |
| W11 | Home | `aci/wave-11-android-home` | W12 |
| W12 | Chat | `aci/wave-12-android-chat` | W11 |
| W13 | Voice Capture | `aci/wave-13-android-voice` | W14 |
| W14 | Tasks | `aci/wave-14-android-tasks` | W13 |
| W15 | Worker Lane | `aci/wave-15-android-worker-lane` | W16 |
| W16 | Approvals | `aci/wave-16-android-approvals` | W15 |
| W17 | Memory Transparency | `aci/wave-17-android-memory-transparency` | W18 |
| W18 | Proof History | `aci/wave-18-android-proof-history` | W17 |
| W19 | Emergency Stop | `aci/wave-19-android-estop` | W20 |
| W20 | Control / Settings | `aci/wave-20-android-control-settings` | W19 |
| W21 | Notifications Command Center | `aci/wave-21-android-notifications-center` | none (must be late so the Notifications channel design is final) |

- Dependencies for every row: W09, W10.
- Allowed for every row: `apps/android/app/src/main/java/com/aci/hermes/ui/<screen>/**`, the corresponding test path, and `docs/aci/reports/W<NN>_*`.
- W16 reconciles: PR titled "docs(aci): W10 plan — Android owner-approval screen (no code)" (which becomes the W16 plan precursor).
- Integration-only: no.
- Owner-gate: no.

### W22 — Permission education flow

- Branch family: `aci/wave-22-permission-education`.
- Dependencies: W08.
- Allowed: `apps/android/app/src/main/java/com/aci/hermes/ui/permission/**`, the corresponding test path, `docs/aci/reports/W22_*`.
- Parallel-safe siblings: W11 through W21 once W09 and W10 land.
- Integration-only: no.
- Owner-gate: no.

### W23 — Push / notification channel

- Branch family: `aci/wave-23-android-push`.
- Dependencies: W08, W22.
- Allowed: `apps/android/app/src/main/java/com/aci/hermes/push/**`, the corresponding test path, `docs/aci/reports/W23_*`.
- Parallel-safe siblings: none.
- Integration-only: no.
- Owner-gate: yes (vendor selection for push delivery; no third-party SDK without owner sign-off).

### W24 — End-to-end integration sweep on emulator

- Branch family: `aci/wave-24-e2e-emulator`.
- Dependencies: W08, W09, W10, W11 through W23.
- Allowed: `apps/android/app/src/androidTest/**`, `docs/aci/reports/W24_*`.
- Parallel-safe siblings: none.
- Integration-only: yes.
- Owner-gate: no.

### W25 — Termux and doctor reconciliation

- Branch family: `aci/wave-25-termux-doctor`.
- Dependencies: W00, W01 through W06 (for behavior captured in the in-flight audit).
- Allowed: `scripts/install.sh`, `SETUP.md`, `hermes_cli/doctor.py`, `constraints-termux.txt`, `pyproject.toml` (Termux extras only), `docs/aci/reports/W25_*`.
- Parallel-safe siblings: W26.
- Integration-only: no.
- Owner-gate: no.
- Reconciles: the Termux doctor audit PR (currently labelled W11).

### W26 — Dependency and supply-chain hardening

- Branch family: `aci/wave-26-dependency-hardening`.
- Dependencies: W00.
- Allowed: per-PR — only one file from `pyproject.toml`, `uv.lock`, `constraints-termux.txt`, `package.json`, `package-lock.json`, `flake.nix`, `flake.lock`, `Dockerfile`, or `.github/dependabot.yml`; plus `docs/aci/reports/W26_*`. Dep changes follow the "dependency-only PR" rule (one supply-chain change per PR).
- Parallel-safe siblings: W25, W27.
- Integration-only: no.
- Owner-gate: no.
- Reconciles: the supply-chain audit PR (currently labelled W12).

### W27 — CI hardening

- Branch family: `aci/wave-27-ci-hardening`.
- Dependencies: W00.
- Allowed: `.github/workflows/**`, `docs/aci/reports/W27_*`.
- Parallel-safe siblings: W25, W26.
- Integration-only: no.
- Owner-gate: no.

### W28 — Release engineering

- Branch family: `aci/wave-28-release-engineering`.
- Dependencies: W08, W23, W27.
- Allowed: `apps/android/app/build.gradle.kts` (signing config, build flavors), `apps/android/release/**` (keystore custody docs only — no keystore checked in), `docs/aci/reports/W28_*`.
- Parallel-safe siblings: none.
- Integration-only: no.
- Owner-gate: yes (keystore custody, build flavor isolation, package id finalization). No store submission.

### W29 — Documentation polish

- Branch family: `aci/wave-29-docs-polish`.
- Dependencies: W21 (for screenshots), W24 (for verified flows).
- Allowed: `docs/aci/jarvis-prime/**` (additive only), `docs/aci/reports/W29_*`, top-level Jarvis docs (additive cross-links only — no rewrites without owner sign-off).
- Parallel-safe siblings: W30 planning.
- Integration-only: no.
- Owner-gate: no.

### W30 — Launch readiness review

- Branch family: `aci/wave-30-launch-readiness`.
- Dependencies: every wave above.
- Allowed: `docs/aci/reports/W30_*` only.
- Parallel-safe siblings: none.
- Integration-only: yes.
- Owner-gate: yes. The owner approves go or no-go. No store submission inside W30. Store submission is a separate owner-only action after W30 passes.

## End notes

- Final merge target is `main` for every wave. There is no release branch.
- Integration-only waves: W07, W08, W24, W30.
- Owner-gate waves: W08, W23, W28, W30.
- Every Android wave (W08 through W23 and W28) lives under `apps/android/**` and only `apps/android/**`. Any other Android path is rejected on sight; see `JARVIS_PRIME_NAMING_AND_SCOPE_RULES.md` section 2.
- Each wave PR description must cite the spec sections it satisfies and the wave id from this map.

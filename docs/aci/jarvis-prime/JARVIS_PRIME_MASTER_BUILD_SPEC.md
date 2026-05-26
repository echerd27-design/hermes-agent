# Jarvis Prime Master Build Specification

## Purpose

This document is the master build specification for Jarvis Prime. It unifies the product identity, architecture, Android screen map, risk and approval tiers, permission rules, gateway event contract, build-wave sequence, and launch definition into one launch-ready contract. Every Jarvis Prime wave that follows W00 must conform to this specification. Conformance is verified at PR review by citing the section number this PR satisfies.

This spec references and indexes the existing top-level Jarvis docs (`docs/jarvis-prime-operating-system.md`, `docs/jarvis-verification-gates.md`, `docs/aos-jarvis-agent-routing.md`, `docs/memory-and-personality-policy.md`, `docs/mobile-voice-development-workflow.md`, `docs/slack-mobile-command-policy.md`, `docs/jarvis-code-operator-workflow.md`). It does not duplicate them and does not silently contradict them.

Companion documents in the same directory:

- `JARVIS_PRIME_LAUNCH_WAVE_MAP.md` — the canonical wave sequence W00 to W30 with dependencies, parallel-safe siblings, integration-only flags, and the reconciliation table for in-flight PRs.
- `JARVIS_PRIME_NAMING_AND_SCOPE_RULES.md` — canonical names, forbidden paths, naming patterns, scope walls, and the anti-pattern list.

The W00 report lives at `docs/aci/reports/W00_MASTER_BUILD_SPEC_REPORT.md`.

## 1. Product Identity

Jarvis Prime is the user-facing AI operating partner. Hermes is the backend, runtime, and execution shell. The Android app is the command center, body, and control surface — not the AI brain.

| Surface | Identifier | Where it appears |
| --- | --- | --- |
| User-facing product name | **Jarvis Prime** | Android UI copy, push notifications, voice responses, app-store listing, marketing, onboarding screens, support copy. |
| Backend / runtime / package | **Hermes** | Python package paths (`hermes_cli/`, `hermes/`), gateway endpoints, internal logs, developer CLI, dev tooling, repo identifier. Hermes is allowed to remain in code identifiers for package compatibility and is not removed. |
| Council subsystem | **AOS Council** | `.claude/agents/`, `skills/aos-enterprise-council/`, council routing in `docs/aos-jarvis-agent-routing.md`. |

The Android app is the body. It captures voice and text input, renders Jarvis Prime's output, surfaces approvals, shows the proof history, and exposes the emergency stop. It does not host the LLM, does not host the council, does not host the memory tree, and does not embed a Python runtime. The brain lives in the Hermes backend.

See `docs/jarvis-prime-operating-system.md` for the operating-partner identity rules and the operating hierarchy already established in the repo.

## 2. Architecture

Jarvis Prime is composed of nine components. The high-level data flow is:

```text
Owner
↓
Jarvis Prime Android App   <----- push / WebSocket events ----- Gateway / Event Spine
↓                                                                ↑      ↑
chat / voice / approvals / estop ------- HTTPS ---------------->  |      |
                                                                  |      |
                              JARVIS Prime Runtime <-------------- |      |
                                       ↓                                  |
                              ACI Build Governor ---------> Hermes Native Engineer
                                       ↓                                  |
                              Context Engine <-------- Memory Tree        |
                                       ↓                                  |
                              Permission Kernel (gates every action) <----+
                                       ↓
                              Proof / Audit History (append-only)
```

The nine components are defined below. Each component declares its responsibility, where it lives, its inputs, and its outputs.

### 2.1 Jarvis Prime Android App

Responsibility: capture owner input (chat, voice, taps), render Jarvis Prime output (text, voice, cards), surface approvals and the emergency stop, expose memory transparency and proof history.

- Lives at `apps/android/` and only `apps/android/`. The repository contains exactly one Android module.
- Compose UI. Kotlin. Owner-only auth. Talks only to the Gateway over TLS.
- Does not embed a Python runtime. Does not store gateway-side secrets. Does not implement risk decisioning, council routing, memory storage, or LLM inference.
- Cross-links: the Android launch audit (current draft at W10 audit PR) and the Android approval-screen plan (current draft at W10 approval-screen PR) describe the screen-level details.

### 2.2 Gateway / Event Spine

Responsibility: the single point of contact between Android and the backend; carries every event in section 6.

- Lives at `tui_gateway/ws.py:19` and `hermes_cli/web_server.py:86-107` today.
- Surfaces: WebSocket for live events, HTTPS for request/response.
- All `aci.*` events flow through here. Adding a second transport, a second port, or a second protocol family is out of scope for Phase 1.

### 2.3 JARVIS Prime Runtime

Responsibility: hosts the operating partner; the daemon that receives owner input, asks the build governor what to do, drives the worker lane, updates memory, and emits events.

- Cross-link: `docs/jarvis-prime-operating-system.md` defines the operating-partner identity, the hierarchy (Owner → Mobile → JARVIS Prime → AOS Council Director → Specialists → Workers → Outputs), and the specialist set.
- Lives inside the Hermes process; not a separate service.

### 2.4 ACI Build Governor

Responsibility: deterministic decision layer that classifies each owner request as one of: direct answer, council review packet, build packet for the Hermes Native Engineer, memory note, or approval-required.

- The specialist-activation matrix is implemented in `hermes_cli/jarvis_prime/specialists.py` (current draft at the specialist-activation PR).
- The router that consumes the matrix lives in `hermes_cli/jarvis_prime/router.py` (later wave).
- Decisions are deterministic for a given input plus context, and every decision emits an `aci.proof.*` ledger entry.

### 2.5 Hermes Native Engineer

Responsibility: worker lane that executes scoped build packets — code edits, test runs, PR drafts, repo audits — and returns evidence.

- Operates over the existing `agent/` and `hermes_cli/` modules; W00 does not change them.
- Worker turns emit `aci.worker.*` events and produce verification-packet evidence (see section 6).
- Workers do not own approval and never cross owner-only walls.

### 2.6 Memory Tree

Responsibility: local-first memory store for Jarvis Prime.

- Tree shape at the spec level: `root -> epochs -> episodes -> facts`. Each fact carries a source, a timestamp, an optional expiry, and a confidence flag.
- Cross-link: `docs/memory-and-personality-policy.md` defines the policy (what is remembered, what is corrected, what is forgotten).
- Storage implementation is owned by the Memory Tree backend wave (see the launch wave map). W00 does not choose a storage engine.

### 2.7 Context Engine

Responsibility: per-turn context assembly — mission, retrieved memory, active specialists, active gates, recent proof events — fed to the runtime before every response.

- Reads from the Memory Tree, the AOS council registry, the decision ledger, and the gate state.
- Output is a single context bundle the runtime hands to the LLM provider or to the build governor.

### 2.8 Permission Kernel

Responsibility: enforces every owner-only wall before any action that crosses one.

- Wall set (re-stated from `AGENTS.md` owner-only walls and the recovered Android rule doc):
  - No Play Store / App Store submission.
  - No production deploy or production-promote action.
  - No DNS change.
  - No money action, no payment, no subscription change.
  - No credential rotation or secret write.
  - No secret in non-owner code paths, logs, screenshots, fixtures, or reports.
  - No force push to `main`. No branch deletion on `main`. No mass file deletion.
- Every wall check emits an `aci.proof.*` entry (kernel decision + outcome). A blocked attempt is also an event, not a silent denial.

### 2.9 Proof / Audit History

Responsibility: append-only ledger of every decision, every approval, every gate result, every worker turn, every override.

- Ledger primitive lives in `hermes_cli/jarvis_prime/ledger.py` (current draft at the decision-ledger PR).
- Verification-packet evidence lives in `hermes_cli/jarvis_prime/verification.py` (current draft at the verification-packet PR).
- The Android Proof History screen renders the ledger and the verification packets to the owner.

## 3. Android Screen Map

Eleven screens. Each row lists the screen, its purpose, the gateway events it consumes, the gateway events it emits, and the owner-only or permission notes that gate its use.

| Screen | Purpose | Consumes | Emits | Owner-only / permission notes |
| --- | --- | --- | --- | --- |
| Home | Landing surface; quick status; one-tap entries to Chat, Approvals, Proof History, Emergency Stop. | `aci.task.*`, `aci.approval.*`, `aci.estop.*` | none | None. Always reachable, no permission gate. |
| Chat | Text conversation with Jarvis Prime. | `aci.task.*`, `aci.worker.*` | `aci.task.created` | None. |
| Voice Capture | Voice input; transcript display; voice playback. | `aci.task.*` | `aci.task.created` | Microphone requested only after the owner taps the voice button. App fully functional if denied. |
| Tasks | Active and recent task list with status. | `aci.task.*` | none | None. |
| Worker Lane | Live view of Hermes Native Engineer worker turns; pause and resume controls. | `aci.worker.*` | `aci.worker.paused`, `aci.worker.resumed` | None. |
| Approvals | Pending owner approvals with exact-phrase confirmation, biometric, and nonce. | `aci.approval.requested` | `aci.approval.responded` | Biometric required for critical-tier responses. See section 5. |
| Memory Transparency | Read-only view of the Memory Tree; what is remembered, why, and from where. | `aci.memory.*` | none | None. |
| Proof History | Append-only render of the decision ledger and verification packets. | `aci.proof.*` | none | None. |
| Emergency Stop | One large button; halts all worker lanes and pauses the runtime. | `aci.estop.status` | `aci.estop.fired`, `aci.estop.cleared` | Always reachable from Home in one tap. No biometric for fire. Biometric for clear. |
| Control / Settings | App configuration: gateway endpoint, owner identity, permission education entry points. | none | none | Each permission has a dedicated education screen before the system dialog. |
| Notifications Command Center | In-app surface that lists what would have been a notification; the owner controls whether the system notification channel is enabled. | `aci.task.*`, `aci.approval.requested`, `aci.estop.*` | none | No automatic notification permission prompt on first launch. The system dialog appears only after the owner enables notifications from this screen. |

Each screen above is delivered by its own wave in the launch wave map (see W11 through W21 in `JARVIS_PRIME_LAUNCH_WAVE_MAP.md`).

## 4. Risk and Approval Tiers

Every action Jarvis Prime considers is classified into one of three tiers. The tier determines the gate the Permission Kernel applies.

| Tier | Examples | Automation rule | Gate |
| --- | --- | --- | --- |
| Normal | Read a file, plan, draft a response, propose a change, summarize, search memory, render a screen. | Auto-approve. | None. Emits `aci.proof.decision` only. |
| Serious | Write code, open a draft PR, run tests, modify the Memory Tree, change a recurring rule, send a Slack draft, schedule a job. | Confirm in app with one tap. | Approvals screen, one-tap approve, no biometric, no exact phrase. Emits `aci.approval.requested` then `aci.approval.responded`. |
| Critical | Anything behind an owner-only wall: deploy, publish, DNS change, money action, credential rotation, app-store submission, force push, branch deletion, mass file deletion, removing a permission wall, modifying the kernel itself. | Never auto. Never one-tap. | Server-issued exact-phrase confirmation, NFKC-normalized, paste-blocked, autofill-blocked; biometric within 30 seconds; nonce-bound. Cross-link: the Android approval-screen plan (current draft at the W10 approval-screen PR). |

Tier promotion rule: when a request is ambiguous between Serious and Critical, the kernel promotes it to Critical. Demotion requires an explicit allowlist entry signed off by the owner.

## 5. Permission Rules

Phase 1 permission discipline. These rules are non-negotiable for the launch checklist (section 8) to pass.

1. **No startup notification prompt on first launch.** The system notification dialog appears only after the owner enables notifications from the Notifications Command Center.
2. **Permission education first.** Every permission has a dedicated education screen that explains what the permission unlocks before the system dialog is presented.
3. **No SMS read, no Call Log read, no always-listening behavior in Phase 1.** These manifest entries are forbidden.
4. **Microphone permission is requested only after the owner taps the voice capture button.** The Voice Capture screen renders the education entry, then the system dialog.
5. **Camera, location, contacts, storage are optional.** The app must still work fully if any of them is denied. Features that depend on a denied permission must degrade gracefully and tell the owner why a feature is unavailable.
6. **No third-party SDK that requires additional permissions or that phones home.** All telemetry is local; the Proof History is the only audit surface.

Cross-link: `docs/mobile-voice-development-workflow.md` and the recovered Android rule at `recovered-agent-sources/from-hazmat-command/rules/android-mobile-and-release-surface.md`.

## 6. Event Contract Overview

The gateway carries six event families under the `aci.` namespace. Event names are lower-snake. Every event carries a `version`, a `ts` epoch-ms, an `event` name, a `payload` object, and an `actor` (owner, runtime, worker, kernel, governor).

### 6.1 `aci.task.*` — task lifecycle

- `aci.task.created` — owner submitted a task. Payload: id, mode, input summary.
- `aci.task.classified` — build governor assigned a tier and a worker plan. Payload: id, tier, plan summary.
- `aci.task.completed` — terminal state. Payload: id, outcome, evidence references.
- Producer: runtime, build governor, worker. Consumer: Home, Chat, Tasks, Worker Lane.

### 6.2 `aci.approval.*` — owner approvals

- `aci.approval.requested` — kernel requires owner confirmation. Payload: id, tier, action description, exact-phrase token (server-issued), nonce, expires-at.
- `aci.approval.responded` — owner approved, denied, or deferred. Payload: id, response, reason if denied.
- Producer: Permission Kernel. Consumer: Approvals, Notifications Command Center.
- Cross-link: the Android approval-screen plan (current draft at the W10 approval-screen PR).

### 6.3 `aci.memory.*` — Memory Tree mutations

- `aci.memory.added` — a new fact, episode, or epoch was written. Payload: path in tree, source, expiry if set.
- `aci.memory.corrected` — a fact was updated. Payload: path, previous value summary, new value summary, reason.
- `aci.memory.forgotten` — a fact was removed. Payload: path, reason.
- Producer: runtime. Consumer: Memory Transparency.

### 6.4 `aci.proof.*` — decision ledger appends

- `aci.proof.decision` — every kernel decision, build-governor classification, gate evaluation. Payload: id, decision, evidence references.
- Producer: kernel, governor, runtime. Consumer: Proof History.

### 6.5 `aci.worker.*` — Hermes Native Engineer turns

- `aci.worker.started`, `aci.worker.progress`, `aci.worker.completed`, `aci.worker.paused`, `aci.worker.resumed`.
- Producer: Hermes Native Engineer. Consumer: Worker Lane, Tasks.

### 6.6 `aci.estop.*` — emergency stop

- `aci.estop.fired` — owner pressed the emergency stop button.
- `aci.estop.status` — current state.
- `aci.estop.cleared` — owner cleared the stop, with biometric confirmation.
- Producer: kernel. Consumer: every screen that runs workers or shows runtime state.

Payload shape sketches above reference the Kotlin model files in `apps/android/app/src/main/java/com/aci/hermes/model/` (current draft at the W10 job-state-models PR) by path only. The spec stays implementation-agnostic; payload field lists are owned by the gateway event-bus wave (see the launch wave map).

## 7. Build Waves

The canonical wave sequence lives in `JARVIS_PRIME_LAUNCH_WAVE_MAP.md`. Summary:

- **W00** — Master Build Spec (this wave). Docs-only.
- **W01 through W03** — Backend contract waves: turn shape, surface adapters, specialist matrix, decision ledger, verification packet, review packet schema. Parallel-safe.
- **W04** — Memory Tree backend.
- **W05** — Context Engine backend.
- **W06** — Permission Kernel backend.
- **W07** — Gateway event-bus extensions for `aci.*`. Integration-only.
- **W08** — `apps/android/` skeleton (gradle wrapper, manifest, app build files). Integration-only and owner-gate.
- **W09** — Android networking and auth.
- **W10** — Android job-state models (already drafted; depends on W08).
- **W11 through W21** — One wave per Android screen, in screen-map order.
- **W22** — Permission education flow.
- **W23** — Push / notification channel. Owner-gate.
- **W24** — End-to-end integration sweep on emulator. Integration-only.
- **W25** — Termux / doctor reconciliation.
- **W26** — Dependency and supply-chain hardening.
- **W27** — CI hardening.
- **W28** — Release engineering. Owner-gate.
- **W29** — Documentation polish.
- **W30** — Launch readiness review. Integration-only and owner-gate. No store submission inside W30.

Final merge target is `main`. Each wave merges as a draft PR after owner approval. There is no release branch. Integration-only waves are W07, W08, W24, and W30. Owner-gate waves are W08, W23, W28, and W30.

## 8. Launch Definition

Jarvis Prime is launch-ready when every item below is true.

1. Android debug build assembles green on `apps/android/`. `./gradlew assembleDebug` exits 0 and produces a debug APK.
2. There is exactly one Android module path in the tree: `apps/android/`. The repository must not contain any of: `mobile/jarvis-prime-android/`, `android/` at repo root, `JarvisPrimeAndroid/`, or any other parallel Android module. See `JARVIS_PRIME_NAMING_AND_SCOPE_RULES.md` for the full forbidden-path list.
3. Every user-facing string in the Android app, push notifications, voice responses, and app-store metadata reads "Jarvis Prime", not "Hermes" or "JARVIS". The Android string-resource file is grepped for "Hermes" and the grep returns zero hits in user-facing keys.
4. No `*.kt`, `*.kts`, `*.gradle`, `AndroidManifest.xml`, or string-resource file contains a secret, token, API key, signing key, or gateway secret. Verified by a CI grep over the Android tree.
5. The Approvals, Proof History, and Emergency Stop screens are each reachable from Home in at most one tap.
6. Every wave PR that landed under the launch wave map was draft-merged with green CI, no force push, and an explicit owner approval recorded as an `aci.approval.responded` event.
7. The Permission Kernel passes a test suite that asserts every owner-only wall blocks a synthetic agent attempt and emits an `aci.proof.decision` for the blocked attempt.
8. The Notifications Command Center has been verified by manual test: a fresh install does not surface the system notification dialog until the owner enables notifications from inside the app.
9. The microphone permission is requested only after the owner taps the voice capture button. Verified by manual test on a fresh install.
10. No SMS, no Call Log, no accessibility-service, no foreground-always-listening permission appears in `AndroidManifest.xml`. Verified by grep.
11. The launch wave map reconciliation table (Part A of `JARVIS_PRIME_LAUNCH_WAVE_MAP.md`) shows every in-flight PR as merged or explicitly retired.

The launch readiness review is W30. The owner approves go or no-go. No store submission happens inside W30; store submission is a separate owner-only action after W30 passes.

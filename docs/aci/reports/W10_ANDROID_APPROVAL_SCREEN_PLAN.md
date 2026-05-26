# W10 — Android Owner-Approval Screen: Implementation Plan

**Wave:** 10
**Date:** 2026-05-26
**Status:** Plan only — no code in this PR.
**Branch:** `aci/wave-10-android-approval-screen-plan`
**Mode:** Draft PR, no merge to main.

---

## 1. Universal Header & Non-Overlap Contract (restated)

- Create and work only on branch `aci/wave-10-android-approval-screen-plan`.
- **Allowed files (this wave only):**
  - `docs/aci/reports/W10_ANDROID_APPROVAL_SCREEN_PLAN.md`
- **Forbidden files (this wave):**
  - `apps/android/**`
  - All source code (Python, Kotlin, JS, anything compileable)
  - `README.md`, `pyproject.toml`, `uv.lock`
  - Package files, Gradle files, GitHub workflows, shared config
  - Any other wave's files
- If a required change is discovered outside allowed files, **stop** and
  record it in this report instead of editing.
- **No merge to main.** Open a draft PR only.
- No publish, deploy, DNS change, secret rotation, money spend, or app
  store submission as part of this wave.
- **No secrets** in code, logs, docs, tests, fixtures, or screenshots.
- This wave produces only a written plan; no tests are required for the
  plan itself. Tests required by the *future coding wave* are enumerated
  in §11 below.

---

## 2. Mission & Out-of-Scope

### Mission
Design — without coding — the Android screen that lets the human owner
review, approve, deny, or defer high-risk actions originating from
Hermes / JARVIS Prime. The backend already emits `approval_requested`
and `approval_resolved` events through the MCP event bridge
(`mcp_serve.py:199`, `:314`, `:681`), and the owner-approval gate is
already required policy in `docs/jarvis-verification-gates.md:129`. What
is missing is the **mobile surface** that presents and resolves those
approvals — built with safeguards strong enough to prevent accidental
production approval.

### Out-of-scope for W10
- Writing any Kotlin, Compose, Gradle, or AndroidManifest content.
- Adding Android modules, dependencies, build flavors, or signing config.
- Finalising the backend `/v1/approvals` HTTP contract (assumed here;
  must be ratified by a backend wave).
- Implementing biometric, Keystore, or Play Integrity code.
- Sending, queuing, or persisting any approval decision.
- A multi-approval inbox / list view (deferred to a later wave).
- iOS or web parity (separate waves).

---

## 3. Screen Route

**Primary route:** `aci/approval/{approvalId}` registered in the Compose
NavHost.

**Deep link:** `aci://approval/{approvalId}` (e.g. opened by a push
notification or system intent). Deep-link handling **must** verify that
the `approvalId` matches a server-known pending approval before showing
any sensitive content; if not, the screen presents an "Approval not
found or already resolved" state and offers a Close action — never a
retry that exposes payload to a stranger.

**Single-approval focus:** the screen surfaces exactly one approval at a
time. No inbox, no batched approve. A list / inbox surface is explicitly
deferred to a future wave.

**Back behaviour:** system back / up navigation from the approval screen
is treated as "leave undecided" — it does **not** send `defer` or any
decision to the backend. Audit log records a `viewed_only` event with
duration.

---

## 4. ViewModel State

`ApprovalViewModel` exposes a single `StateFlow<ApprovalUiState>` and a
small command surface (`onPhraseChanged`, `onApproveClicked`,
`onDenyClicked`, `onDeferClicked`, `onBiometricResult`).

```
sealed interface ApprovalUiState {
  data object Loading : ApprovalUiState
  data class Ready(
    val details: ApprovalDetails,
    val confirmation: ConfirmationInput,
    val submissionGuard: SubmissionGuard,
  ) : ApprovalUiState
  data object Submitting : ApprovalUiState
  data class Resolved(val decision: Decision) : ApprovalUiState
  data class Error(val reason: ErrorReason, val recoverable: Boolean)
    : ApprovalUiState
}
```

`ApprovalDetails` carries the server-provided fields (see §5).
`ConfirmationInput` debounces the user's typed phrase and runs the
case-sensitive, trimmed comparator described in §6.
`SubmissionGuard` is a small AND-gate that returns `true` only when
**all** of the following hold:

1. `risk_class` has been displayed for ≥ 5 seconds (when
   `risk_class == "production"`).
2. The typed phrase matches the server-issued phrase exactly.
3. A biometric / device-credential prompt has succeeded within the last
   30 seconds.
4. Device attestation token is fresh (≤ 60 seconds old).
5. Network is currently reachable (no offline approves — see §10).
6. `ApprovalUiState` is `Ready` (i.e. not already submitting / resolved).

The approve button is rendered as **disabled** whenever any guard
condition is false. The reason for the disable is exposed in an
inline-help string for accessibility and debugging.

---

## 5. API Endpoint Assumptions

**Status: ASSUMED — to be ratified by a backend wave before W10
implementation.** All four endpoints below are predictions grounded in
the *observed* MCP event bridge in `mcp_serve.py`. The implementation
wave **must not** invent the contract unilaterally.

### 5.1 Fetch approval
```
GET /v1/approvals/{approval_id}
Authorization: Bearer <owner-session-token>
```
Response (assumed; mirrors `_pending_approvals` value in
`mcp_serve.py:300-302`):
```json
{
  "approval_id": "apr_01HXY...",
  "session_key": "sess_abc...",
  "created_at": "2026-05-26T18:31:02Z",
  "expires_at": "2026-05-26T18:46:02Z",
  "risk_class": "production" | "staging" | "internal" | "low",
  "requested_by": "agent:jarvis-prime",
  "summary": "Merge PR #142 to main",
  "payload": { ... action-specific structured data ... },
  "confirmation_phrase": "APPROVE WAVE-10 #a1b2",
  "phrase_ttl_seconds": 300
}
```
Notes:
- `confirmation_phrase` is **server-issued and per-approval-bound**.
- `phrase_ttl_seconds` lets the client surface "phrase expired" before
  the user pastes-and-submits something stale.

### 5.2 Resolve approval
```
POST /v1/approvals/{approval_id}/respond
Authorization: Bearer <owner-session-token>
Content-Type: application/json
X-Device-Attestation: <attestation-token>
```
Body:
```json
{
  "decision": "approve" | "deny" | "defer",
  "confirmation_phrase": "APPROVE WAVE-10 #a1b2",   // approve only
  "reason": "...",                                   // deny only, ≥8 chars
  "defer_until": "2026-05-26T19:00:00Z",            // defer only
  "client_signature": "<keystore-signed digest>"
}
```
Maps to bridge method `respond_to_approval(approval_id, decision)` at
`mcp_serve.py:304-319`. The implementation wave **must** confirm whether
the wider envelope (phrase, reason, defer_until, signature) is
server-validated end-to-end or only client-side; W10 plan **requires**
end-to-end server validation.

### 5.3 Realtime updates
Reuse the existing MCP `events_wait` long-poll
(`mcp_serve.py:699-720`) **or** a thin HTTP/SSE wrapper over it:
- Subscribe with `after_cursor=<last>` filtered to
  `approval_resolved` events.
- If the screen is showing `approval_id == X` and an
  `approval_resolved` event arrives for the same id, auto-dismiss with
  "This approval was resolved elsewhere ({decision})."

### 5.4 Push notification (separate channel, not in W10 scope)
Plan only — the push payload that opens the screen via deep link must
**never** include the action payload, summary, or `confirmation_phrase`.
Push body is limited to `approval_id` and a generic title.

---

## 6. Exact-Phrase Confirmation UX

Borrowed from `docs/jarvis-verification-gates.md:128-130` (owner approval
gate). The owner must type a server-issued phrase to enable Approve.

**Phrase format (server-generated):** `APPROVE <SHORT-ID> #<4-char-nonce>`

Example: `APPROVE WAVE-10 #a1b2`

Properties:
- Begins with literal uppercase word `APPROVE`.
- Includes the action's short identifier (`WAVE-10` here is illustrative;
  real value is action-derived).
- Ends with a 4-character nonce **bound to `approval_id`**. Server
  rejects any phrase whose nonce does not match the stored nonce for
  that approval.
- Server treats the nonce as **single-use**. Replay = reject.

**Input field behaviour:**
- `KeyboardOptions(autoCorrect = false, keyboardCapitalization = None,
  keyboardType = Ascii)`.
- `visualTransformation = None` (visible — the secret is bound to the
  approval, not to the user).
- **Paste blocked** (`onPaste` intercepted; clipboard listener disabled
  on focus).
- **Autofill disabled** (`Modifier.semantics { contentType = None }`).
- Comparison is **case-sensitive** and **trimmed** of leading/trailing
  whitespace only — internal whitespace must match.
- Comparison runs debounced at 150 ms after the last keystroke.
- Unicode normalization: input is `NFKC`-normalized before comparison to
  defeat homoglyph attacks (e.g. Cyrillic `А` vs Latin `A`); a homoglyph
  hit logs a tamper event (see §8).
- The Approve button only becomes enabled when **the phrase matches AND
  every other guard in §4 passes**.

**Biometric step:** clicking Approve triggers a `BiometricPrompt` with
`BIOMETRIC_STRONG | DEVICE_CREDENTIAL`. The submission is only made
after a successful biometric callback within the same 30-second window.

---

## 7. Deny / Defer Actions

### 7.1 Deny
- **Affordance:** secondary button labelled "Deny", clearly de-emphasised
  vs Approve to avoid mis-tap, but still single-tap reachable.
- **Phrase required?** No exact phrase. Denying is the safe default.
- **Reason required?** Yes. Free-text reason ≥ 8 characters,
  ≤ 280 characters. Auto-correct allowed on the reason field (it is
  audit text, not a secret).
- **Confirmation modal?** Yes — a single "Confirm deny" tap to prevent
  fat-finger mid-typing.
- **Payload emitted:** `{ "decision": "deny", "reason": "..." }`.
- **Audit event:** `aci.approval.decision` with `decision = "deny"`.

### 7.2 Defer
- **Affordance:** tertiary action ("Defer") that opens a snooze chooser:
  - 15 minutes
  - 1 hour
  - Until tomorrow 9:00 am (local time)
- No phrase. No reason.
- **Payload emitted:** `{ "decision": "defer",
  "defer_until": "<ISO-8601>" }`.
- Server-side, defer leaves the approval `pending` and pushes the
  effective re-notification window. (Whether `defer` is a true
  server-side state or a client-only reminder is an **open question** —
  see §15.)
- **Audit event:** `aci.approval.decision` with `decision = "defer"`
  and the chosen `defer_until`.

---

## 8. Audit Log Event

Every terminal user interaction produces a structured audit envelope.
The Android client emits both a local persistent log (encrypted Room
DB) and a server audit POST.

**Event name:** `aci.approval.decision`

**Schema (assumed):**
```json
{
  "event": "aci.approval.decision",
  "approval_id": "apr_...",
  "decision": "approve" | "deny" | "defer" | "viewed_only",
  "reason": "...",                  // deny only
  "defer_until": "...",             // defer only
  "phrase_match": true,             // approve only
  "biometric_used": true,           // approve only
  "biometric_strength": "STRONG" | "WEAK" | "DEVICE_CREDENTIAL",
  "device_id": "<opaque, non-PII id>",
  "app_version": "1.0.0+42",
  "build_flavor": "release" | "internal" | "debug",
  "network_class": "wifi" | "cellular" | "offline",
  "latency_ms": 1234,
  "client_ts": "<ISO-8601>",
  "server_ts": "<ISO-8601 set on receipt>",
  "tamper_flags": ["homoglyph_detected", "clock_skew_high", ...]
}
```

**Storage:**
- **Local:** encrypted Room DB, capped at 500 entries with FIFO
  eviction; never exported, never sent to crash reporters or analytics.
- **Server:** `POST /v1/audit/events` (assumed; may already exist —
  the coding wave must check before defining a new endpoint).

**Offline forensics:** local audit copy persists even when the network
POST fails, so a stolen device can be reviewed after recovery.

---

## 9. Security Warnings (MUST / SHOULD / MUST NOT)

### MUST
- Require a recent (≤ 30 seconds) biometric or device-credential
  prompt success before Approve submission.
- Sign the response body with an Android Keystore key (StrongBox-backed
  where available) and include `client_signature` for server-side
  verification.
- Apply `FLAG_SECURE` to the approval screen's window to block
  screenshots and prevent rendering in the recent-apps thumbnail.
- Verify TLS certificate pinning against the ACI control plane (pin
  set carried in resource, not hard-coded in shareable strings).
- Validate the server-issued phrase nonce is bound to the current
  `approval_id` — if the server response includes a phrase whose nonce
  does not match expected entropy properties, refuse to render the
  Approve UI at all.
- Re-fetch the approval and clear the typed phrase on app
  foreground / background transitions.
- Treat the approval payload as PII-equivalent: never log to logcat in
  release builds, never send to crash reporters or analytics.

### SHOULD
- Display a tamper banner if `created_at` skew vs the device clock
  exceeds 5 minutes (covers a rooted-device clock-rollback class).
- Use `StrongBox` for the signing key when the device supports it.
- Attest device integrity with Play Integrity (`MEETS_STRONG_INTEGRITY`)
  before allowing Approve in `production` risk class.
- Throttle re-attempts: after three submit failures in 60 seconds, lock
  the screen for 30 seconds with a "rate limited" banner.

### MUST NOT
- Auto-fill, paste, suggest, or remember the confirmation phrase.
- Cache the approval payload or phrase in:
  - System share-sheet history
  - Accessibility node tree
  - Assist / contextual content surfaces
  - Backup / auto-backup (`android:allowBackup="false"` for the module)
- Send the phrase, payload, or audit body to any third-party SDK
  (analytics, crash, A/B, attribution).
- Persist the phrase to disk under any condition.
- Allow Approve to enter `Submitting` state when network is offline.
- Allow the screen to be embedded inside another app via `taskAffinity`
  hijack — set `android:exported="false"` and `singleInstance` launch
  mode at scaffold time.

---

## 10. Offline Behaviour

| State | UX | Behaviour |
| --- | --- | --- |
| Cold open offline | Loading → Error (recoverable) with "Network required" | No payload shown; Retry button polls reachability |
| Online → fetched → goes offline | Payload remains visible, Approve disabled, banner "Network required" | Phrase input stays editable so user is ready when reconnect happens |
| Submit attempted while offline | Submit blocked by guard | Banner reminds user that decisions cannot be queued |
| Network loss mid-submit | Screen shows "Outcome unknown" | Forces a re-fetch on reconnect; outcome is whatever the server records — client never re-submits without an explicit user action |
| Approval expired (TTL passed) | Banner: "This approval expired. Re-request from the originating agent." | Approve / Deny / Defer all disabled; Close visible |

**Deliberate anti-pattern guard:** decisions are **never** queued for
later send. A stolen, locked phone that comes back online must not be
able to drain a queue of pending approvals.

---

## 11. Tests Needed (for the future coding wave)

The implementation wave **must** add tests in the categories below.
Tests are part of the acceptance criteria; if any category is skipped,
the rationale must be written in the implementation wave's report.

### 11.1 ViewModel unit tests
*Framework:* Turbine + kotlinx-coroutines-test + Mockk
- State transition matrix: `Loading → Ready → Submitting → Resolved`
  and every error branch.
- Phrase comparator: case mismatch, leading/trailing whitespace,
  internal whitespace, NFKC homoglyph (Cyrillic А vs Latin A),
  trailing newline, mixed-script combining marks.
- SubmissionGuard: each AND-gate exercised individually and in
  combination.
- Defer scheduling: 15 min / 1 hr / tomorrow 9 am math across DST and
  timezone boundaries.

### 11.2 Compose UI tests
*Framework:* `androidx.compose.ui.test`
- Approve button enabled/disabled across the full guard truth table.
- `FLAG_SECURE` assertion via window flag inspection.
- BiometricPrompt invocation on Approve click.
- Screenshot blocking — automated assertion that `FLAG_SECURE` is set
  while the screen is in resumed state.
- Deny modal confirmation flow.
- Defer chooser interaction.
- Deep-link entry with an unknown / resolved `approval_id`.

### 11.3 Repository / integration tests
*Framework:* MockWebServer
- 200 OK happy path, 400, 401, 403, 404, 409 (already resolved), 410
  (expired), 429 (rate-limited), 500, 503.
- TLS pin mismatch is rejected at the OkHttp / Ktor layer.
- Idempotency: submitting the same decision twice does not double-act.
- Long-poll auto-dismiss on `approval_resolved` event.

### 11.4 Security tests
- Paste-clipboard rejection on the phrase field.
- Accessibility-tree leak check (the phrase value must not appear in
  the semantics tree).
- Autofill rejection check.
- Deep-link tampering: a deep link with a tampered `approval_id` does
  not show payload before server confirmation.
- `allowBackup` is false in the feature module manifest.

### 11.5 Acceptance / end-to-end
- Golden-path approve (production risk class).
- Deny-with-reason (reason length validation).
- Defer-and-wake (server confirms re-pending after `defer_until`).
- Offline-readonly view.
- Network-loss-mid-submit "Outcome unknown" recovery.
- Expired-phrase refresh flow.

---

## 12. Files a Future Coding Wave May Edit

**Status: ASSUMED canonical Android Gradle paths.** `apps/android/`
does not yet exist in this repo (verified by `ls`). All entries below
are therefore tagged **NEW**. The implementation wave **must** confirm
the actual module layout before creating files; if the project decides
on a different module name (e.g. `feature-owner-approval` vs
`feature-approval`), the wave updates this list before coding.

| Path | Status | Purpose |
| --- | --- | --- |
| `apps/android/feature-approval/src/main/kotlin/com/aci/jarvis/approval/ApprovalScreen.kt` | NEW | Compose UI |
| `apps/android/feature-approval/src/main/kotlin/com/aci/jarvis/approval/ApprovalViewModel.kt` | NEW | State + commands |
| `apps/android/feature-approval/src/main/kotlin/com/aci/jarvis/approval/ApprovalUiState.kt` | NEW | Sealed state hierarchy |
| `apps/android/feature-approval/src/main/kotlin/com/aci/jarvis/approval/data/ApprovalRepository.kt` | NEW | API + audit orchestration |
| `apps/android/feature-approval/src/main/kotlin/com/aci/jarvis/approval/data/ApprovalApi.kt` | NEW | Retrofit / Ktor surface |
| `apps/android/feature-approval/src/main/kotlin/com/aci/jarvis/approval/audit/ApprovalAuditLogger.kt` | NEW | Local Room + server POST |
| `apps/android/feature-approval/src/main/kotlin/com/aci/jarvis/approval/security/PhraseValidator.kt` | NEW | NFKC + comparator |
| `apps/android/feature-approval/src/main/kotlin/com/aci/jarvis/approval/security/DeviceAttestation.kt` | NEW | Play Integrity wrapper |
| `apps/android/feature-approval/src/main/kotlin/com/aci/jarvis/approval/security/BiometricGate.kt` | NEW | BiometricPrompt wrapper |
| `apps/android/feature-approval/src/main/AndroidManifest.xml` | NEW | `allowBackup=false`, deep-link, exported=false |
| `apps/android/app/src/main/kotlin/com/aci/jarvis/navigation/ApprovalNavGraph.kt` | NEW | Registers `aci/approval/{approvalId}` route |
| `apps/android/feature-approval/src/test/...` (mirror tree) | NEW | Unit tests |
| `apps/android/feature-approval/src/androidTest/...` (mirror tree) | NEW | Compose / instrumentation tests |

The implementation wave **must not** edit anything outside this list
without writing the deviation into its own wave report.

---

## 13. Anti-Production-Approval Safeguards

These exist specifically to satisfy the W10 acceptance criterion
"Plan prevents accidental production approval."

1. **Risk class banner:** the server's `risk_class` is displayed at the
   top of the screen before the phrase input is editable. For
   `risk_class == "production"`, the input is **disabled for 5 seconds**
   while a red banner reads
   "PRODUCTION ACTION — read carefully." Countdown is visible.
2. **Nonce-bound phrase:** the server-issued phrase ends in a nonce
   bound to `approval_id`. Server rejects reuse. Server rejects any
   nonce that does not match the stored value for that approval.
3. **Biometric recency:** the server rejects an `approve` decision if
   `client_signature` was produced more than 30 seconds after the
   biometric callback timestamp. The client encodes the biometric
   timestamp inside the signed payload.
4. **Device attestation:** server rejects `approve` if Play Integrity
   token indicates the device fails `MEETS_STRONG_INTEGRITY` for any
   approval whose `risk_class == "production"`.
5. **Single-use approval_id:** server treats `approval_id` as single-use.
   Resubmits return `409 Conflict` with the stored decision.
6. **Build-flavor guard:**
   - `debug` and `internal` flavors render a watermark banner over the
     screen, set the API base URL to staging, and refuse to attach a
     real Play Integrity token (a stub token is used).
   - The production API base URL is **only compiled into the `release`
     flavor** via build-time constant.
7. **No paste / no autofill / no clipboard:** see §6 and §9. Removes
   the "an attacker socially-engineered the owner to paste a phrase
   they received over chat" class.
8. **No offline approvals:** see §10. Removes the "drain pending queue
   after recovery" class.
9. **TTL display:** the screen shows `phrase_ttl_seconds` countdown.
   When it reaches zero, the screen forces a re-fetch.
10. **No screenshots / no recents thumbnail:** `FLAG_SECURE` blocks
    casual screen-sharing of the phrase.

---

## 14. AOS Council Routing for the Implementation Wave

Per `CLAUDE.md:23-46`, the AOS Council bench reviews high-impact
implementation. For the W10 *coding* wave (not this planning wave), the
required reviewers are:

- `principal-systems-architect` — module boundaries, navigation graph,
  state machine soundness.
- `assurance-risk-director` — security warnings (§9), anti-production
  safeguards (§13), audit log shape (§8).
- `product-experience-architect` — exact-phrase UX (§6), deny/defer
  affordances (§7), accessibility, mis-tap risk.
- `contrarian-reviewer` — adversarial review: rooted device, stolen
  device, social engineering, push-notification tampering.
- `codex-dispatch-governor` — convert this plan into bounded
  implementation tasks with acceptance criteria and validation commands
  before any Kotlin is written.

The planning wave (W10, this PR) is reviewed by `contrarian-reviewer`
and `assurance-risk-director` only — enough to validate that the plan
itself does not pre-bake an unsafe design.

---

## 15. Open Questions for the Backend Wave (non-blocking for this plan)

1. Final `GET /v1/approvals/{id}` response schema (assumed shape in §5
   is the starting point).
2. Whether `defer` is a true server-side state (re-pending with new
   notification window) or a client-only reminder. Plan currently
   assumes server-side state.
3. Where the confirmation phrase is generated — server-side store or
   HMAC-derived from `approval_id` + secret. Plan currently assumes
   server-side store with explicit nonce.
4. Device-attestation mechanism: Play Integrity vs. legacy SafetyNet
   vs. a custom attestation. Plan currently assumes Play Integrity.
5. Whether an existing `POST /v1/audit/events` endpoint already exists
   or must be added. Coding wave **must** check before defining new
   routes.
6. Push-notification payload contract — the W10 plan requires that
   pushes carry only `approval_id` and a generic title, but the
   notification channel itself is a separate wave.

---

## 16. Wave Report Footer

### Changed files
- `docs/aci/reports/W10_ANDROID_APPROVAL_SCREEN_PLAN.md` (NEW)
- `docs/aci/reports/` directory created (NEW; previously absent)

### Tests run
- None applicable — this wave produced only a planning document. No
  source, no fixtures, no schemas changed.
- Acceptance verification: `git diff --stat` shows exactly one new file
  under `docs/aci/reports/`; no other paths touched.

### Remaining risks
- Backend `/v1/approvals` contract is assumed; if the eventual contract
  diverges materially, §5 and §13 must be revisited before the coding
  wave begins.
- `apps/android/` module layout is assumed canonical; the actual
  scaffold may rename the feature module, in which case §12 paths must
  be rewritten before any file creation.
- Push-notification channel and audit-events endpoint are referenced
  but not designed here; both are explicit open questions (§15).
- The plan presumes a Play Integrity-capable device for `production`
  risk-class approvals; behaviour on a non-attestable device is to
  reject Approve outright — this may need a policy carve-out for
  emergency use which has **not** been designed in W10.

### Rollback plan
1. `git checkout main` (or the branch this PR targets).
2. `git branch -D aci/wave-10-android-approval-screen-plan` locally.
3. Close the draft PR (do not merge).
4. Optionally `rmdir docs/aci/reports docs/aci` if no other wave has
   landed there in the meantime.
No code, config, dependency, secret, infrastructure, or environment is
touched by this wave, so rollback is metadata-only.

### PR summary (draft only)
**Title:** `docs(aci): W10 plan — Android owner-approval screen (no code)`
**Body:**
> Wave 10 of the ACI initiative. Plan-only PR — no source code, no
> Gradle, no Android modules. Documents the screen route, ViewModel
> state, assumed API contract, exact-phrase confirmation UX, deny /
> defer / audit / offline behaviours, and anti-production-approval
> safeguards for the future Android owner-approval screen.
>
> Companion to the existing backend approval-event infrastructure
> (`mcp_serve.py:199, 304, 681`) and the owner-approval gate policy
> (`docs/jarvis-verification-gates.md:129`).
>
> Draft PR. Do not merge. Implementation wave (Kotlin / Compose) is a
> separate, future wave that will consume this plan.

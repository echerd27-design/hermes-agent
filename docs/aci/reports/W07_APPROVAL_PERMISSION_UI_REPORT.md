# W07 — Jarvis Prime Approval Cards & Permission Kernel UI

| | |
|---|---|
| Wave | ACI W07 — Jarvis Prime approval-cards & permission-kernel UI |
| Branch | `claude/upbeat-hypatia-EiqPO` (harness-assigned; supersedes sprint's `aci/jarvis-prime-07-approval-permission-ui`) |
| Mission | Design — without coding — the Compose component contract for Jarvis Prime's three-tier approval cards and permission-kernel surface, so the future implementation wave can land them against a buildable Android module. |
| Scope | Documentation only. **No Kotlin / Compose / Gradle / Manifest edits.** |
| Allowed files | `docs/aci/reports/W07_APPROVAL_PERMISSION_UI_REPORT.md` |
| Forbidden | `apps/android/app/src/main/java/com/aci/hermes/MainActivity.kt`, `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/{home,tasks,chat,memory,proof}/**`, `apps/android/AndroidManifest.xml`, `hermes_cli/**`, `skills/**`, `README.md`, `pyproject.toml`, `uv.lock`, `.github/**`, all Gradle files |
| Repo | `echerd27-design/hermes-agent` (harness-scoped). Sprint header named `A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent` — not reachable this session. |
| Date | 2026-05-26 |

---

## 1. Executive verdict

W07 was scoped against an assumed state — *an existing Android Gradle
module at `apps/android/` with W01–W06 of the Jarvis Prime UI wave-set
already merged*. That assumption does not hold in this repository.

Pre-flight verification (§3) confirms:

- `apps/android/` does not exist on `origin/main` or on the working
  branch. No `build.gradle`, no `settings.gradle`, no
  `AndroidManifest.xml`, no `MainActivity.kt`, no Compose dependency
  declaration, no `com/aci/hermes/ui/jarvis/**` package anywhere in
  the tree.
- No `aci/jarvis-prime-0*` branch exists in the remote. W01–W06
  predecessors have not been opened on this fork.
- The only branch in the remote that carries any `apps/android/**`
  content is `aci/wave-10-android-job-models`, which contains 6
  pure-Kotlin data classes + 5 JUnit tests — and **no** Gradle
  scaffold, manifest, MainActivity, or Compose setup.
- The sibling `aci/wave-10-android-approval-screen-plan` branch and
  the `aci/wave-10-android-launch-audit` branch both shipped
  **report-only PRs** and independently documented the same gap.
- The scaffolding required to make any Kotlin compile (Gradle files,
  `AndroidManifest.xml`, `MainActivity.kt`) is on this sprint's
  **FORBIDDEN FILES** list.

Per the sprint's NON-OVERLAP CONTRACT — *"If a needed change is
outside ALLOWED FILES, do not edit it; write it into the report"* —
W07 ships as a single-file documentation deliverable. The full
component contract is specified here so the future implementation
wave (W07-bis, after a W00 scaffold wave) can land the components
against a real, buildable module without re-deriving the design.

No destructive UI is wired. No gateway calls are made. No Kotlin is
authored. No Gradle invocation is attempted (no project to invoke).

---

## 2. Mission & out-of-scope

### Mission

Specify the Compose UI surface for Jarvis Prime's three-tier approval
workflow:

- **Normal** — display-only, no approval required.
- **Serious** — approval card with action summary; single confirmation.
- **Critical** — impact report, rollback summary, exact-phrase gate
  (`Yes, with authorization.`), two confirmations, visible
  emergency-stop placeholder.

Seven components are in scope: `ApprovalCard`,
`CriticalActionImpactPanel`, `RollbackSummaryPanel`,
`ExactPhraseConfirmationField`, `EmptyApprovalState`,
`ApprovalStatusBadge`, plus the `Approve / Deny / Defer` callback
contract.

### Out-of-scope for W07

- Writing any Kotlin, Compose, Gradle, or `AndroidManifest.xml` —
  the module does not exist and the scaffolding files are FORBIDDEN.
- Navigation integration (`MainActivity.kt`, NavHost wiring) — also
  FORBIDDEN.
- Wiring callbacks to a real backend gateway. W07 components emit
  callbacks; routing the callbacks to network code is a later wave.
- Push-notification surfacing of approvals — separate channel work.
- Permissions plumbing for `RECORD_AUDIO`, `POST_NOTIFICATIONS`,
  Location, etc. The "permission kernel" half of this sprint covers
  the **UI primitives** that gate destructive actions; OS-permission
  request flow lands in a permissions wave with explicit per-permission
  justification per the Global Product Rules ("No automatic
  notification permission prompt on first launch", "Microphone
  permission only after user taps voice").
- Biometric / Keystore / Play Integrity attestation — that surface
  belongs in the dedicated approval-screen scope (see W10's
  `docs/aci/reports/W10_ANDROID_APPROVAL_SCREEN_PLAN.md` on branch
  `aci/wave-10-android-approval-screen-plan`).
- iOS or web parity.

### Relationship to W10's approval-screen plan

W10's `W10_ANDROID_APPROVAL_SCREEN_PLAN.md` (on
`aci/wave-10-android-approval-screen-plan`) designs the **full-screen
single-approval flow** with server-issued nonce-bound phrases,
biometric gates, and device attestation. W07 designs the **card-level
components** that the future inbox/timeline surfaces would compose to
display many approvals at a glance. The two surfaces share an
ApprovalDecision callback shape (§7) so a future implementation wave
can use the same primitives in both contexts.

W07 does **not** re-derive W10's server contract; it deliberately
keeps the card components ignorant of the network. Components accept
inert immutable state and emit semantic callbacks. That is the entire
contract.

---

## 3. Pre-flight evidence

All commands run from working tree at `/home/user/hermes-agent` on
branch `claude/upbeat-hypatia-EiqPO`.

| Step | Command | Result |
|---|---|---|
| 1 | `git fetch origin main` | OK |
| 2 | `git status --short` | clean |
| 3 | `git branch --show-current` | `claude/upbeat-hypatia-EiqPO` |
| 4 | `git log --oneline origin/main..HEAD` | empty (zero commits ahead at start) |
| 5 | `ls apps/` | ENOENT |
| 6 | `git ls-tree -r origin/main --name-only \| grep '^apps/'` | empty |
| 7 | `git ls-tree -r origin/main --name-only \| grep -iE 'build\\.gradle\|settings\\.gradle\|AndroidManifest\\.xml\|MainActivity\\.kt'` | empty |
| 8 | `git ls-tree -r origin/main --name-only \| grep '^docs/aci/'` | empty (this report creates the directory) |
| 9 | `git branch -r \| grep 'jarvis-prime-0'` | empty |
| 10 | `git ls-tree -r origin/aci/wave-10-android-job-models -- apps/android` | 11 files: 6 Kotlin model classes + 5 unit tests, no Gradle scaffold |
| 11 | `git show origin/aci/wave-10-android-approval-screen-plan -- docs/aci/reports/` | `W10_ANDROID_APPROVAL_SCREEN_PLAN.md` only (report-only PR; precedent) |
| 12 | `git show origin/aci/wave-10-android-launch-audit -- docs/aci/reports/` | `W10_ANDROID_LAUNCH_AUDIT.md` only (report-only PR; precedent) |

**Branch inventory of `origin` (echerd27-design/hermes-agent):**

```
aci/wave-05-review-packet-schema
aci/wave-05-verification-packet
aci/wave-08-decision-ledger
aci/wave-10-android-approval-screen-plan
aci/wave-10-android-job-models
aci/wave-10-android-launch-audit
aci/wave-11-termux-doctor-audit
aci/wave-12-dependency-review
claude/*    (harness branches)
feature/aos-operating-registry-cleanup
feature/jarvis-prime-operating-layer
fix/*
main
repo-modernization-*
```

No `aci/jarvis-prime-0*` branches. W01–W06 of the Jarvis Prime UI
wave-set are absent from the accessible remote.

**Contract clauses being honored:**

- *"If a needed change is outside ALLOWED FILES, do not edit it;
  write it into the report."* → no Kotlin authored.
- *"If another open branch/PR appears to touch the same allowed
  files, stop and write a collision report."* → no collision (no
  other branch touches `docs/aci/reports/W07_APPROVAL_PERMISSION_UI_REPORT.md`).
- *"Every change needs validation or a clear skipped-test reason."*
  → §13 documents the skipped-test reason.
- *"Open a draft PR only."* → see §15.

---

## 4. Approval tier model

| Tier | Trigger | UI affordance | User action required | Default state |
|---|---|---|---|---|
| **Normal** | Backend tagged action as informational / read-only / already idempotent | Card body only, status badge `Informational`, no action buttons | None | Display |
| **Serious** | Backend tagged action as state-mutating but reversible (e.g. file edits, branch creates, non-destructive commits) | Card body + summary line + `Approve` / `Deny` / `Defer` buttons | One tap on Approve | Buttons enabled by default; Approve emits `ApprovalDecision.Approve` |
| **Critical** | Backend tagged action as destructive, externally-visible, irreversible, security-relevant, or money-spending | Card body + `CriticalActionImpactPanel` + `RollbackSummaryPanel` + `ExactPhraseConfirmationField` + visible emergency-stop placeholder + `Approve` / `Deny` / `Defer` | Type exact phrase, two-step Approve confirm; Deny/Defer always one tap | Approve disabled until phrase matches; Deny/Defer always enabled |

**Tier is a server-side classification.** The UI does not infer
criticality from action text. The data model carries
`tier: ApprovalTier` from the server and the card composes the
correct sub-tree based on that field. UI-side tier inference is
explicitly an anti-pattern: it lets a renamed action sneak past the
Critical gate.

**Exact phrase for Critical tier:** literal, fixed, case-sensitive:

```
Yes, with authorization.
```

(Trailing period included. NFKC-normalized at comparison time to
defeat homoglyph substitutions — see §6.2.) This is intentionally
**not** the server-issued per-approval nonce that W10's screen design
uses; this is a UI-only gesture confirming user intent, not a
cryptographic gate. The cryptographic gate is the *callback consumer's*
responsibility (later wave), which can still require a server-issued
nonce on top of this UI gesture.

---

## 5. Component contracts

All components live (when implemented) under
`apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/approvals/`.
The package and path are the sprint's ALLOWED FILES set; nothing else
is touched.

### 5.1 `ApprovalCard`

Top-level container. Composes the right sub-tree per `tier`.

Signature (Kotlin pseudocode — for the implementation wave):

```kotlin
@Composable
fun ApprovalCard(
    state: ApprovalCardState,
    onDecision: (ApprovalDecision) -> Unit,
    onEmergencyStop: () -> Unit = {},
    modifier: Modifier = Modifier,
)
```

`ApprovalCardState` shape:

```kotlin
data class ApprovalCardState(
    val approvalId: String,
    val tier: ApprovalTier,                 // Normal | Serious | Critical
    val title: String,
    val summary: String,
    val requestedBy: String,                // e.g. "agent:jarvis-prime"
    val createdAt: Instant,
    val expiresAt: Instant?,                // null for Normal
    val status: ApprovalStatus,             // Pending | Approved | Denied | Deferred | Expired
    val impact: ImpactReport? = null,       // required for Critical, null otherwise
    val rollback: RollbackSummary? = null,  // required for Critical, null otherwise
    val emergencyStopLabel: String? = null, // shown for Critical
)
```

**Tier composition rules:**

- `Normal` → renders title, summary, `ApprovalStatusBadge`. No
  buttons. No phrase field.
- `Serious` → adds `Approve` / `Deny` / `Defer` row.
- `Critical` → adds `CriticalActionImpactPanel`,
  `RollbackSummaryPanel`, `ExactPhraseConfirmationField`,
  emergency-stop link placeholder, and a two-step `Approve` confirm
  modal. `Approve` is **disabled** until the phrase matches and the
  state is still `Pending`.

**Required preconditions (assertions for unit tests):**

- `tier == Critical` ⇒ `impact != null && rollback != null`. The
  component throws `IllegalArgumentException` at composition if
  violated. This is the **default-deny invariant**: a critical
  action with no impact/rollback information cannot render an
  Approve path at all.
- `status != Pending` ⇒ Approve / Deny / Defer buttons are not
  rendered. The card becomes a status display.

### 5.2 `CriticalActionImpactPanel`

Required sub-component of Critical-tier cards.

```kotlin
@Composable
fun CriticalActionImpactPanel(
    impact: ImpactReport,
    modifier: Modifier = Modifier,
)

data class ImpactReport(
    val headline: String,                       // "This will delete 14 files in main."
    val scope: List<ImpactScopeEntry>,          // structured rows
    val externallyVisible: Boolean,             // shows banner "Externally visible"
    val moneyImpactCents: Long? = null,         // shows "Estimated cost: $X.YY"
    val securityImpact: SecuritySeverity? = null,
)

data class ImpactScopeEntry(val label: String, val value: String)

enum class SecuritySeverity { LOW, MEDIUM, HIGH, CRITICAL }
```

**Layout requirements:**

- Headline is `MaterialTheme.typography.titleMedium` weight Bold,
  visually prominent (Critical color from theme).
- Scope rendered as label/value rows (semantic role `Pair` for
  accessibility readout).
- `externallyVisible == true` shows a high-emphasis banner.
- `moneyImpactCents != null` shows formatted currency with the
  device locale; null hides the row entirely (do not show
  "Estimated cost: $0.00" — that misrepresents free actions).
- `securityImpact` shows a colored chip per severity; null hides
  the row.

**MUST NOT:**

- Truncate `headline` with ellipsis. Wrap to multiple lines.
- Render any clickable link inside the panel (clickable = potential
  social-engineering vector). Read-only text only.

### 5.3 `RollbackSummaryPanel`

Required sub-component of Critical-tier cards.

```kotlin
@Composable
fun RollbackSummaryPanel(
    rollback: RollbackSummary,
    modifier: Modifier = Modifier,
)

data class RollbackSummary(
    val available: Boolean,
    val mechanism: String,        // "git revert", "DB restore from snapshot s_2026-05-26T18:00Z", "None — irreversible"
    val estimatedTimeSeconds: Int?, // null if unknown
    val notes: String? = null,
)
```

**Layout requirements:**

- If `available == false`, the panel renders an **error-toned**
  banner reading "This action is irreversible" with the
  `mechanism` text below.
- If `available == true`, the panel renders a neutral panel with
  the mechanism, estimated time (if known), and notes.
- The panel **must** be rendered even when `available == false`;
  hiding it would let critical irreversibles slip past unaware
  approvers. The visible "irreversible" banner is the safety
  feature.

### 5.4 `ExactPhraseConfirmationField`

Required sub-component of Critical-tier cards. Single-line text
field with phrase-match gate.

```kotlin
@Composable
fun ExactPhraseConfirmationField(
    requiredPhrase: String,
    typed: String,
    onTypedChange: (String) -> Unit,
    isMatched: Boolean,            // hoisted-state contract; see below
    modifier: Modifier = Modifier,
)
```

**Match contract (executed by the consumer / ViewModel, not the
component — kept out of UI to keep the component pure):**

- Input is **NFKC-normalized** before comparison. This defeats
  homoglyph substitution (e.g. Cyrillic `А` for Latin `A`,
  full-width punctuation, combining marks).
- Comparison is **case-sensitive**.
- Comparison **trims leading and trailing whitespace only**.
  Internal whitespace must match the required phrase character-for-
  character.
- Required phrase for the W07 design is the literal string
  `Yes, with authorization.` (including the period). The
  implementation wave must store this as a `const val` in a single
  location and forbid alternate phrasings.

**Input field behaviour requirements:**

- `KeyboardOptions(autoCorrect = false, keyboardCapitalization = None,
  keyboardType = Ascii)`.
- Autofill suggestion suppressed (`Modifier.semantics { contentType
  = ContentType.Unspecified }` in the implementation wave).
- Paste is **blocked**. The field intercepts paste actions and
  shows an inline hint ("Type the phrase manually.").
- Long-press → no clipboard popup.
- `visualTransformation = None` — the phrase is visible. The phrase
  is not a secret; it is a user-intent gesture.
- `isError = typed.isNotEmpty() && !isMatched` — show subtle error
  state to indicate near-miss.
- Field is `enabled = false` once `status != Pending` or once the
  parent reports `Submitting` (passed via a separate flag in the
  Critical card's local state).

**Accessibility:**

- Label is "Type the confirmation phrase exactly as shown."
- `contentDescription` includes the literal required phrase so a
  screen-reader user can hear it.
- The error state announces "Phrase does not match." rather than
  reading every keystroke.

### 5.5 `Approve / Deny / Defer` callback contract

The three actions are **callback emitters only**. There is no
network code, no persistence, no clipboard write, no analytics
event, no navigation side-effect. The component emits one of:

```kotlin
sealed interface ApprovalDecision {
    val approvalId: String

    data class Approve(
        override val approvalId: String,
        val tier: ApprovalTier,
        val confirmedPhrase: String? = null,  // present for Critical, null otherwise
        val confirmedAt: Instant,
    ) : ApprovalDecision

    data class Deny(
        override val approvalId: String,
        val reason: String,                   // ≥ 8 chars; required
        val deniedAt: Instant,
    ) : ApprovalDecision

    data class Defer(
        override val approvalId: String,
        val deferUntil: Instant,
        val deferredAt: Instant,
    ) : ApprovalDecision
}
```

**Emission rules:**

- `Approve` is only emitted when, per tier:
  - `Normal` — never (Normal has no Approve button).
  - `Serious` — single tap.
  - `Critical` — phrase matches **and** the second-step confirm
    modal is confirmed. The component must show a modal ("Confirm:
    submit Approve?") before emitting; the modal's cancel must
    leave the state untouched.
- `Deny` opens a small bottom-sheet collecting a free-text reason
  (≥ 8 chars, ≤ 280 chars, auto-correct allowed — reason is audit
  text, not a secret). Emit `Deny` after the user submits the
  reason. The reason field is required because the absence of a
  reason makes audit logs useless.
- `Defer` opens a chooser: `15 min`, `1 hour`, `Until tomorrow
  09:00 (local)`. Emit `Defer` with the resolved `Instant`. No
  reason field.
- Deny and Defer are **always available** for Pending Serious /
  Critical cards (no phrase gate, no two-step confirm). Safety
  defaults must always be one tap.

**Callback consumer responsibility (not in this component):**

- Validate that the approval is still pending server-side before
  acting on the decision.
- Apply rate-limiting / replay protection.
- Persist audit events (mirroring W10's `aci.approval.decision`
  schema where applicable).
- Translate the UI decision into a backend RPC call. **None of
  this lives in the UI components.**

### 5.6 `EmptyApprovalState`

Rendered by parent surfaces (inbox / timeline) when no approvals
are pending.

```kotlin
@Composable
fun EmptyApprovalState(
    headline: String = "No pending approvals",
    subtext: String = "Jarvis Prime will surface anything that needs your call here.",
    modifier: Modifier = Modifier,
)
```

- Pure stateless display.
- No action buttons. (No "create approval" or similar — approvals
  come from the backend, not from the human.)
- Accessibility: announced as a single combined text block, not as
  two separately-focused texts.

### 5.7 `ApprovalStatusBadge`

Small inline badge showing approval status. Renders inside
`ApprovalCard` and may also be used in list/timeline rows.

```kotlin
@Composable
fun ApprovalStatusBadge(
    status: ApprovalStatus,
    modifier: Modifier = Modifier,
)

enum class ApprovalStatus { PENDING, APPROVED, DENIED, DEFERRED, EXPIRED }
```

**Visual mapping (theme tokens to be defined by the future
implementation wave; described here semantically):**

| Status | Visual treatment | Semantic role |
|---|---|---|
| `PENDING` | Neutral container, primary-emphasis label | "needs your attention" |
| `APPROVED` | Success container, success label | "you said yes" |
| `DENIED` | Subtle muted container, neutral label | "you said no" (intentionally **not** error-toned: denial is the safe default and should not feel like a mistake) |
| `DEFERRED` | Neutral container, "Snoozed until …" subtext | "will return" |
| `EXPIRED` | Warning container, warning label | "TTL elapsed; re-request needed" |

**Accessibility:**

- `contentDescription` is the explicit status word; do not rely on
  color alone.
- Status changes announce via `LiveRegion` when the badge is the
  only thing changing in an otherwise-static card.

---

## 6. Safety contract

### 6.1 MUST (UI surface)

- Approve button for Critical tier is **disabled** until the typed
  phrase matches and the card is still `Pending`.
- Deny and Defer are always available for Pending Serious /
  Critical cards.
- Emergency-stop link placeholder is rendered for Critical-tier
  cards. The link surface is a `TextButton` with
  `onEmergencyStop` callback. The component **does not**
  implement the stop action; routing belongs to the consumer (this
  is consistent with the "UI emits callbacks/events only" rule).
- Critical-tier Approve emits an event only after both gates pass
  (phrase match + two-step confirm modal).
- The required phrase string is owned by a single source-of-truth
  constant. Tests assert the literal value `Yes, with
  authorization.` (with the period).
- Components default-deny: if `ImpactReport` or `RollbackSummary`
  is missing on a Critical card, composition fails fast.

### 6.2 MUST (security warnings the implementation wave must encode)

- Phrase comparison is **NFKC-normalized** before equality.
- Phrase field disables autocorrect, autofill, paste, and clipboard
  popups.
- Phrase value is **never** written to logs, analytics, crash
  reporters, or A/B systems.
- Components do not read or write `SharedPreferences`, DataStore,
  Room, network, files, the clipboard, or notifications. They are
  stateless given their state inputs.
- Components do not register receivers, services, content
  providers, or accessibility hooks.
- Components are independent of `MainActivity.kt`; they expose
  hoisted state and callbacks so the host activity can wire them
  without leaking lifecycle into the UI.

### 6.3 MUST NOT

- Execute any destructive action (no `delete`, no `submit`, no
  `dispatch`, no network call inside the components).
- Issue gateway calls — there is no gateway client in the
  approvals package by design.
- Auto-fill, paste, suggest, autocomplete, or remember the
  confirmation phrase.
- Render a "remember decision" / "approve all like this" / "do not
  ask again" affordance. Each approval is independent.
- Default any Critical-tier card to `Approve`-enabled.
- Hide the irreversible-action banner when `rollback.available ==
  false`.
- Treat a Deny without a reason as valid.
- Persist any approval state across process death (state hoisting
  + ViewModel ownership; the UI itself is stateless).
- Speak to a microphone, Call Log, SMS, or always-listening API
  (Global Product Rules — out of scope and forbidden by product
  policy).

---

## 7. State + ViewModel ownership

The components are **stateless** given their inputs (hoisted state +
callbacks). The `ApprovalCardState`, `ApprovalDecision` sealed type,
and supporting data classes (§5.1, §5.5) live in the approvals
package. The ViewModel that owns the live state — and the consumer
that wires `onDecision` to a real backend — are out of scope for
W07.

Recommended (for the implementation wave) hoisted-state shape:

```kotlin
@Stable
class CriticalApprovalUiState(
    private val initialPhrase: String = "",
    val requiredPhrase: String = REQUIRED_CRITICAL_PHRASE,
) {
    var typed: String by mutableStateOf(initialPhrase)
        private set
    val matched: Boolean by derivedStateOf {
        normalize(typed.trim()) == normalize(requiredPhrase)
    }
    fun onTypedChange(newValue: String) { typed = newValue }

    companion object {
        const val REQUIRED_CRITICAL_PHRASE: String = "Yes, with authorization."
        private fun normalize(s: String): String =
            java.text.Normalizer.normalize(s, java.text.Normalizer.Form.NFKC)
    }
}
```

The constant `REQUIRED_CRITICAL_PHRASE` is the single source of
truth. Tests must reference it directly; they must not duplicate
the literal in a second location.

---

## 8. Permission kernel UI

The sprint header pairs "approval cards" with a **permission
kernel**. The two surfaces share an intent: gating destructive or
sensitive actions behind explicit user consent. They differ in
trigger:

- *Approval cards* respond to backend-initiated approval requests.
- *Permission kernel* responds to UI-initiated permission requests
  (microphone, notifications, optional integrations) that the user
  themselves triggered.

The Global Product Rules constrain the permission kernel sharply:

- **No automatic notification permission prompt on first launch.**
  The kernel never preemptively requests `POST_NOTIFICATIONS`. The
  prompt only appears in response to an explicit user action that
  asks for notifications (e.g. tapping a "Get notified" toggle).
- **Microphone permission only after the user taps voice.** The
  kernel exposes a permission rationale card that explains why the
  mic is needed, then routes to the system prompt only after the
  user taps "Continue."
- **Optional permissions must remain optional.** Denial paths must
  let the app continue working with the optional feature disabled
  (no nag loops, no app-restart prompts).

### 8.1 `PermissionRationaleCard` (component, in scope for the
implementation wave — same allowed-files path)

```kotlin
@Composable
fun PermissionRationaleCard(
    permission: JarvisPermission,
    onContinue: () -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
)

enum class JarvisPermission {
    MICROPHONE,
    NOTIFICATIONS,
    // Future optional permissions are added here, never silently.
}
```

**Constraints:**

- Card body explains *why this app wants this permission* in plain
  language, *what happens if denied* (always: "the app keeps
  working without this feature"), and *what data leaves the
  device* (microphone: "audio only while recording, never stored,
  never sent to third parties unless you also enable cloud
  transcription"; notifications: "no data leaves the device for
  notifications").
- `onContinue` triggers the system permission prompt **only after
  the user explicitly taps Continue**. The component never calls
  `ActivityResultLauncher` itself.
- `onDismiss` closes the rationale without prompting. Dismissal
  must not be treated as denial; the app retains the ability to
  re-offer the rationale later if the user invokes the feature
  again.

### 8.2 What the permission kernel UI does NOT do

- It does not call `ActivityCompat.requestPermissions(...)`. That
  is a host responsibility wired via `ActivityResultLauncher`
  outside the components package.
- It does not query current permission status. Status is hoisted in
  from the host so the components remain side-effect-free.
- It does not render permanently-blocked / "go to Settings" guidance.
  That UX belongs in a settings surface (`ui/jarvis/settings/`),
  which is **not** in the W07 ALLOWED FILES set.

---

## 9. File tree for the future implementation wave

**Status: paths assumed.** `apps/android/` does not exist in this
repo (§3). The future implementation wave must verify the actual
module layout post-W00-scaffold before creating files; if the
project decides on a different module name, the table is rewritten
before any file is created.

| Path | Status | Purpose |
|---|---|---|
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/approvals/ApprovalCard.kt` | NEW (future) | §5.1 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/approvals/CriticalActionImpactPanel.kt` | NEW | §5.2 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/approvals/RollbackSummaryPanel.kt` | NEW | §5.3 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/approvals/ExactPhraseConfirmationField.kt` | NEW | §5.4 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/approvals/ApprovalActions.kt` | NEW | Approve / Deny / Defer button row + reason sheet + defer chooser; §5.5 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/approvals/EmptyApprovalState.kt` | NEW | §5.6 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/approvals/ApprovalStatusBadge.kt` | NEW | §5.7 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/approvals/model/ApprovalCardState.kt` | NEW | data classes from §5.1 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/approvals/model/ApprovalDecision.kt` | NEW | sealed type from §5.5 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/approvals/state/CriticalApprovalUiState.kt` | NEW | §7 |
| `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/approvals/PermissionRationaleCard.kt` | NEW | §8.1 |
| `apps/android/app/src/test/java/com/aci/hermes/ui/jarvis/approvals/CriticalApprovalUiStateTest.kt` | NEW | phrase-match comparator tests (§13.1) |
| `apps/android/app/src/test/java/com/aci/hermes/ui/jarvis/approvals/ApprovalCardContractTest.kt` | NEW | composition preconditions (§13.1) |
| `apps/android/app/src/androidTest/java/com/aci/hermes/ui/jarvis/approvals/ApprovalCardComposeTest.kt` | NEW | Compose UI tests (§13.2) |

The future implementation wave **must not** create files outside
this list without first writing the deviation into its own wave
report.

---

## 10. Prerequisite gap

To land any Kotlin from this design, the following must exist
**before** the implementation wave begins — none of it can be
authored in W07 because every file below is on the FORBIDDEN list:

1. `apps/android/settings.gradle.kts` — root Gradle settings,
   `include(":app")`.
2. `apps/android/build.gradle.kts` — root build with AGP + Kotlin
   plugins pinned.
3. `apps/android/app/build.gradle.kts` — module build:
   `compileSdk 35`, `minSdk 26+`, Compose BOM, Material 3, Lifecycle
   ViewModel, `kotlin("plugin.compose")`, kotlinx-coroutines.
4. `apps/android/gradle/wrapper/gradle-wrapper.properties` +
   `gradle-wrapper.jar` + `gradlew` + `gradlew.bat`.
5. `apps/android/app/src/main/AndroidManifest.xml` — minimal:
   `allowBackup="false"`, `exported="false"` for any inner
   activities, `FLAG_SECURE` defaults for sensitive screens.
6. `apps/android/app/src/main/java/com/aci/hermes/MainActivity.kt`
   — minimal Compose host; routes to a placeholder screen.
7. `apps/android/app/src/main/java/com/aci/hermes/ui/theme/*.kt`
   — `JarvisPrimeTheme`, `Color.kt`, `Type.kt` so cards have a
   theme to inherit from.

All seven items are in this sprint's FORBIDDEN FILES list. They
must be delivered by a dedicated **W00 — Android module scaffold**
wave with its own contract. Suggested allowed-files set for W00 is
exactly the seven paths above plus a `docs/aci/reports/W00_*.md`
report; nothing else.

Once W00 has landed, a W07-bis wave can implement the components
in §5–§8 against the now-buildable module.

---

## 11. Cross-fork scope ambiguity

The sprint header names repo
`A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent`. The Claude Code
harness in this session is scoped to
`echerd27-design/hermes-agent`. The two are different remotes; only
the latter is reachable. The pre-flight (§3) confirmed that the
echerd27-design fork does not carry the Android module.

Three possibilities, all of which the owner must disambiguate
before W07-bis is opened:

1. **The Android module lives on the A-C-I-SOFTWARE-AND-DEVELOPMENT
   fork.** In that case W07-bis runs in that org's harness with the
   same component spec from §5–§8.
2. **The Android module is yet to be created on either fork.** In
   that case W00 (§10) is the next wave, then W07-bis on whichever
   fork the owner decides is the canonical home.
3. **The two forks have diverged.** In that case the canonical
   target needs an explicit owner decision; the W10 sibling-branch
   precedent suggests this fork (echerd27-design) is the active
   one, but that is not confirmed.

This report is shipped on `echerd27-design/hermes-agent` because
that is the only reachable target; the report itself documents the
ambiguity so it survives the cross-fork question.

---

## 12. Test plan for the future implementation wave

The wave that actually writes the components must include the
tests below. Categories may not be skipped without an explicit
written reason in that wave's report.

### 12.1 Unit tests (JVM)

*Framework:* JUnit 4 (matches the existing
`apps/android/app/src/test/...` layout on sibling branch
`aci/wave-10-android-android-job-models`).

- `CriticalApprovalUiStateTest`
  - Exact match returns `matched = true`.
  - Case-mismatch returns `matched = false`
    (`"yes, with authorization."` rejected).
  - Trailing whitespace trimmed (`"Yes, with authorization. "` →
    matched).
  - Internal whitespace **not** trimmed
    (`"Yes,  with authorization."` → not matched).
  - Trailing period required (`"Yes, with authorization"` → not
    matched).
  - NFKC homoglyph rejection: Cyrillic `Ｙ` / full-width
    punctuation variants → not matched.
  - Empty string and whitespace-only never matched.
- `ApprovalDecisionTest`
  - Approve only emitted with non-null `confirmedPhrase` on Critical
    tier.
  - Deny requires `reason.length >= 8` (constructor or factory
    asserts).
  - Defer requires `deferUntil > deferredAt`.
- `ApprovalCardContractTest`
  - `Critical` tier with `impact == null` throws
    `IllegalArgumentException` at composition.
  - `Critical` tier with `rollback == null` throws likewise.
  - Card with `status != PENDING` does not expose action callbacks
    (tested by capturing emitted decisions over the card's lifecycle).

### 12.2 Compose UI tests (instrumentation)

*Framework:* `androidx.compose.ui.test.junit4`.

- Critical-tier card: Approve disabled at first render; types
  matching phrase → Approve enabled; clicks Approve → two-step
  modal appears; confirms modal → `onDecision` fires with
  `Approve.confirmedPhrase = "Yes, with authorization."`.
- Critical-tier card: Deny is enabled and one-tap; bottom-sheet
  collects reason; emitting `Deny` requires reason ≥ 8 chars
  (button stays disabled below).
- Serious-tier card: Approve / Deny / Defer all enabled at first
  render; Approve fires after a single tap.
- Normal-tier card: no Approve / Deny / Defer buttons rendered;
  `ApprovalStatusBadge` is present.
- `EmptyApprovalState` renders both headline and subtext; semantics
  tree contains exactly one combined block.
- `RollbackSummaryPanel` with `available == false` renders the
  irreversibility banner.
- `ExactPhraseConfirmationField` rejects paste:
  `performKeyInput { performTextInputSelection(...) }` then a
  programmatic paste attempt leaves the field empty + shows the
  inline hint.
- `PermissionRationaleCard`: `onContinue` only fires after the user
  taps the Continue button; the component itself never calls a
  permission API.

### 12.3 Accessibility checks

- All cards: tap-target ≥ 48dp.
- Status badge: `contentDescription` matches enum literal
  (`Pending` / `Approved` / `Denied` / `Deferred` / `Expired`).
- Critical card: emergency-stop placeholder is reachable by
  TalkBack focus traversal *before* the Approve button (so a
  screen-reader user encounters the stop affordance first).

### 12.4 Tests **not** in W07-bis scope

- No network / repository / integration tests. The components do
  not touch network.
- No biometric / Keystore / Play Integrity tests — those land in
  the W10 dedicated approval-screen wave, not the card components.

---

## 13. Validation for this wave

This wave produced only a planning document. No source, no
fixtures, no schemas, no Gradle output.

- `assembleDebug` — **skipped with reason**: there is no Gradle
  project in this repository (§3, §10). The contract clause
  *"Every change needs validation or a clear skipped-test reason"*
  is satisfied by this paragraph.
- `testDebugUnitTest` — **skipped with reason**: same as above.
- `git diff --stat` — single new file under `docs/aci/reports/`
  plus the directory creation (`docs/aci/`, `docs/aci/reports/`
  were previously absent on `main`; W10 sibling branches that
  created them have not merged).
- `git status --short` — exactly one untracked then staged file
  before commit; clean tree after.

No code paths are exercised. No tests are added. No new
dependencies. No CI changes. No secrets.

---

## 14. Risks (this wave)

- **Spec drift.** The component contracts in §5 are unconsumed
  until W00 + W07-bis land. If the W00 scaffold wave chooses a
  different module layout or a different Compose BOM than §10
  expects, §9's file paths and §5's signatures must be revisited
  before W07-bis begins.
- **Tier-classification dependency.** §4 declares tier is
  server-supplied. If the backend approval-request schema does not
  yet carry a `tier` field, defining it is a backend wave. W07-bis
  must not write a client-side tier-inferrer; that is explicitly
  an anti-pattern (§4).
- **Cross-fork resolution (§11).** If the canonical Android module
  lives on `A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent`, W07-bis
  must run in that harness. This report is portable: it carries
  enough detail to be re-used there verbatim.
- **Phrase-string regression.** The literal
  `Yes, with authorization.` is a contract with the user. Any
  future translation, copy review, or accessibility rewrite must
  preserve the exact phrase (or change the phrase **and** the
  associated unit tests in lockstep). The W07-bis implementation
  wave should add a `// DO NOT EDIT WITHOUT WAVE` annotation on
  the constant; that is the only intentional code comment this
  design recommends.

---

## 15. Draft PR summary

**Title:** `W07: Add Jarvis Prime approval cards and permission
kernel UI`

**Body (planned):**

> Wave 07 of the ACI Jarvis Prime initiative. **Report-only PR** —
> no Kotlin, no Compose, no Gradle, no `AndroidManifest.xml`. The
> sprint targeted `apps/android/app/src/main/java/com/aci/hermes/ui/jarvis/approvals/**`
> but the Android Gradle module does not exist in this repository
> (pre-flight verified — see report §3); the scaffolding files that
> would make Kotlin compile are on the sprint's FORBIDDEN list.
>
> Per the NON-OVERLAP CONTRACT — *"If a needed change is outside
> ALLOWED FILES, do not edit it; write it into the report"* — the
> deliverable is a single documentation file specifying:
>
> - Approval-tier model (Normal / Serious / Critical) and the
>   literal Critical confirmation phrase (`Yes, with authorization.`).
> - Seven Compose component contracts: `ApprovalCard`,
>   `CriticalActionImpactPanel`, `RollbackSummaryPanel`,
>   `ExactPhraseConfirmationField`, `EmptyApprovalState`,
>   `ApprovalStatusBadge`, plus the Approve / Deny / Defer callback
>   surface.
> - Safety contract (MUST / MUST NOT for the UI surface).
> - Permission kernel UI (microphone-after-tap, no auto
>   notification prompt) per the Global Product Rules.
> - Hoisted-state ViewModel ownership pattern.
> - File-tree plan for the future implementation wave.
> - Prerequisite gap: a W00 module-scaffold wave must land first
>   (the seven files in §10 are all FORBIDDEN here).
> - Cross-fork question: sprint named
>   `A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent`, harness scoped
>   to `echerd27-design/hermes-agent`; canonical Android home
>   needs an owner call.
> - Test plan for W07-bis (JVM unit + Compose UI + accessibility).
>
> Validation: `assembleDebug` and `testDebugUnitTest` are skipped
> with explicit reason (no Gradle project). `git diff --stat`
> shows a single new file under `docs/aci/reports/`.
>
> Precedent: sibling branches
> `aci/wave-10-android-approval-screen-plan` and
> `aci/wave-10-android-launch-audit` both shipped report-only PRs
> after independently confirming the same `apps/android/` absence.
>
> Draft PR. Do not merge. Implementation wave (Kotlin/Compose) is
> a separate, future wave that depends on a prior W00 scaffold
> wave.

**State:** draft.
**Base:** `main`.
**Head:** `claude/upbeat-hypatia-EiqPO`.
**Repo:** `echerd27-design/hermes-agent` (harness-scoped).

---

## 16. Wave Report Footer

### Changed files

- `docs/aci/reports/W07_APPROVAL_PERMISSION_UI_REPORT.md` (NEW)
- `docs/aci/reports/` directory created (NEW; previously absent on
  `origin/main`, present on other unmerged wave branches).
- `docs/aci/` directory created (NEW; same reason).

### Tests run

- None. Wave produced only a planning document. No source,
  fixtures, or schemas changed.
- Acceptance verification: `git diff --stat` shows exactly one new
  file under `docs/aci/reports/`.

### Risks

See §14.

### Rollback

1. Close the draft PR without merging.
2. `git rm docs/aci/reports/W07_APPROVAL_PERMISSION_UI_REPORT.md`
   (optional, if the report needs to be retracted before the PR is
   closed).
3. Optionally `rmdir docs/aci/reports docs/aci` if no other wave
   has merged a sibling report in the meantime.
4. `git branch -D claude/upbeat-hypatia-EiqPO` locally.

No code, config, dependency, secret, infrastructure, or environment
is touched. Rollback is metadata-only.

### Open questions

1. **Canonical Android home.** Is `apps/android/` intended to live
   on `A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent` (sprint
   header) or `echerd27-design/hermes-agent` (this harness)? §11.
2. **W00 scaffold ownership.** Who lands the seven scaffold files
   in §10 — a dedicated W00 wave by Claude Code, or an owner-led
   bootstrap? The files are owner-sensitive (signing config,
   package id, AndroidManifest) and may belong on an owner-only
   wave.
3. **Tier source.** Does the backend approval-request schema carry
   a `tier: ApprovalTier` field today, or is adding it a separate
   backend wave?
4. **Permission kernel scope.** §8 covers microphone and
   notifications. The list of "optional permissions" referenced by
   the Global Product Rules is open-ended. A future wave should
   enumerate them so the kernel UI knows which `JarvisPermission`
   enum values to support.

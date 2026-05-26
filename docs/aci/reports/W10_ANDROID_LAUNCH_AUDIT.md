# W10 — Android Launch Audit

| | |
|---|---|
| Wave | ACI W10 — Android launch audit |
| Branch | `aci/wave-10-android-launch-audit` |
| Mission | Audit Android app launch gaps and produce a launch-readiness checklist. |
| Scope | Documentation only. **No Kotlin / Gradle / Manifest / Capacitor edits.** |
| Allowed files | `docs/aci/reports/W10_ANDROID_LAUNCH_AUDIT.md` |
| Forbidden | `apps/android/**`, all source code, README.md, pyproject.toml, uv.lock |
| Date | 2026-05-26 |

---

## Executive verdict

**There is no Android app in this repository.** The mission's audit
target — `apps/android/` — does not exist on `main`, on this branch,
or anywhere in the working tree. There are no `*.kt`, `*.kts`,
`AndroidManifest.xml`, `build.gradle*`, `settings.gradle*`,
`capacitor.config.json`, `PLAY_STORE.md`, or `PUBLISH.md` files in
the repo. The only "mobile" surface in `hermes-agent` today is the
Termux + Slack command path documented in
`docs/mobile-voice-development-workflow.md` and `README.md`.

The audit therefore covers **the gap between "nothing exists" and
"Play Store-launchable Android client"**, not a review of existing
Kotlin. Every requested topic (screens, connection flow, gateway URL,
token handling, mock mode, push notifications, skill picker, voice
input, release signing, cleartext/HTTPS, Play Store readiness) is
reported as `MISSING` with the smallest safe PR plan that lands the
scaffold without touching owner-only walls.

The Wave 10 deliverable should be **the implementation checklist
below**, not premature Kotlin. A future wave (W11+) can open
`apps/android/` once the owner has signed off on the package id,
backend topology, and signing-key custody plan in this report.

---

## Audit method

| Step | Command | Result |
|---|---|---|
| 1. Confirm absence of `apps/` | `ls apps/ 2>/dev/null` | Directory does not exist |
| 2. Search for any Android source | `find . -iname "*.kt" -o -iname "*.kts" -o -iname "AndroidManifest*"` | 0 matches |
| 3. Search for Capacitor | `find . -name "capacitor.config*"` | 0 matches |
| 4. Search for Gradle / Play artifacts | `find . -name "build.gradle*" -o -name "PLAY_STORE.md" -o -name "PUBLISH.md"` | 0 matches |
| 5. Audit existing rule for the surface | Read `skills/aos-enterprise-council/rules/android-mobile-and-release-surface.md` | Rule exists; paths it references (`android/**`, `capacitor.config.json`, `PLAY_STORE.md`) are not present |
| 6. Audit existing mobile guidance | Read `docs/mobile-voice-development-workflow.md`, `docs/slack-mobile-command-policy.md`, `scripts/hermes-mobile-workspace-init.sh` | Mobile = Termux + Slack today; not a native Android client |
| 7. Audit gateway auth model | Read `hermes_cli/web_server.py`, `web/src/lib/api.ts`, `web/src/lib/gatewayClient.ts`, `tui_gateway/ws.py` | Localhost-only by default; ephemeral session token injected into `index.html` |
| 8. Audit owner walls | Read `AGENTS.md`, `skills/aos-enterprise-council/rules/android-mobile-and-release-surface.md` | Play Store submission, signed AAB upload, prod deploy, DNS = owner-only |
| 9. Audit recovered sources | Read `recovered-agent-sources/from-hazmat-command/docs/skills/mobile-capacitor-release-check.md` | Capacitor playbook from sister repo (`com.hazmatcommand.app`) — **not** committed to this repo |

---

## Inventory — what currently exists vs. what the audit asked for

### Files the rule expects (none present)

| Expected path | Source of expectation | Present? |
|---|---|---|
| `apps/android/` | Wave 10 mission | No |
| `android/` | `skills/aos-enterprise-council/rules/android-mobile-and-release-surface.md` line 3 | No |
| `capacitor.config.json` | Same rule, line 4 | No |
| `PLAY_STORE.md` | Same rule, line 5 | No |
| `PUBLISH.md` | Same rule, line 6 | No |
| `docs/releases/**` | Same rule, line 8 | No |
| `public/manifest.json` / `public/sw.js` | Recovered hazmat-command skill | No |
| `src/pages/SharedUpload.jsx` / `MainActivity.java` | Recovered hazmat-command skill | No |

### Files that do exist and matter for the eventual Android client

| Path | Role for the future Android client |
|---|---|
| `tui_gateway/server.py` | JSON-RPC dispatcher the Android client would call |
| `tui_gateway/ws.py:19` | `@app.websocket("/api/ws")` — the WebSocket endpoint the client would connect to |
| `tui_gateway/transport.py` | Frame format (`write_json`, `WSTransport`) the client must speak |
| `hermes_cli/web_server.py:86` | `_SESSION_TOKEN = secrets.token_urlsafe(32)` — process-lifetime token |
| `hermes_cli/web_server.py:87` | `_SESSION_HEADER_NAME = "X-Hermes-Session-Token"` — the auth header |
| `hermes_cli/web_server.py:98–107` | CORS restricted to `localhost / 127.0.0.1` — Android cannot speak to it from a phone over Wi-Fi without changing this |
| `hermes_cli/web_server.py:158–194` | Anti-DNS-rebinding host allow-list — blocks non-loopback hosts unless explicit `0.0.0.0` opt-in |
| `hermes_cli/web_server.py:3674–3685` | `<script>window.__HERMES_SESSION_TOKEN__="…"</script>` injection into `index.html` (browser-only auth path) |
| `web/src/lib/api.ts:31–45` | Web client reads token from `window.__HERMES_SESSION_TOKEN__` and sends `X-Hermes-Session-Token` header |
| `web/src/lib/gatewayClient.ts` | Reference implementation of the JSON-RPC-over-WS protocol the Android client must mirror |
| `gateway/session_context.py` | `HERMES_SESSION_PLATFORM`, `HERMES_SESSION_CHAT_ID`, `HERMES_SESSION_USER_ID`, etc. — context vars the Android transport would need to populate |
| `gateway/platforms/` | Platform adapters (Slack, Telegram, WhatsApp, …) — pattern an `android` platform adapter would follow if Android were wired as a Hermes platform |
| `docs/mobile-voice-development-workflow.md` | Today's mobile contract (Termux + Slack); product baseline an Android app would either replace or complement |
| `docs/slack-mobile-command-policy.md` | Owner-only / off-limits action list any Android UI must respect |
| `scripts/hermes-mobile-workspace-init.sh` | Today's "mobile" bootstrapper — a Termux helper, not an APK builder |
| `skills/aos-enterprise-council/rules/android-mobile-and-release-surface.md` | Rule that will auto-activate the moment `apps/android/` (or `android/`) is created |
| `AGENTS.md` line 716 | Owner control over merges, deploys, publishing, credential changes, spending |

### Repository topology check

```
apps/                          MISSING
android/                       MISSING
capacitor.config.json          MISSING
PLAY_STORE.md                  MISSING
PUBLISH.md                     MISSING
docs/releases/                 MISSING
docs/aci/                      newly created (this report only)
docs/aci/reports/              newly created (this report only)
```

---

## Per-topic findings

### 1. Current screens

- **Finding:** No screens. No `MainActivity`, no Compose `@Composable`,
  no XML layouts, no Capacitor `index.html` shell.
- **Expected paths (do not exist):**
  `apps/android/app/src/main/java/.../MainActivity.kt`,
  `apps/android/app/src/main/res/layout/*.xml`,
  `apps/android/app/src/main/AndroidManifest.xml`.
- **Reference for what the screen would need to render:**
  the web client's chat surface is `web/src/pages/ChatPage.tsx` and
  the sidebar inventory at `web/src/components/ChatSidebar.tsx`;
  the wire protocol is JSON-RPC over WS per `tui_gateway/ws.py:19`
  and `web/src/lib/gatewayClient.ts`.
- **Gap:** A v0 Android client needs, at minimum, a connection /
  status screen, a chat transcript view, a composer, and a settings
  pane (gateway URL, token paste, mock-mode toggle).

### 2. Connection flow

- **Finding:** Undefined. The web client assumes it is served by the
  Hermes web server itself (`web/src/lib/api.ts:1–18` describes
  base-path injection from `X-Forwarded-Prefix`), so the token
  arrives via the same response that delivers `index.html`. An
  Android app cannot rely on that mechanism — it ships separately
  from the server response.
- **Gateway endpoints the client must speak:**
  - WebSocket: `ws(s)://<host>:<port>/api/ws?token=<…>`
    (`tui_gateway/ws.py:19`, `web/src/lib/gatewayClient.ts`).
  - REST: `/api/status`, `/api/sessions`, `/api/logs`,
    `/api/analytics/...`, `/api/model/...`, `/api/config*`, all
    requiring header `X-Hermes-Session-Token`
    (`web/src/lib/api.ts:65–98`,
    `hermes_cli/web_server.py:87`).
- **Server bind:** `hermes_cli/web_server.py:4583` calls
  `uvicorn.run(app, host=host, port=port, ...)`. The default is
  loopback; only an explicit `0.0.0.0` bind exposes the server to a
  LAN-attached phone (`web_server.py:194`).
- **CORS:** `web_server.py:102–107` restricts origins to
  `localhost / 127.0.0.1` — an Android WebView would either need to
  load `https://localhost` (impractical on device) or the server
  needs an explicit, gated allow-list extension.
- **Gap:** No documented Android-friendly connection flow. The
  smallest plausible v0 path is **paste-token** (manual): the owner
  starts `hermes web --host 0.0.0.0 --port <p>` on Termux, reads the
  printed session token, and pastes both into the Android settings
  pane. Anything more (auto-discovery, QR-code pairing, OAuth-style
  flow) is a follow-up wave.

### 3. Gateway URL behavior

- **Finding:** Undefined. Two patterns are visible in the codebase
  and both must be ruled in or out by the owner:
  1. **Local Termux gateway** — Hermes on-device, app talks to
     `http://127.0.0.1:<port>`. Pros: no exposed network surface, no
     cleartext-over-Wi-Fi risk. Cons: only works when both Hermes
     and the app run on the same device; requires Termux foreground
     service to keep the gateway alive.
  2. **LAN gateway** — Hermes on a desktop / laptop / Pi, app talks
     to `http://<lan-ip>:<port>` from the phone. Pros: real
     two-device workflow. Cons: cleartext on Wi-Fi (see topic 10);
     blocked by current CORS + DNS-rebinding guards in
     `hermes_cli/web_server.py:158–219`.
- **Cloud-hosted gateway is out of scope** for this wave — that
  crosses the owner-only Vercel / DNS / cert wall in
  `skills/aos-enterprise-council/rules/android-mobile-and-release-surface.md`
  L24–36 and `AGENTS.md` L716.
- **Gap:** The gateway URL field has no spec yet. Choose between
  loopback-only (Termux co-resident) and LAN (requires server-side
  CORS / host allow-list relaxation, which must be gated behind an
  explicit flag — see PR plan).

### 4. Token handling

- **Finding:** The token model today is **server-injects-into-HTML**.
  - `hermes_cli/web_server.py:86` generates a fresh
    `secrets.token_urlsafe(32)` per server start, never persisted,
    dies with the process.
  - `web_server.py:3685` injects it as
    `<script>window.__HERMES_SESSION_TOKEN__="…"</script>`.
  - `web/src/lib/api.ts:30–45` reads it from `window` and sends
    `X-Hermes-Session-Token` on every `/api/*` request.
  - `web/src/lib/gatewayClient.ts` passes it as a `?token=…` query
    param on the WS upgrade URL.
- **What the Android client must do:**
  1. Accept the token via paste (or QR scan in a later wave).
  2. Store it in **EncryptedSharedPreferences** (AndroidX Security)
     or the Android Keystore — never plain `SharedPreferences`,
     never logged, never in a fixture.
  3. Send it as `X-Hermes-Session-Token` on every REST call.
  4. Append it as `?token=<urlencoded>` on the WS upgrade only —
     never as a long-lived URL param embedded in a deep link.
  5. Treat any 401 / 403 as "server was restarted; ask the owner to
     re-paste."
- **Gap:** No client storage layer exists. No paste UI. No QR
  scanner. No token-rotation behavior. No 401 → re-pair UX.

### 5. Mock mode

- **Finding:** No Android mock mode exists (no client exists).
  However the surface is friendly to one — the gateway speaks a
  stable JSON-RPC dialect (`tui_gateway/transport.py`,
  `tui_gateway/ws.py`), so a mock backend that replays canned
  events is straightforward.
- **Gap:** Define a `BuildConfig.MOCK_MODE` (or DataStore flag)
  that swaps the network client for a fixture replayer. Mock
  fixtures should live under
  `apps/android/app/src/main/assets/mock/` and mirror real
  `gateway.ready` / `agent.message` / `tool.call` events from a
  recorded session. **Mock mode must default OFF in release
  builds** and refuse to ship if any release flavor leaves it on.

### 6. Push notifications (missing)

- **Finding:** Not present. No FCM (`google-services.json`,
  `FirebaseMessagingService` subclass), no manifest receiver, no
  server-side push dispatcher in `tui_gateway/` or `gateway/`.
- **Owner-wall consideration:** Wiring FCM requires a Firebase
  project, a `google-services.json` keyed to a package id, and a
  server-side credential. **All three are owner-gated** under
  `AGENTS.md` L716 (credential changes, spending).
- **Gap:** Decision needed before scaffolding — FCM vs.
  in-app long-poll over the existing WS. The smallest safe path is
  **no push in v0**: keep the app foreground-only, rely on WS
  reconnect for state. FCM lands in a separate wave with owner
  sign-off on the Firebase project.

### 7. Skill picker (missing)

- **Finding:** Not present. The web UI has a slash-popover
  (`web/src/components/SlashPopover.tsx`) and a sidebar that lists
  skills (`web/src/components/ChatSidebar.tsx`), driven by
  `web/src/lib/slashExec.ts`. The Android equivalent does not
  exist.
- **Data source:** The skills list comes from the gateway's
  `/api/config` / `/api/model/...` family in `web/src/lib/api.ts`
  and the slash registry in
  `gateway/slash_access.py` / `tui_gateway/slash_worker.py`. The
  Android client can call the same endpoints with the same header.
- **Gap:** Define an Android skill-picker UI (modal sheet with
  search). Mirror the web slash registry's contract; do not invent
  a parallel list. Skill execution must respect the owner-only
  walls in `docs/slack-mobile-command-policy.md` (no merge / no
  deploy / no DNS / no spend from the mobile surface).

### 8. Voice input (missing)

- **Finding:** Not present. No `SpeechRecognizer` integration, no
  `RecognizerIntent`, no on-device Whisper bundle. The current
  "mobile voice" path is **Slack → Hermes** or **Termux dictation →
  `hermes "JARVIS capture: …"`** as described in
  `docs/mobile-voice-development-workflow.md`.
- **Privacy / owner-wall consideration:**
  - Cloud STT (Google, OpenAI) sends raw audio to a third party →
    spending + data-handling decision → owner-gated.
  - Android's offline `SpeechRecognizer` (API 31+) keeps audio
    on-device but requires `RECORD_AUDIO` permission — an
    `AndroidManifest.xml` change classified RC3 by
    `skills/aos-enterprise-council/rules/android-mobile-and-release-surface.md`
    L40–43.
- **Gap:** No voice scaffold. Smallest safe v0: **no microphone
  permission**, defer to keyboard-only input + the existing
  Termux / Slack voice paths. Voice in-app lands in a later wave
  with an explicit permission justification.

### 9. Release signing (missing)

- **Finding:** No keystore, no `signingConfigs` block, no
  `release.keystore.properties`, no `gradlew` wrapper. There is
  nothing to sign because there is nothing to build.
- **Owner-wall consideration:** `gradlew bundleRelease` for upload
  and any keystore generation is **owner-only** per
  `skills/aos-enterprise-council/rules/android-mobile-and-release-surface.md`
  L30–33 and the recovered hazmat-command skill at
  `recovered-agent-sources/from-hazmat-command/docs/skills/mobile-capacitor-release-check.md`
  L54–56.
- **Gap:** Keystore custody plan. Recommended: owner generates the
  keystore offline, stores it in a password manager + offline
  backup, never commits it. CI builds **debug-only**; release
  signing happens on the owner's machine. No `release.keystore`
  ever in git. No `.keystore` ever in CI secrets unless the owner
  explicitly opts in (separate decision).

### 10. Cleartext / HTTPS risk

- **Finding:** This is the single highest-risk topic that has to be
  decided before any Kotlin lands.
- **Current state of the server:**
  - `hermes_cli/web_server.py:4583` runs `uvicorn` over **plain HTTP**
    unless fronted by a reverse proxy. There is no built-in TLS.
  - CORS in `web_server.py:102–107` allow-lists `http://` origins.
  - The session token is sent on the WS upgrade as a query param
    (`web/src/lib/gatewayClient.ts`) — over `ws://` that is a
    plaintext credential on the wire.
- **Android baseline (API 28+):** cleartext traffic is **blocked by
  default**. To talk to `http://<lan-ip>:<port>` the app would need
  a `networkSecurityConfig` carve-out *or* a debug-build-only
  override. Putting a cleartext carve-out in a release build is a
  Play Store red flag and a security regression.
- **Three viable paths, owner picks one:**
  1. **Loopback-only via Termux** — phone runs Hermes locally;
     the app talks to `http://127.0.0.1:<port>`. Cleartext is
     acceptable on loopback. No LAN exposure.
  2. **LAN with self-signed TLS** — Hermes terminates TLS itself
     (new feature, not present today); app pins the cert. Requires
     server-side change + cert management runbook. Out of scope
     for W10 audit; flag for a later wave.
  3. **LAN cleartext, debug builds only** — app ships a
     `networkSecurityConfig` that allows cleartext to RFC1918
     addresses **only in `debug`**; release flavor disallows
     cleartext. Acceptable for owner-internal use, **not Play
     Store launch-ready**.
- **Gap & recommendation:** Default v0 to path 1 (Termux loopback).
  Treat path 2 as the Play-Store-ready end state. Path 3 is a
  development convenience that must never leak into release.

### 11. Play Store readiness blockers

The following are required before a Play Store submission. **None
exist today.** Submission itself is owner-only per
`skills/aos-enterprise-council/rules/android-mobile-and-release-surface.md`
L30–33; this list is the readiness work that precedes the owner's
button-press.

| # | Blocker | Status | Owner-gated? |
|---|---|---|---|
| 1 | Package id chosen and reserved (e.g. `com.echerd27.hermes`) | NOT CHOSEN | Yes (id is forever) |
| 2 | App name + tagline + short / full description | NOT WRITTEN | Yes (public-facing copy) |
| 3 | Icons: 48–512 px raster + 1024 maskable + adaptive foreground/background | NOT CREATED | Yes (brand) |
| 4 | Feature graphic 1024×500 | NOT CREATED | Yes (brand) |
| 5 | Phone + tablet screenshots (≥ 2 each) of a real working build | NOT POSSIBLE (no build) | — |
| 6 | Privacy policy URL on an owner-controlled domain | NOT PUBLISHED | Yes (DNS / hosting) |
| 7 | Data-safety form: what the app collects, where it sends it | NOT FILLED | Yes (legal) |
| 8 | Content-rating questionnaire | NOT FILLED | Yes |
| 9 | Target API level meets Play's current floor (35 as of 2026) | N/A — no build | — |
| 10 | Permission justifications (every `<uses-permission>` mapped to a feature) | N/A — manifest does not exist | — |
| 11 | Release-signed AAB (`bundleRelease`) produced and tested | NOT POSSIBLE (no keystore) | **Yes — owner-only** |
| 12 | Play Console account, billing, developer-program agreement | UNKNOWN | **Yes — owner-only** |
| 13 | Internal testing track set up, ≥ 1 internal tester invited | N/A | Yes |
| 14 | Crash-reporting and ANR triage path (Crashlytics, Sentry, or none) | NOT CHOSEN | Yes (data egress decision) |
| 15 | `PLAY_STORE.md` / `PUBLISH.md` runbook committed | NOT WRITTEN | No (agent can draft once 1–4 are decided) |
| 16 | `docs/releases/v0.0.1-android.md` release note | NOT WRITTEN | No (agent can draft post-build) |

---

## Smallest safe PR plan

Each PR is bounded, documentation-only or non-Kotlin, and stops
short of every owner wall. Each is a *separate* wave; this audit
recommends them in order but does not authorize them.

### W11 — Owner decisions captured (docs only)

- **Branch:** `aci/wave-11-android-owner-decisions`
- **Allowed files:**
  - `docs/aci/decisions/W11_ANDROID_OWNER_DECISIONS.md` (new)
- **Content:** A single decision-record file that the owner fills
  in: package id, gateway topology choice (loopback / LAN-TLS /
  LAN-cleartext-debug-only), keystore custody, crash-reporter
  choice (or "none"), Firebase yes/no, voice-input yes/no,
  privacy-policy URL plan.
- **Owner-gated:** Drafting allowed; merging requires the owner to
  fill in the blanks.
- **Validation:** `git diff --stat` shows only the one new file.

### W12 — Repository scaffold paths (docs + empty placeholder)

- **Branch:** `aci/wave-12-android-scaffold-paths`
- **Allowed files:**
  - `PLAY_STORE.md` (skeleton playbook only; no submission steps)
  - `PUBLISH.md` (skeleton; references the owner-only wall in
    `skills/aos-enterprise-council/rules/android-mobile-and-release-surface.md`)
  - `docs/releases/.gitkeep`
  - `apps/.gitkeep`
- **Explicitly NOT touched:** any `*.kt`, `*.kts`, Gradle file,
  `AndroidManifest.xml`, `capacitor.config.json`.
- **Owner-gated:** No, these are docs / empty dirs.
- **Validation:** `find apps -type f` returns only `.gitkeep`.

### W13 — Android module scaffold (first Kotlin)

- **Branch:** `aci/wave-13-android-module-scaffold`
- **Pre-requisite:** W11 decisions merged.
- **Allowed files (proposed; not committed by this wave):**
  - `apps/android/build.gradle.kts`
  - `apps/android/settings.gradle.kts`
  - `apps/android/gradle/wrapper/*`
  - `apps/android/app/build.gradle.kts`
  - `apps/android/app/src/main/AndroidManifest.xml` (zero
    permissions; INTERNET only if v0 needs network)
  - `apps/android/app/src/main/java/<package>/MainActivity.kt`
    (single empty Compose screen, no network yet)
  - `apps/android/app/src/main/res/values/{strings,themes,colors}.xml`
  - `apps/android/app/src/debug/res/xml/network_security_config.xml`
    (debug-only cleartext to RFC1918 if path 3 chosen)
- **Forbidden in this wave:**
  - Any release-signing config.
  - Any FCM dependency.
  - Any microphone permission.
  - Any production cleartext exemption.
- **Validation:**
  - `./gradlew :app:assembleDebug` builds.
  - `./gradlew :app:lintDebug` passes.
  - `apkanalyzer` confirms zero non-INTERNET permissions in the
    debug APK.

### W14 — Gateway client + connection screen

- **Branch:** `aci/wave-14-android-gateway-client`
- **Allowed files:**
  - `apps/android/app/src/main/java/<package>/net/GatewayClient.kt`
    (mirrors `web/src/lib/gatewayClient.ts`)
  - `apps/android/app/src/main/java/<package>/net/AuthInterceptor.kt`
    (adds `X-Hermes-Session-Token` to every REST call)
  - `apps/android/app/src/main/java/<package>/data/TokenStore.kt`
    (uses `EncryptedSharedPreferences`)
  - `apps/android/app/src/main/java/<package>/ui/ConnectionScreen.kt`
    (gateway URL field + paste-token field + connect button)
  - Unit tests for `GatewayClient`, `TokenStore`, and the JSON-RPC
    framer.

### W15 — Chat surface (read-only)

- **Branch:** `aci/wave-15-android-chat-readonly`
- Adds a transcript view that subscribes to gateway events; no
  composer yet. Validates against a recorded mock session under
  `apps/android/app/src/main/assets/mock/`.

### W16 — Composer + skill picker

- **Branch:** `aci/wave-16-android-composer-and-skills`
- Adds the slash skill picker (mirrors
  `web/src/components/SlashPopover.tsx`).

### W17 — Voice input decision

- Owner-gated. Only proceeds if W11 decided "yes." Adds
  `RECORD_AUDIO` permission with a justification block in the PR
  body. Cited explicitly to satisfy
  `skills/aos-enterprise-council/rules/android-mobile-and-release-surface.md`
  L40–43.

### W18 — Push notifications decision

- Owner-gated. FCM only if W11 decided "yes." Otherwise this wave
  is "explicitly NOT shipping push; document why."

### W19 — Pre-launch hardening

- Lint, Detekt, ktlint, dependency-vulnerability scan, leak-canary
  in debug, BuildConfig.MOCK_MODE assertion that release builds
  reject mock fixtures.

### W20 — Owner-only Play Store submission

- Documentation-only from agents. Submission itself is the owner's
  hands per `skills/aos-enterprise-council/rules/android-mobile-and-release-surface.md`
  L30–33.

---

## Owner walls preserved by this audit

This report and the proposed waves do **not** cross any of the
following walls:

- No Play Store / App Store submission.
  (`skills/aos-enterprise-council/rules/android-mobile-and-release-surface.md`
  L30–33).
- No `gradlew bundleRelease` for upload, no Play Console
  interaction, no App Store Connect interaction.
- No `vercel --prod`, no DNS change at IONOS or Cloudflare, no
  Base44 publish.
- No `AndroidManifest.xml` permission additions in this wave
  (none can be added — no manifest exists).
- No production credential creation (no Firebase project, no
  keystore, no signing key).
- No spending decisions (no paid SDK, no paid Play Console fee
  triggered).
- No DNS / hosting decisions.
- No secrets in code, logs, docs, tests, fixtures, or
  screenshots — this report contains zero tokens, zero URLs to
  owner infrastructure, and zero private package ids.

---

## Blockers & risks

| # | Blocker / risk | Severity | Resolution path |
|---|---|---|---|
| B1 | Package id is forever; not yet chosen | High | W11 decision record |
| B2 | Gateway topology not chosen (loopback vs. LAN-TLS vs. LAN-cleartext) | High | W11 decision record |
| B3 | Server has no built-in TLS; LAN deployment exposes session token on wire | High | Either pick loopback, or schedule a separate "Hermes TLS termination" wave |
| B4 | CORS + anti-DNS-rebinding currently blocks Android over LAN | Medium | Server-side gated allow-list extension, in a separate wave with owner sign-off |
| B5 | Keystore custody not defined | High | W11 decision record; owner generates offline, never in CI without separate decision |
| B6 | Privacy policy URL not yet published | High (Play blocker) | W11 owner decision + hosting wave |
| B7 | Data-safety form unanswered (depends on FCM / crash-reporter / voice choices) | High (Play blocker) | Decided as W11 yes/no flags resolve |
| B8 | Mock mode not yet defined; risk of mock fixtures leaking into release | Medium | W19 hardening wave adds release-build assertion |
| B9 | Voice / mic permission is RC3 (rule L40–43); cannot be added casually | Medium | W17 is gated on W11 |
| B10 | No release notes process for Android (`docs/releases/**` not present) | Low | W12 scaffold creates `docs/releases/.gitkeep` |

---

## Execution checklist (W10 deliverable)

This is the checklist a future operator can hand to the owner.

- [ ] Owner reads this report end-to-end.
- [ ] Owner answers the open questions in section below.
- [ ] W11 decision PR opened with owner answers committed.
- [ ] W12 scaffold-paths PR opened (docs + empty dirs).
- [ ] W13 Android module scaffold PR opened (first Kotlin, debug-only build).
- [ ] W14 gateway client + connection screen PR opened.
- [ ] W15 chat read-only PR opened.
- [ ] W16 composer + skill picker PR opened.
- [ ] W17 voice decision wave (only if W11 said yes).
- [ ] W18 push decision wave (only if W11 said yes).
- [ ] W19 pre-launch hardening PR opened.
- [ ] Owner runs `gradlew bundleRelease` locally with the offline
      keystore.
- [ ] Owner manually files Play Console submission.
- [ ] `docs/releases/v0.0.1-android.md` written *after* the
      submission, citing the merged SHA and the build's test count.

---

## Validation commands (for this wave only)

```bash
# Confirm the audit touched only the allowed path.
git diff --stat main...aci/wave-10-android-launch-audit

# Expected output: exactly one file changed —
#   docs/aci/reports/W10_ANDROID_LAUNCH_AUDIT.md

# Confirm no source files were modified.
git diff --name-only main...aci/wave-10-android-launch-audit \
  | grep -E '\.(kt|kts|gradle|xml|py|ts|tsx|js|jsx)$' \
  && echo "FAIL: source files in diff" \
  || echo "OK: no source files in diff"

# Confirm forbidden paths are untouched.
git diff --name-only main...aci/wave-10-android-launch-audit \
  | grep -E '^(apps/android/|README\.md$|pyproject\.toml$|uv\.lock$)' \
  && echo "FAIL: forbidden path in diff" \
  || echo "OK: forbidden paths clean"
```

---

## Rollback

```bash
git rm docs/aci/reports/W10_ANDROID_LAUNCH_AUDIT.md
# (optionally) rmdir docs/aci/reports docs/aci
git commit -m "rollback: remove W10 audit report"
```

The directories `docs/aci/` and `docs/aci/reports/` were created by
this wave; remove them only if no other waves have committed files
underneath.

---

## Open questions for the owner (blocking W11)

1. **Package id** — `com.echerd27.hermes`? Something else? It is
   permanent on Play.
2. **Gateway topology for v0** — loopback-via-Termux, LAN-with-TLS
   (requires Hermes TLS work), or LAN-cleartext-debug-only?
3. **Keystore custody** — offline-only on owner machine, or also a
   CI-secret for debug builds?
4. **Crash reporter** — none, Sentry, Crashlytics?
5. **Push notifications** — defer entirely for v0, or set up FCM?
6. **Voice input** — defer to Termux/Slack, or in-app mic with
   `RECORD_AUDIO` permission?
7. **Privacy policy URL** — which owner-controlled domain will host
   it?
8. **Play Console account** — already exists, or is account
   creation + developer-program fee part of this rollout?

---

## Wave report

- **Changed files:** `docs/aci/reports/W10_ANDROID_LAUNCH_AUDIT.md`
  (one new file). Two new directories created en route
  (`docs/aci/`, `docs/aci/reports/`).
- **Tests run:** None. This wave is documentation only; no code
  changed and no test surface exists to exercise. Test-skip
  justification: ALLOWED FILES contains a single Markdown file;
  there is nothing executable to verify.
- **Remaining risks:** All ten in the *Blockers & risks* table
  above. The largest are B1 (package id is forever), B3 (no
  server-side TLS), and B5 (keystore custody undefined). None are
  introduced by this PR; all pre-date it and block W11+.
- **Rollback plan:** Delete the single file (commands above).
- **PR summary:** Documentation-only audit. Establishes that
  `apps/android/` does not exist, inventories every dependency the
  eventual Android client would have on the current gateway,
  enumerates the eleven launch topics requested in the W10 mission
  with concrete file-path references, and proposes a ten-wave
  sequence (W11–W20) that stays inside every owner wall in
  `AGENTS.md` and
  `skills/aos-enterprise-council/rules/android-mobile-and-release-surface.md`.
  No source changes. No store interactions. No secrets.

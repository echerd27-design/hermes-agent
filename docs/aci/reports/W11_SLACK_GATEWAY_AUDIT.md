# Wave 11 — Slack Gateway Audit

**Branch:** `aci/wave-11-slack-gateway-audit`
**Scope:** read-only audit of Slack support in `gateway/` and adjacent
CLI/docs. **No code changed.**
**Audience:** the operator (mobile-first, Android/Termux) and the next
wiring/fix wave.

---

## 1. Executive summary

- Slack support in Hermes is **implemented, not stubbed**. A 3,027-line
  Socket Mode adapter lives at `gateway/platforms/slack.py` with
  multi-workspace clients, Block Kit rendering, threading, reactions,
  media uploads with retry, exec-approval buttons, and ephemeral slash
  responses.
- Slack deps (`slack-bolt`, `slack-sdk`, `aiohttp`) are pinned in
  `pyproject.toml` and lazy-installed at first adapter start via
  `tools.lazy_deps.ensure("platform.slack")`. The `[termux]` extra
  does **not** preinstall them — Slack costs zero install time until
  the operator actually wires a token.
- Tests exist: five `tests/gateway/test_slack*.py` + `tests/hermes_cli/`
  files covering mention behaviour, channel-skill bindings, approval
  buttons, and the manifest CLI.
- The full Slack app manifest can be generated on-device with
  `hermes slack manifest --write` (writes to
  `$HERMES_HOME/slack-manifest.json`). Slash commands come from
  `COMMAND_REGISTRY` in `hermes_cli/commands.py` — a single source of
  truth shared with every other gateway.
- **The wiring gaps are operator-facing, not code-level:** `.env.example`
  documents 3 of ~10 Slack env vars, there is no consolidated mobile
  setup doc, and there is no `/health` endpoint for orchestrated
  deploys.
- **Recommended next-wave scope:** add the missing env vars to
  `.env.example` and ship a `docs/user-guide/messaging/slack.md`
  operator guide that lifts §9 + §10 of this report. Code changes are
  optional and clearly out-of-scope for the minimum wiring wave.

---

## 2. Current Slack support — what exists today

| File | Role |
| --- | --- |
| `gateway/platforms/slack.py` (3,027 lines) | `SlackAdapter`: Socket Mode (`slack_bolt.AsyncApp` + `AsyncSocketModeHandler`), multi-workspace `_team_clients` map, `MessageDeduplicator` for reconnect replays, thread-context cache, assistant-thread metadata cache, Block Kit rendering, reactions (eyes / white_check_mark / x), image/audio/video/document upload with 3-attempt retry, `send_exec_approval` (Block Kit approval buttons), `send_slash_confirm`, `send_private_notice`, ephemeral slash responses via `response_url`. |
| `gateway/platforms/base.py` | `BasePlatformAdapter`, `MessageEvent`, `MessageType`, `SendResult`, `ProcessingOutcome`, `SUPPORTED_DOCUMENT_TYPES`, proxy helpers (`resolve_proxy_url`, `is_host_excluded_by_no_proxy`, `safe_url_for_log`), `cache_document_from_bytes` — all inherited by `SlackAdapter`. |
| `gateway/platforms/helpers.py` | `MessageDeduplicator` used by Slack to drop Socket Mode replay events. |
| `gateway/config.py` | `Platform.SLACK` enum + `PlatformConfig` fields: `require_mention`, `strict_mention`, `allow_bots`, `free_response_channels`, `reactions`, `allowed_channels`, `home`, `reply_in_thread`. |
| `gateway/session.py` | `SessionSource` — the unifying messaging-surface contract: `platform`, `chat_id`, `user_id`, `thread_id`, `guild_id`, `parent_chat_id`, `chat_type`. Slack populates all of these. |
| `gateway/run.py` | Gateway entrypoint (`gateway run`). Applies secret-redaction patterns for `xoxb-` and `xapp-` tokens in logs. |
| `hermes_cli/slack_cli.py` (159 lines) | `hermes slack manifest` — emits the full Slack app manifest JSON: display info, OAuth scopes, bot events, Socket Mode, interactivity, and slash commands sourced from `COMMAND_REGISTRY`. Supports `--write`, `--name`, `--description`, `--slashes-only`. |
| `hermes_cli/commands.py` | `COMMAND_REGISTRY` + `slack_app_manifest()` — single source of truth; every CLI command surfaces as a Slack slash command. |
| `cli.py` (line 7773) | `Platform.SLACK: ("Slack", "SLACK_BOT_TOKEN")` startup mapping. |
| `pyproject.toml` (lines 84/86) | `slack = ["slack-bolt==1.27.0", "slack-sdk==3.40.1", "aiohttp==3.13.3"]` (also folded into the `messaging` extra). Lazy-installed at first use. |
| `tests/gateway/test_slack.py` | Core adapter behaviour. |
| `tests/gateway/test_slack_mention.py` | Mention-requirement edge cases. |
| `tests/gateway/test_slack_channel_skills.py` | Per-channel skill bindings. |
| `tests/gateway/test_slack_approval_buttons.py` | Block Kit approval-button flow. |
| `tests/hermes_cli/test_slack_cli.py` | Manifest CLI. |
| `docs/slack-mobile-command-policy.md` | Operator-facing JARVIS command pattern policy (`JARVIS <verb>: <payload>`). |
| `docs/mobile-voice-development-workflow.md` | Adjacent mobile workflow doc. |
| `SETUP.md` | Termux / Android baseline install path (cites `[termux]` extra). |
| `setup-hermes.sh` (lines 213, 217) | `slack` listed among tolerated lazy extras. |
| `constraints-termux.txt` | Termux dependency constraints. |

---

## 3. Required environment variables

### 3a. Documented in `.env.example` today (3 vars)

| Var | Value | Purpose |
| --- | --- | --- |
| `SLACK_BOT_TOKEN` | `xoxb-…` | Bot OAuth token (required). Accepts comma-separated values for multi-workspace. |
| `SLACK_APP_TOKEN` | `xapp-…` | App-level token (required for Socket Mode). |
| `SLACK_ALLOWED_USERS` | CSV of `Uxxxxxxx` | Users permitted to act on approval/confirmation buttons. |

### 3b. Read by the adapter but **not** in `.env.example` (gap)

| Var | Default | Purpose |
| --- | --- | --- |
| `SLACK_ALLOW_BOTS` | `none` | `none` / `mentions` / `all` — filter for bot-authored messages. |
| `SLACK_REQUIRE_MENTION` | `true` | Require `@Hermes` to trigger in channels. |
| `SLACK_STRICT_MENTION` | `false` | Strict exact-mention match. |
| `SLACK_FREE_RESPONSE_CHANNELS` | empty | CSV of channel IDs that bypass mention-requirement. |
| `SLACK_ALLOWED_CHANNELS` | empty | CSV channel allow-list. |
| `SLACK_REACTIONS` | (per-config) | Toggle eyes/check reaction lifecycle. |
| `SLACK_CHANNEL_SKILL_BINDINGS` | empty | Per-channel skill map (JSON/CSV form per adapter). |
| `HERMES_HOME` | `~/.hermes` | Consumed by `hermes slack manifest --write` for output path. |

These exist in code (see `gateway/platforms/slack.py` and
`gateway/config.py`) but operators have no example to copy from. The
wiring wave should append them to `.env.example` (see §11).

---

## 4. Event / subscription model

- **Transport:** Socket Mode (WebSocket). No public ingress, no
  webhook endpoint, no HMAC verification path. Replay protection is
  handled in-process by `MessageDeduplicator`.
- **Subscribed bot events** (manifest, `hermes_cli/slack_cli.py` lines
  87–94):
  - `app_mention`
  - `assistant_thread_context_changed`
  - `assistant_thread_started`
  - `message.channels`
  - `message.groups`
  - `message.im`
- **OAuth bot scopes** (manifest, lines 67–82):
  `app_mentions:read`, `assistant:write`, `channels:history`,
  `channels:read`, `chat:write`, `commands`, `files:read`,
  `files:write`, `groups:history`, `groups:read`, `im:history`,
  `im:read`, `im:write`, `users:read`.
- **Manifest settings:** `socket_mode_enabled: true`,
  `interactivity.is_enabled: true`, `token_rotation_enabled: false`,
  `org_deploy_enabled: false`.
- **Inbound path:**
  `AsyncSocketModeHandler` →
  `SlackAdapter._handle_slack_message` →
  dedup check (`_dedup.is_duplicate(event_ts)`) →
  bot / mention / channel filters →
  Block Kit text extraction (`_extract_text_from_slack_blocks`) →
  thread-context fetch (`_fetch_thread_context`) →
  build `SessionSource` →
  `AIAgent.run_conversation` (sync; the gateway bridges async↔sync).
- **Outbound path:** `SlackAdapter.send` (text + Block Kit),
  `send_image`, `send_voice`, `send_video`, `send_document`,
  `send_exec_approval`, `send_slash_confirm`, `send_private_notice`,
  `edit_message`. Reactions added/removed via `_add_reaction` /
  `_remove_reaction`.

---

## 5. Command handling

- **Single source of truth:** `COMMAND_REGISTRY` in
  `hermes_cli/commands.py`. `slack_app_manifest()` reads it and the
  manifest CLI emits one Slack slash command per entry — so adding a
  new CLI command propagates to Slack on the next manifest
  regenerate-and-paste.
- **`gateway_only=True` commands** (`topic`, `approve`, `deny`,
  `sethome`) appear in Slack but not in CLI help.
- **In-thread `!cmd …`** is rewritten to `/cmd …` by the adapter
  (`_handle_slack_message` lines ~1809–1819) so operators can use
  commands inside threads without Slack's slash-command UI.
- **Command authorization** today: governed at command-implementation
  level, not at the adapter. `SLACK_ALLOWED_USERS` is enforced only on
  approval/confirmation Block Kit buttons (see §8).

---

## 6. Slash command support

- **Generation:**
  `hermes slack manifest [--write] [--name NAME] [--description DESC] [--slashes-only]`
  (see `hermes_cli/slack_cli.py`).
- **Output:** stdout JSON, or `$HERMES_HOME/slack-manifest.json` when
  `--write` is passed with no arg.
- **Install workflow:** generate manifest → Slack app config (Features
  → App Manifest → Edit) → paste → Save → Slack diffs and prompts to
  reinstall if scopes or commands changed.
- **Ephemeral responses:** when a slash command triggers a reply,
  `SlackAdapter.send` matches the invoker via the `_slash_user_id`
  ContextVar (declared near line 61) and posts ephemeral output via
  the stashed `response_url`. Multiple users issuing slash commands
  on the same channel concurrently are correctly disambiguated
  because ContextVars propagate to child asyncio tasks.

---

## 7. DM handling

- Subscribed via the `message.im` event + `im:history` / `im:read` /
  `im:write` scopes.
- DM detection: `chat_type="dm"` set on the `SessionSource`. Mention
  requirement is bypassed for DMs. The session key is derived from
  the DM channel id so multi-turn DM context persists.
- `send_private_notice` sends DM-style notices independent of the
  originating channel — used for out-of-band notifications (e.g. "I
  finished the long-running task you started in #foo").
- Assistant-thread metadata (`_assistant_thread_*`) is cached so DM
  context survives Socket Mode reconnects.

---

## 8. Security risks

Ratings: **L / M / H** = low / medium / high. File refs are
approximate where line numbers may drift.

| Sev | Finding | Reference |
| --- | --- | --- |
| **M** | Env-var documentation gap. `.env.example` lists 3 of ~10 Slack env vars. Operators run with surprising defaults (`SLACK_ALLOW_BOTS=none`, `SLACK_REQUIRE_MENTION=true`, empty `SLACK_ALLOWED_CHANNELS`) without seeing them. Fix is documentation-only. | `.env.example` ~lines 326–332 vs `gateway/platforms/slack.py` env reads |
| **M** | `SLACK_ALLOWED_USERS` is enforced only on approval/confirm Block Kit buttons (`_handle_slash_confirm_action`, slack.py ~line 2399), not on general slash commands or messages. Operators may assume it gates all command access. Documenting this clearly is the minimum fix; a separate `SLACK_ALLOWED_COMMAND_USERS` env var is an optional code change. | `gateway/platforms/slack.py` ~2399 |
| **L** | No HTTP `/health` endpoint. `gateway run` does not expose Socket Mode connection status externally. Acceptable for Termux foreground use; flag for container/orchestrated deploys. | `gateway/run.py` |
| **L** | Client-side rate-limit posture: media uploads retry 3× with backoff but there is no token-bucket; Slack 429s surface as errors. Fine for the single-operator mobile use case. | `gateway/platforms/slack.py` `send_video` / `send_document` retry blocks |
| **L** | Slack Connect file objects arrive as stubs and require a `files.info` round-trip before download. Already handled in the adapter; documented here for awareness. | `gateway/platforms/slack.py` ~lines 2027–2178 |
| **L** | 100 KB document text-injection threshold and 20 MB upload ceiling are constants, not configurable env vars. Acceptable for mobile use; flag for enterprise. | `gateway/platforms/slack.py` `MAX_DOC_BYTES` |
| **None** | Webhook signing / HMAC: **not applicable.** Socket Mode is the transport. | n/a |
| **OK** | Secret redaction for `xoxb-` and `xapp-` tokens in gateway logs. | `gateway/run.py` redaction patterns |

**Logs and fixtures:** no Slack tokens or workspace IDs appear in any
test fixture, log, or doc that this audit touched. The wiring wave
should hold the same line — keep example tokens as placeholders
(`xoxb-…`, `xapp-…`, `Uxxxxxxx`).

---

## 9. Mobile-first (Android / Termux) setup path

Numbered checklist the operator can run end-to-end from a phone:

1. **Termux:** install from a trusted source; `pkg install python git`.
2. **Clone + install:**
   ```
   git clone https://github.com/echerd27-design/hermes-agent.git
   cd hermes-agent
   uv pip install -e ".[termux]"
   ```
   Use the `[termux]` extra **before** `[all]` per `SETUP.md` lines 48
   and 108 — desktop/voice extras may not build under Termux. Slack
   deps lazy-install on first adapter start.
3. **Create the Slack app:** open `https://api.slack.com/apps` →
   *Create New App* → *From an app manifest*. Select your workspace.
4. **Generate the manifest on the phone:**
   ```
   hermes slack manifest --write
   ```
   The file is written to `$HERMES_HOME/slack-manifest.json` (defaults
   to `~/.hermes/slack-manifest.json`). The CLI prints follow-up
   instructions on stderr.
5. **Paste the manifest** into the Slack app's *Features → App
   Manifest → Edit* form. Save. Slack will prompt to install/reinstall
   to the workspace.
6. **Enable Socket Mode + generate the app token:** Slack app config →
   *Basic Information → App-Level Tokens → Generate Token and Scopes*
   → scope `connections:write`. Copy the `xapp-…` token.
7. **Copy the bot token:** Slack app config → *OAuth & Permissions* →
   copy the `xoxb-…` Bot User OAuth Token.
8. **Write `~/.hermes/.env`** (or `$HERMES_HOME/.env`):
   ```
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_APP_TOKEN=xapp-...
   SLACK_ALLOWED_USERS=Uxxxxxxx   # your own Slack user ID
   ```
   Optionally also set `SLACK_REQUIRE_MENTION=true` (the default) and
   `SLACK_ALLOW_BOTS=none` (the default) explicitly so they show up
   in `env`.
9. **Run the gateway** in Termux session A:
   ```
   gateway run
   ```
   Watch for the `slack` adapter starting and a Socket Mode
   `connected` event.
10. **Verify from Slack mobile app:**
    - DM the bot: `ping` → expect a reply.
    - In a channel where the bot is invited: `@Hermes hi` → reply
      threaded.
    - `/btw` or `/topic mobile-test` → confirms slash routing.
    - Trigger an approval-requiring tool → confirm the Block Kit
      buttons render and that only `SLACK_ALLOWED_USERS` members can
      act on them.

**Reference docs (do not edit):** `SETUP.md` (Android/Termux
baseline), `docs/slack-mobile-command-policy.md` (JARVIS command
pattern), `docs/mobile-voice-development-workflow.md`,
`constraints-termux.txt`, `setup-hermes.sh` lines 213/217.

---

## 10. Smoke tests

### In Termux

```
# Resolve Slack extras without installing (dry run).
uv pip install -e ".[slack]" --dry-run

# Generate the manifest to $HERMES_HOME/slack-manifest.json.
hermes slack manifest --write

# Run the Slack-specific test suite.
pytest tests/gateway/test_slack.py \
       tests/gateway/test_slack_mention.py \
       tests/gateway/test_slack_channel_skills.py \
       tests/gateway/test_slack_approval_buttons.py \
       tests/hermes_cli/test_slack_cli.py -q

# Start the gateway in the foreground.
gateway run
```

### In the Slack workspace

- DM the bot `ping` → expect a reply.
- DM the bot `/help` → expect a slash command listing.
- In a channel: `@Hermes status` → reply in thread.
- In a channel: `/topic mobile-test` → confirms `gateway_only` slash
  routing.
- Trigger an approval-requiring tool → confirm Block Kit buttons
  render and only `SLACK_ALLOWED_USERS` members can click them.
- React to a bot reply with `:eyes:` → confirm reaction lifecycle is
  not broken.

---

## 11. Exact files a future wiring/fix wave should edit

Listed by priority. The audit only **names** these files — the next
wave's prompt owns the actual edits.

### Required (minimum wiring wave)

1. `.env.example` — append the 7 missing `SLACK_*` env vars from §3b
   with comments mirroring the existing 3 entries. Pure documentation
   change.
2. `docs/user-guide/messaging/slack.md` *(new file)* — operator setup
   guide that lifts §9 (Android/Termux path) and §10 (smoke tests)
   from this report into a product-doc location.

### Optional (only if scope is explicitly broadened)

3. `gateway/run.py` — add a `/health` endpoint returning Socket Mode
   connection state. Closes §8 L #1.
4. `gateway/platforms/slack.py` — introduce
   `SLACK_ALLOWED_COMMAND_USERS` (or rename) to close the
   authorization-scope gap in §8 M #2. Touches a forbidden directory
   for the audit wave; must be its own gated wave with tests.

### Out of scope for the wiring wave (do not touch)

- `gateway/platforms/base.py`, `gateway/platforms/helpers.py`,
  `gateway/config.py`, `gateway/session.py`,
  `hermes_cli/slack_cli.py`, `hermes_cli/commands.py`, `cli.py`,
  `pyproject.toml`, `uv.lock`, `README.md`, `Dockerfile`,
  `docker-compose.yml`.
- `docs/aci/reports/W11_SLACK_GATEWAY_AUDIT.md` — this report;
  finalised by this wave.

---

## 12. Wave close-out

- **Changed files:** `docs/aci/reports/W11_SLACK_GATEWAY_AUDIT.md`
  (single file, additive).
- **Tests run:** none. Reason: audit is documentation only; the task
  explicitly forbids `gateway/**`, `hermes_cli/**`, `apps/android/**`,
  `pyproject.toml`, `uv.lock`, and `README.md`. The smoke-test
  commands in §10 are listed for the operator and the next wave to
  run.
- **Remaining risks:** the M/L items in §8 (env-var doc gap,
  authorization-scope gap, missing `/health`, no client-side rate
  limit, file-size constants). All are documentation-actionable
  except the last two, which are scope decisions for later waves.
- **Rollback plan:** `git rm docs/aci/reports/W11_SLACK_GATEWAY_AUDIT.md`
  (or delete pre-commit). Single-file audit; nothing else to undo.
- **PR summary (draft):** *Wave 11 — Slack gateway audit. Documents
  what already exists (Socket Mode adapter, lazy deps, manifest CLI,
  five test files), enumerates required env vars, lists the
  event/scope/slash/DM model, rates security risks, gives an
  Android/Termux setup checklist and smoke tests, and names the exact
  files the next wiring wave should touch. No code changed.*

# Wave 11 — Termux Install & Doctor Audit (ACI Hermes)

**Branch:** `aci/wave-11-termux-doctor-audit`
**Wave type:** Audit (read-only)
**Date:** 2026-05-26
**Author role:** /builder

## Non-overlap contract (recap from universal header)

- Wave branch only: `aci/wave-11-termux-doctor-audit`. Never merge to
  main. Open a draft PR only.
- This wave touches exactly one file:
  `docs/aci/reports/W11_TERMUX_DOCTOR_AUDIT.md`.
- Forbidden in this wave: `scripts/**`, `hermes_cli/**`,
  `apps/android/**`, `pyproject.toml`, `uv.lock`, `README.md`, GitHub
  workflows, package files, Gradle files, and every other wave's files.
- No publishing, deploying, DNS changes, secret rotation, money spend,
  or app store submission.
- No secrets in code, logs, docs, tests, fixtures, or screenshots —
  every token shape below is a placeholder (`xoxb-...`, `xapp-...`,
  `sk-...`).
- Mission: inspect install scripts, docs, and Termux extras; report
  findings; ship nothing else.

## 1. Current Termux install path

There are two documented paths today. They are not identical, which is
the first thing the next wave needs to reconcile.

### 1a. Official one-liner (`scripts/install.sh`)

```bash
# from a fresh Termux shell
pkg update && pkg upgrade -y
pkg install -y curl git
curl -fsSL https://raw.githubusercontent.com/echerd27-design/hermes-agent/main/scripts/install.sh | bash
```

Termux behaviour inside the script:

- `is_termux()` detection by `$TERMUX_VERSION` or `$PREFIX` containing
  `com.termux/files/usr` (`scripts/install.sh:229-231`).
- Skips uv entirely on Termux — uses stdlib `python -m venv` + `pip`
  (`scripts/install.sh:358-362, 441-458`).
- `INSTALL_DIR` resolves to `$HERMES_HOME/hermes-agent`, i.e.
  `~/.hermes/hermes-agent` (`scripts/install.sh:253-256`).
- `hermes` command symlinked into `$PREFIX/bin` (already on PATH in
  Termux) via `get_command_link_dir()`
  (`scripts/install.sh:282-289, 1260-1303`).
- Auto-installs build toolchain with
  `pkg install -y clang rust make pkg-config libffi openssl
  ca-certificates curl` plus optional `ripgrep` / `ffmpeg`
  (`scripts/install.sh:733-746`).
- Pre-builds psutil from the Android-patched shim before the main
  install (`scripts/install.sh:1043-1049` → `scripts/install_psutil_android.py`).
- Three-tier pip fallback, all with `-c constraints-termux.txt`
  (`scripts/install.sh:1053-1064`):
  1. `python -m pip install -e '.[termux-all]' -c constraints-termux.txt`
  2. `python -m pip install -e '.[termux]' -c constraints-termux.txt`
  3. `python -m pip install -e '.' -c constraints-termux.txt`
- Sets `ANDROID_API_LEVEL` from `getprop ro.build.version.sdk`, defaults
  to 24, exports it before pip (`scripts/install.sh:1027-1034`).

Non-interactive guard: `IS_INTERACTIVE` is auto-detected on stdin
(`scripts/install.sh:80-84`). If launched via `curl | bash`, prompts
fall back to `/dev/tty` reads (`scripts/install.sh:206-211`).

### 1b. Manual path from `SETUP.md`

```bash
pkg update && pkg upgrade
pkg install -y git python ripgrep clang libffi openssl rust
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.profile 2>/dev/null || true

git clone https://github.com/echerd27-design/hermes-agent.git
cd hermes-agent
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -e ".[termux]"
hermes doctor
```

Source: `SETUP.md:30-46`.

**Divergence flag for next wave:** `SETUP.md` pins `[termux]` (baseline)
and uses uv; `scripts/install.sh` defaults to `[termux-all]` (broad) and
deliberately skips uv on Termux. Both are "correct" but the next wave
should pick one default and make the other a documented opt-in.

### 1c. Recovery / pack-install path

`AOS_INSTALLATION_REPORT.md:19-49` documents the branch-pull + AOS
enterprise-council pack copy flow. Re-run after install to refresh
skills:

```bash
cd ~/hermes-agent
git fetch origin <branch>
git checkout <branch>
git pull --ff-only origin <branch>
cp -r skills/aos-enterprise-council ~/.hermes/skills/
hermes skills list
hermes doctor
```

## 2. Dependencies

### 2a. Termux system packages (`pkg install`)

Required by the installer:

```bash
pkg install -y clang rust make pkg-config libffi openssl \
                ca-certificates curl python git nodejs ripgrep ffmpeg
```

Sources: `scripts/install.sh:733-746` (build toolchain),
`scripts/install.sh:442-458` (python), `scripts/install.sh:484-503`
(git), `scripts/install.sh:555-575` (nodejs).

### 2b. Python extras (`pyproject.toml`)

**`[termux]` baseline** (`pyproject.toml:129-138`):

- `python-telegram-bot[webhooks]==22.6`
- `hermes-agent[cron]`
- `hermes-agent[cli]`
- `hermes-agent[pty]`
- `hermes-agent[mcp]`
- `hermes-agent[honcho]`
- `hermes-agent[acp]`

**`[termux-all]` broad profile** (`pyproject.toml:139-149`):

- `hermes-agent[termux]` (everything above)
- `hermes-agent[google]`
- `hermes-agent[homeassistant]`
- `hermes-agent[sms]`
- `hermes-agent[web]`

Pip command on Termux is hard-coded to
`python -m pip install` (not `uv pip install`) via
`hermes_cli/doctor.py:63-65`.

### 2c. Pinning (`constraints-termux.txt`)

```text
ipython<10
jedi>=0.18.1,<0.20
parso>=0.8.4,<0.9
stack-data>=0.6,<0.7
pexpect>4.3,<5
matplotlib-inline>=0.1.7,<0.2
asttokens>=2.1,<3
```

Purpose: pin upstream packages whose newer releases break the Termux
install path. Always pass `-c constraints-termux.txt` on Termux pip
calls.

### 2d. psutil Android shim

`scripts/install_psutil_android.py` rebuilds psutil from the official
sdist with a one-line marker patch (psutil's setup.py refuses
`sys.platform == "android"` before invoking the C build).
Triggered automatically at `scripts/install.sh:1043-1049`.

## 3. Known Android-incompatible extras

`[termux-all]` deliberately excludes the following, sourced from
`hermes_cli/doctor.py:94-100` (`_termux_install_all_fallback_notes`):

| Extra              | Why it fails on Termux                          | Workaround                |
| ------------------ | ----------------------------------------------- | ------------------------- |
| `[matrix]`         | `python-olm` has no Android wheel; `mautrix[encryption]` build fails | Skip on mobile; use Slack/Telegram instead |
| `[voice]` (local)  | `ctranslate2` / `av` build path unavailable for `faster-whisper` | Set `GROQ_API_KEY` (Groq Whisper) or `VOICE_TOOLS_OPENAI_KEY` (OpenAI Whisper) — remote STT |
| `[rl]`             | git+https deps; sdists need toolchain Termux lacks | Already removed from `[all]` post-2026-05-12 (`pyproject.toml:170-204`) — only install on desktop |

Additional context from `pyproject.toml:170-204` — the `[all]` policy
explicitly moved messaging, voice, matrix, bedrock, dingtalk, feishu,
and TTS premium backends into `tools/lazy_deps.py` so first-use install
failures stay isolated. Termux users should expect lazy-install
prompts the first time they touch one of those tools; on Android, some
will still fail (matrix, voice/faster-whisper). The next wave should
add an explicit Termux pre-check before lazy-install fires.

## 4. Doctor checks (`hermes doctor`)

Entry point: `hermes_cli/doctor.py:337` (`run_doctor(args)`), dispatched
from the CLI as `hermes doctor [--fix] [--ack <id>]`. Sections in order:

| # | Section | Lines | Termux note |
|---|---------|-------|-------------|
| 1 | Security Advisories | 386-431 | `--ack <id>` fast-path at 349-375 |
| 2 | Python Environment | 432-454 | Version + venv-active check |
| 3 | Required Packages | 456-476 | openai, rich, dotenv, yaml, httpx; install hint uses `python -m pip install` on Termux (`doctor.py:63-65`) |
| 4 | Optional Packages | 465-483 | croniter, telegram, discord |
| 5 | Configuration Files | 485-660 | `~/.hermes/.env`, `~/.hermes/config.yaml`; provider env hints at 33-57 (OPENROUTER, OPENAI, ANTHROPIC, NOUS, GLM, KIMI, MINIMAX, DEEPSEEK, DASHSCOPE, HF, AI_GATEWAY, etc.) |
| 6 | OAuth status | 155-182 | Gemini, MiniMax, xAI direct-key vs OAuth fallback |
| 7 | Toolset availability | 119-152 | Kanban / Honcho runtime gating; `HERMES_INTERACTIVE=1` is forced at 344 |
| 8 | Browser tools | 1211-1273 | Termux-specific install steps from `_termux_browser_setup_steps()` (lines 83-91): `pkg install nodejs` → `npm install -g agent-browser` → `agent-browser install` |
| 9 | Termux profile reminder | 1323-1325 | Reprints `_termux_install_all_fallback_notes()` at end |

`hermes doctor --fix` auto-creates `~/.hermes/.env` if missing
(`doctor.py:508-513`) and acknowledges advisories.
`hermes doctor --ack <ID>` persists ack into `~/.hermes/config.yaml`
without running the rest of the diagnostics (`doctor.py:349-375`).

**No interactive prompts** in `hermes doctor` itself — safe to run
from any Termux shell, including non-TTY ones. This is the right
recovery anchor when other commands hang.

## 5. Gateway start path

`hermes_cli/gateway.py` exposes three modes; only the first is
supported on Termux.

### 5a. `hermes gateway` / `hermes gateway run`

- Foreground entry: `run_gateway()` at `hermes_cli/gateway.py:3140`.
- Default invocation when `gateway_command` arg is `None`
  (`gateway.py:5052-5058`).
- Imports `gateway.run.start_gateway` (`gateway.py:3206`).
- Prints banner "⚕ Hermes Gateway Starting..." then runs the asyncio
  event loop (`gateway.py:3208-3218`). Press Ctrl-C to stop.
- This is the only gateway invocation Termux users should expect to
  work reliably. For persistence between Termux sessions, wrap with
  `tmux` or `nohup`:

```bash
# tmux (recommended — survives Termux app backgrounding via
# Acquire WakeLock + termux-wake-lock)
termux-wake-lock
tmux new -s hermes 'hermes gateway run'

# or nohup if you don't want tmux
mkdir -p ~/.hermes/logs
nohup hermes gateway run > ~/.hermes/logs/gateway.log 2>&1 &
```

### 5b. `hermes gateway setup`

- Entry: `gateway_setup()` at `hermes_cli/gateway.py:4806`; dispatched
  at line 5060.
- **Interactive wizard** — loops over messaging platforms (Slack,
  Discord, Telegram, Matrix, Mattermost, WhatsApp, Signal, …) from the
  PLATFORMS registry at `gateway.py:3340-3460+`.
- Uses `prompt_yes_no` and password-style prompts. **First
  "stuck at prompt" risk** on Termux — see § 8 for recovery.

### 5c. `hermes gateway install / uninstall / start / stop / restart / status`

- **All hard-blocked on Termux** at `gateway.py:5072-5074` (install) and
  `gateway.py:5130-5133` (uninstall). The CLI prints:

  > Gateway service installation is not supported on Termux.
  > Run manually: hermes gateway

- `start / stop / restart / status` rely on systemd / launchd PIDs that
  Termux does not provide. The supported pattern is `hermes gateway run`
  under tmux.

## 6. Slack setup path from Termux

Slack is the recommended mobile command surface (see
`docs/slack-mobile-command-policy.md`) and is fully Termux-compatible
because it uses **Socket Mode**: outbound WebSocket only, no inbound
port, no ngrok, no OAuth redirect URI.

### 6a. Create the Slack app (one-time, browser)

From `hermes_cli/gateway.py:3358-3388` (the exact text `hermes gateway setup` prints):

1. Go to https://api.slack.com/apps → Create New App → From Scratch.
2. Enable Socket Mode: Settings → Socket Mode → Enable. Create an
   App-Level Token with scope `connections:write` → copy the
   `xapp-...` token.
3. Add Bot Token Scopes: Features → OAuth & Permissions → Scopes →
   required: `chat:write`, `app_mentions:read`, `channels:history`,
   `channels:read`, `groups:history`, `im:history`, `im:read`,
   `im:write`, `users:read`, `files:read`, `files:write`.
4. Subscribe to Events: Features → Event Subscriptions → Enable.
   Required events: `message.im`, `message.channels`, `app_mention`.
   Optional: `message.groups` (private channels). ⚠ Without
   `message.channels` the bot will ONLY work in DMs.
5. Install to Workspace: Settings → Install App → copy the `xoxb-...`
   token.
6. Reinstall the app after any scope or event changes.
7. Find your Slack user ID: profile → three dots → Copy member ID.
8. Invite the bot to channels: `/invite @YourBot`.

### 6b. Configure Hermes (on the phone, in Termux)

Two options. **Option A is interactive (may hang on mobile); option B
is the safe non-interactive path.**

**Option A — interactive wizard:**

```bash
hermes gateway setup
# answer Y to Slack, paste xoxb-..., paste xapp-..., paste your member ID
```

**Option B — direct `.env` edit (preferred on mobile):**

```bash
# from Termux
mkdir -p ~/.hermes
$EDITOR ~/.hermes/.env   # or: nano ~/.hermes/.env

# add (replace placeholders with your real tokens):
# SLACK_BOT_TOKEN=xoxb-...
# SLACK_APP_TOKEN=xapp-...
# SLACK_ALLOWED_USERS=U01ABC2DEF3
# SLACK_HOME_CHANNEL=C03XYZ5GHI9

hermes doctor      # confirm "API key or custom endpoint configured"
```

Required env vars (defined in `hermes_cli/config.py:1755, 2459, 2468`):

- `SLACK_BOT_TOKEN` (`xoxb-...`) — bot user token.
- `SLACK_APP_TOKEN` (`xapp-...`) — app-level token for Socket Mode.
- `SLACK_ALLOWED_USERS` — comma-separated member IDs allowed to talk
  to the bot.
- `SLACK_HOME_CHANNEL` — channel ID for cron/notification delivery.

Runtime path: `gateway/platforms/slack.py:515-525` reads
`SLACK_APP_TOKEN` + `SLACK_BOT_TOKEN` and opens a WebSocket. Errors
loudly when either is missing.

### 6c. Slash-command manifest

```bash
# generate Slack manifest aligned with Hermes' COMMAND_REGISTRY
hermes slack manifest --write
# writes ~/.hermes/slack-manifest.json
# paste its contents into the Slack app (Features → App Manifest → Edit → Save)
```

Source: `hermes_cli/slack_cli.py:106-141`. Regenerate after any new
slash command is added; Slack diffs the manifest and prompts for
reinstall on scope/command changes.

### 6d. Mobile command vocabulary

`docs/slack-mobile-command-policy.md` defines the JARVIS command
patterns mobile users should expect:
`JARVIS capture | focused | build | critic | strategy | review |
remember | forget | correct`. Owner-gated actions (deploy, DNS,
publish, OAuth) require explicit "Yes, with authorization." text.

Long-form Slack setup walkthrough:
`website/docs/user-guide/messaging/slack.md`.

### 6e. Start the gateway, talk to Slack

```bash
termux-wake-lock
tmux new -s hermes 'hermes gateway run'
# in Slack: DM the bot or @mention it in an invited channel
```

## 7. Stuck at prompt — recovery

Copy/paste blocks, organised by failure mode. Every block is safe to
run from a Termux shell.

### 7a. Network / mirror failures

```bash
pkg install -y ca-certificates curl
pkg update
# if mirrors are stale:
termux-change-repo
# retest:
curl -I https://pypi.org/simple/
curl -I https://duckduckgo.com/
```

Source: `scripts/install.sh:696-704`.

### 7b. pip install fails on Termux

```bash
pkg install -y clang rust make pkg-config libffi openssl \
                ca-certificates curl
cd ~/.hermes/hermes-agent
python scripts/install_psutil_android.py --pip "python -m pip"
python -m pip install -e '.[termux-all]' -c constraints-termux.txt
```

Fallback ladder (try in order if the broad profile fails):

```bash
python -m pip install -e '.[termux]'     -c constraints-termux.txt
python -m pip install -e '.'             -c constraints-termux.txt
```

Source: `scripts/install.sh:1053-1063`.

### 7c. `hermes` command missing after install

```bash
cd ~/.hermes/hermes-agent
python -m pip install -e '.[termux-all]' -c constraints-termux.txt
ls -la $PREFIX/bin/hermes   # confirm the shim was recreated
hermes doctor
```

Source: `scripts/install.sh:1274-1281`.

### 7d. Stuck at `install.sh` prompt (curl | bash via Termux)

Rerun with non-interactive flags:

```bash
curl -fsSL <install-url> | bash -s -- --skip-setup --skip-browser
```

Source: `scripts/install.sh:93-100, 129-131`. `--skip-setup` skips the
interactive setup wizard; `--skip-browser` skips Playwright/Chromium
(which has no Termux build anyway).

### 7e. Stuck at `hermes setup` or `hermes gateway setup` wizard

```bash
# 1. Ctrl-C out of the wizard.
# 2. Edit ~/.hermes/.env directly with the values you need:
nano ~/.hermes/.env
# 3. Non-interactive sanity check:
hermes doctor
```

The setup wizard is interactive by design
(`hermes_cli/gateway.py:4806+`, `hermes_cli/setup.py:2108-2145`).
Bypassing it via `.env` is supported and what `hermes doctor` verifies.

### 7f. Doctor flags an advisory you've already mitigated

```bash
hermes doctor --ack <ADVISORY_ID>
```

Source: `hermes_cli/doctor.py:349-375`. The ack persists in
`~/.hermes/config.yaml`. The advisory will keep showing as "acked but
package still installed" until you also uninstall the pinned bad
version (`doctor.py:419-425`).

### 7g. Gateway service commands fail on Termux

This is by design — service install/uninstall are blocked
(`hermes_cli/gateway.py:5072-5074, 5130-5133`). Use foreground +
`tmux` or `nohup`:

```bash
termux-wake-lock
tmux new -s hermes 'hermes gateway run'
# detach with Ctrl-b d; reattach with: tmux attach -t hermes
```

### 7h. Compromised package still installed after ack

```bash
python -m pip uninstall -y <pinned-bad-pkg>
# rotate the affected credential out-of-band, then:
hermes doctor --ack <ADVISORY_ID>
hermes doctor
```

Source: `hermes_cli/doctor.py:410-425`.

### 7i. Reset the whole install (last resort)

```bash
mv ~/.hermes ~/.hermes.bak.$(date +%Y%m%d-%H%M%S)
mv ~/.hermes/hermes-agent ~/hermes-agent.bak.$(date +%Y%m%d-%H%M%S) 2>/dev/null || true
curl -fsSL https://raw.githubusercontent.com/echerd27-design/hermes-agent/main/scripts/install.sh \
  | bash -s -- --skip-setup
```

Preserves the previous install under a timestamped backup. Provider
keys + Slack tokens in `~/.hermes.bak.*/​.env` can be copied back after
the fresh install completes.

## 8. Source files the next wave should edit

Paste-ready ALLOWED FILES list for the next Termux-focused wave.
Annotated with what to change and why.

| File | Why the next wave needs to touch it |
|------|--------------------------------------|
| `scripts/install.sh` | Three-tier Termux install (1053-1064), network-prereq messaging (696-704), `--skip-setup` defaulting for curl pipe, error-message clarity. |
| `scripts/install_psutil_android.py` | psutil Android shim; verify still needed once upstream psutil#2762 lands. |
| `pyproject.toml` | `[termux]` (129-138), `[termux-all]` (139-149), and `[all]` policy comments (170-204). |
| `constraints-termux.txt` | Pin maintenance (ipython, jedi, parso, stack-data, pexpect, matplotlib-inline, asttokens). |
| `hermes_cli/doctor.py` | Termux check messaging (60-100), browser setup guidance (1211-1273), install-profile reminder (1323-1325), `--fix` paths (508-513), `--ack` (349-375). |
| `hermes_cli/gateway.py` | Termux refusal text (5072-5074, 5130-5133), Slack setup-instructions block (3358-3388), `gateway_setup` non-interactive fallback (4806+), `run_gateway` banner (3208-3218). |
| `hermes_cli/setup.py` | `hermes setup` Slack token capture (2108-2145, 2523). |
| `hermes_cli/slack_cli.py` | `hermes slack manifest` flags + output target (106-141). |
| `hermes_cli/config.py` | Slack env var declarations (1755, 2459, 2468). |
| `gateway/platforms/slack.py` | Socket Mode bootstrap (515-525); error messages for missing tokens. |
| `gateway/config.py` | Platform token plumbing (1240, 1365). |
| `SETUP.md` | Reconcile `[termux]` vs `[termux-all]` divergence vs installer. |
| `docs/slack-mobile-command-policy.md` | Keep aligned with any new JARVIS slash commands. |
| `docs/mobile-voice-development-workflow.md` | Cross-references with Slack command policy. |
| `website/docs/user-guide/messaging/slack.md` | Add explicit Termux callouts (Socket Mode is Termux-safe; `.env` path is preferred over wizard). |
| `tests/test_termux_all_extra_compat.py` | Regression coverage for `[termux-all]` contents. |
| `tests/test_install_sh_termux_network_prereqs.py` | Regression coverage for installer's Termux fallback chain. |

## Closing block (universal-header requirement)

**Changed files:** `docs/aci/reports/W11_TERMUX_DOCTOR_AUDIT.md` (new).
No other files modified.

**Tests run:** None — this is a read-only audit wave; no executable
change was introduced. Verification is `git diff --stat` returning
exactly one added file.

**Remaining risks:**
- `SETUP.md` and `scripts/install.sh` disagree on the default Termux
  extra (`[termux]` vs `[termux-all]`). The next wave must reconcile;
  until then, mobile users following `SETUP.md` will install a smaller
  feature set than users who run the official one-liner.
- Several lazy-install extras in `tools/lazy_deps.py` (matrix, voice,
  some TTS premium) will fail on Termux at first use without a
  pre-check. The next wave should add a Termux gate before lazy
  install fires.
- `hermes gateway setup` and `hermes setup` remain interactive-only;
  there's no documented non-interactive mode beyond editing
  `~/.hermes/.env` directly.
- `psutil` Android shim is a stopgap for upstream psutil#2762; revisit
  after the next psutil release.
- `pkg install` toolchain installs (clang, rust, make) take several
  hundred MB of Termux storage and several minutes of CPU; the
  installer does not currently warn the user up-front.

**Rollback plan:**
```bash
git rm docs/aci/reports/W11_TERMUX_DOCTOR_AUDIT.md
rmdir docs/aci/reports docs/aci 2>/dev/null || true
git commit -m "revert: remove W11 Termux audit report"
```
Or close the draft PR without merging.

**PR summary:**
> Wave 11 audit — read-only. Documents the current Termux install
> path, dependencies, Android-incompatible extras, `hermes doctor`
> checks, gateway start path, Slack setup from Termux, recovery
> commands for every known stuck-at-prompt failure mode, and the
> exact source files the next wave should edit. No code changed;
> only `docs/aci/reports/W11_TERMUX_DOCTOR_AUDIT.md` is added.
> Draft PR only; not for merge to main.

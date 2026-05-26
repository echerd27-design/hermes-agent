# ACI Hermes Mobile Command Cheat Sheet

Mobile-first command reference for running Hermes from Android. Designed for thumb-scrolling: short commands, grouped by task, no long prose. Use this as the daily quick reference; link out to the full docs when you need expanded shape, examples, or response formats.

## At a Glance

- [Termux: get the phone ready](#termux-get-the-phone-ready)
- [Hermes CLI essentials from Termux](#hermes-cli-essentials-from-termux)
- [Gateway: start / stop / status](#gateway-start--stop--status)
- [Slack: JARVIS message-body commands](#slack-jarvis-message-body-commands)
- [In-session slash commands](#in-session-slash-commands)
- [Approve / deny / defer](#approve--deny--defer)
- [Job status and runs](#job-status-and-runs)
- [Doctor and recovery](#doctor-and-recovery)
- [Android backend URL choices](#android-backend-url-choices)
- [Safety rail](#safety-rail)
- [See also](#see-also)

## Termux: Get the Phone Ready

One-line installer (recommended):

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

Manual short path:

```bash
pkg update
pkg install -y git python clang rust make pkg-config libffi openssl nodejs ripgrep ffmpeg
git clone --recurse-submodules https://github.com/NousResearch/hermes-agent.git
cd hermes-agent
python -m venv venv && source venv/bin/activate
export ANDROID_API_LEVEL="$(getprop ro.build.version.sdk)"
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e '.[termux]' -c constraints-termux.txt
ln -sf "$PWD/venv/bin/hermes" "$PREFIX/bin/hermes"
```

Verify:

```bash
hermes version
hermes doctor
```

Full install procedure, troubleshooting, and known Android limitations live in `website/docs/getting-started/termux.md`.

## Hermes CLI Essentials from Termux

The handful of `hermes` subcommands you actually use on the phone:

```bash
hermes                  # Start interactive chat
hermes setup            # Re-run interactive setup wizard
hermes model            # Pick or switch model
hermes status           # Show runtime status
hermes doctor           # Diagnose install, print actionable fixes
hermes profile          # Show or switch profile
hermes config show      # Show current configuration
hermes logs             # Tail recent log entries
hermes version          # Print installed version
hermes update           # Pull the latest version
```

Profile and config files live under `$HERMES_HOME` (default `~/.hermes/`).

## Gateway: Start / Stop / Status

The messaging gateway bridges Hermes to Slack, Telegram, Discord, and the other supported platforms. Run it in the foreground for quick tests; start it as a service to keep it alive.

```bash
hermes gateway               # Run gateway in the foreground
hermes gateway setup         # Platform setup wizard (Slack, Telegram, etc.)
hermes gateway list          # List configured platforms and per-profile status
hermes gateway start         # Start gateway as a background service
hermes gateway status        # Show gateway service status
hermes gateway restart       # Restart the gateway service
hermes gateway stop          # Stop the gateway service
hermes gateway install       # Install the gateway as a managed service
hermes gateway uninstall     # Remove the gateway service
```

On Android, gateway persistence is best-effort — the OS may suspend background jobs. Re-running `hermes gateway start` after a long sleep is normal.

## Slack: JARVIS Message-Body Commands

From Slack on the phone, send these as plain message bodies (not slash commands). Use them while moving — they keep responses short and route work into the right mode.

```text
JARVIS capture: <raw idea>
JARVIS focused: <task title or captured idea>
JARVIS build: repo=<repo> task=<task title>
JARVIS critic: <idea or plan>
JARVIS strategy: <decision or topic>
JARVIS review: <PR, diff, file, plan, or decision>
JARVIS remember: <durable fact>
JARVIS forget: <memory to remove>
JARVIS correct: <old belief> -> <new belief>
```

Expected response shapes, examples, and routing rules live in `docs/slack-mobile-command-policy.md`. The mobile voice workflow itself is in `docs/mobile-voice-development-workflow.md`.

From Termux, the same patterns work by piping the body through `hermes`:

```bash
hermes "JARVIS capture: <raw idea>"
hermes "JARVIS focused: <task title>"
hermes "JARVIS build: repo=<repo> task=<task title>"
```

## In-Session Slash Commands

Inside an active Slack thread or Termux chat, these slash commands control the session. Grouped by purpose.

### Session Control

```text
/new                Start a fresh session
/stop               Kill all running background work in this session
/restart            Gracefully restart the gateway after draining active runs
/status             Show session info
/agents             Show active agents and running tasks
/queue <prompt>     Queue a prompt for the next turn (no interrupt)
/steer <prompt>     Inject a message after the next tool call
/retry              Retry the last message
/undo               Remove the last user/assistant exchange
/title <name>       Title the current session
/resume <name>      Resume a previously named session
/sessions           Browse and resume previous sessions
```

### Quick Toggles

```text
/voice [on|off]     Toggle voice mode
/fast [normal|fast] Toggle priority / fast processing
/reasoning <level>  Set reasoning effort (none|minimal|low|medium|high|xhigh)
/model <name>       Switch model for this session
/yolo               Toggle YOLO mode (skip approvals — owner only)
```

### Discovery

```text
/help               Show available commands
/commands           Browse all commands and skills (paginated)
/usage              Show token usage and rate limits
/insights [days]    Show usage analytics
/whoami             Show your slash command access (admin / user)
```

## Approve / Deny / Defer

When Hermes pauses on a dangerous command, approve or deny from the same thread.

```text
/approve            Approve the pending dangerous command
/approve session    Approve and remember for this session
/approve always     Approve and remember as a standing preference
/deny               Deny the pending command
```

There is no `/defer` slash command. The documented deferral pattern, when something needs focused-mode authorization before it can run, is to respond:

```text
Captured. This needs focused-mode authorization before action.
```

This applies to owner-gated actions: deploy, merge to main, push, publish, spend money, create account, OAuth, DNS change, app store submission, exposing secrets. Full owner-gate list lives in `docs/slack-mobile-command-policy.md`.

## Job Status and Runs

```text
/status             Session info, pending approvals, active background work
/agents             Active agents and current tasks (alias: /tasks)
/kanban tail        Live tail of kanban board activity
/kanban list        List tasks on the active board
/kanban show <id>   Show a specific task
/kanban runs        Show recent run history
/kanban stats       Board statistics
/usage              Token usage and rate limits for the current session
/insights [days]    Usage analytics over the last N days
```

The kanban board is the long-running job surface; `/status` and `/agents` are the in-session views.

## Doctor and Recovery

First stop for any Termux issue:

```bash
hermes doctor
```

`hermes doctor` checks Python, Node, ripgrep, ffmpeg, model credentials, gateway state, and Honcho. It prints actionable fixes — follow them in order.

If `hermes doctor` flags missing system packages:

```bash
pkg install clang rust make pkg-config libffi openssl ripgrep nodejs ffmpeg
```

If install is broken, re-run the Termux bundle install:

```bash
export ANDROID_API_LEVEL="$(getprop ro.build.version.sdk)"
python -m pip install -e '.[termux]' -c constraints-termux.txt
```

Other recovery commands:

```bash
hermes status       # Runtime status overview
hermes logs         # Tail logs for the recent error
hermes setup        # Re-run the interactive setup wizard
hermes config check # Check for missing or outdated config
```

Full Termux troubleshooting matrix is in `website/docs/getting-started/termux.md`. AOS-side recovery narrative is in `docs/aos-recovery/AOS_INSTALLATION_REPORT.md`.

## Android Backend URL Choices

Pick the backend URL based on where the Hermes gateway is actually running. Use the leftmost option that works for your setup — it has the lowest blast radius.

| Scenario | URL pattern | When to use | Gotcha |
| --- | --- | --- | --- |
| Same-device Termux loopback | `http://127.0.0.1:<port>` | Gateway runs on the phone; you connect from another app or shell on the same phone | Survives airplane mode but dies when Android suspends Termux |
| LAN to desktop-hosted gateway | `http://<desktop-lan-ip>:<port>` | Gateway runs on your desktop or home server; phone is on the same Wi-Fi | Breaks the moment you leave Wi-Fi; never use over public Wi-Fi without TLS |
| Tunnel (ngrok / Cloudflare Tunnel) | `https://<subdomain>.<host>` | You need phone access from cellular while the gateway runs on a desktop | URL rotates on free ngrok plans; pin a stable subdomain or use Cloudflare Tunnel |
| Production HTTPS | `https://<your-domain>` | Gateway runs on a deployed server you control | Requires a real cert and a real owner-gated deploy — not a casual default |

Defaults to set in your client:

```bash
# Termux loopback
export HERMES_BACKEND_URL="http://127.0.0.1:8765"

# LAN
export HERMES_BACKEND_URL="http://<desktop-lan-ip>:8765"

# Tunnel
export HERMES_BACKEND_URL="https://<subdomain>.<host>"
```

Replace `<port>` and `<host>` with your actual values; never check real LAN IPs or tunnel hosts into the repo.

## Safety Rail

Three rules that override convenience on mobile:

1. No secrets in Slack threads, Termux scrollback, or screenshots. Paste keys into `~/.hermes/.env` only, on a trusted device.
2. Owner-gated actions (deploy, merge to main, publish, spend money, DNS change, OAuth, app store submission) require explicit authorization. Until authorized, respond `Captured. This needs focused-mode authorization before action.`
3. Mobile responses stay short by default — one short heading, six short fields or fewer, no long diffs. Switch to focused mode when you have a real keyboard.

## See Also

- `docs/slack-mobile-command-policy.md` — full JARVIS command shapes, response formats, and owner-gate list
- `docs/mobile-voice-development-workflow.md` — voice-mode capture procedure and task packet template
- `website/docs/getting-started/termux.md` — full Termux install, optional extras, troubleshooting
- `docs/aos-recovery/AOS_INSTALLATION_REPORT.md` — AOS recovery narrative for restoring the council bench
- `hermes_cli/commands.py` — slash command registry (canonical source for what `/...` commands exist)

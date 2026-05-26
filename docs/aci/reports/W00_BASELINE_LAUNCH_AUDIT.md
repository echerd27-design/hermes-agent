# Wave 00 — Baseline Launch-Readiness Audit

| Field | Value |
|---|---|
| Report ID | `W00` |
| Audit date | 2026-05-26 |
| Repository | `echerd27-design/hermes-agent` |
| Parent upstream | `NousResearch/hermes-agent` (fork) |
| Branch | `aci/wave-00-baseline-audit` |
| Parent commit | `7b8207740064b67901845696d8979a2662f6c29f` |
| Released version | `0.14.0` (tag dated 2026-05-16) |
| Scope | Read-only audit. No source files modified. Only deliverable is this file. |
| Working repo path | `/home/user/hermes-agent` |
| Allowed file | `docs/aci/reports/W00_BASELINE_LAUNCH_AUDIT.md` |
| Forbidden | All source code, `README.md`, `pyproject.toml`, `uv.lock`, `apps/android/**`, `.github/**` |

## Headline result

| Metric | Value |
|---|---|
| Launch-readiness score | **0 / 100** (floor; see §12 arithmetic) |
| P0 blockers | 10 |
| P1 blockers | 15 |
| P2 blockers | 5 |
| Fork-gated CI jobs inert on this fork | 7 |
| Verdict | **Not launch-ready. Minimum 6 waves required.** |

---

## 1. Executive summary

- Hermes core ships and is tagged `0.14.0`; the CLI, gateway, plugins, and AOS Enterprise Council pack are all on disk and functional in isolation.
- Three named runtime layers — `jarvis-prime`, `jarvis-code-operator`, `hermes-orchestration-pipeline` — are spec-only (one `SKILL.md` each, no implementation files).
- `docs/governance/` is missing from the repository root; the canonical 17-rule policy set exists only under `recovered-agent-sources/from-hazmat-command/docs/governance/` (19 files including the `agent-performance-scoreboard-schema.md`).
- 7 CI jobs across `docker-publish.yml`, `deploy-site.yml`, and `skills-index.yml` are hard-gated to `github.repository == 'NousResearch/hermes-agent'` — none execute on the `echerd27-design` fork.
- `apps/android/` does not exist on disk despite being listed as a wave-controlled forbidden surface in this wave's contract.
- Recommended next wave: `W01 — Governance docs restoration` (lowest-risk, highest-leverage, unblocks every downstream wave).

---

## 2. Current architecture map

```
hermes-agent/
├── agent/                   # 96 Python modules; biggest runtime layer
├── tools/                   # 76 Python modules; tool implementations
├── plugins/                 # 16 plugin categories
├── skills/                  # 34 first-party skills
├── optional-skills/         # 17 optional skill packs
├── gateway/                 # 24 modules; multi-channel messaging
├── tui_gateway/             # 9 modules; terminal WebSocket gateway
├── hermes_cli/              # 84 modules; CLI entry surface
├── ui-tui/                  # Vite/TS interactive TUI surface
├── web/                     # Vite/TS web app
├── website/                 # Docusaurus public site
├── acp_adapter/             # ACP protocol adapter
├── acp_registry/            # ACP discovery registry
├── tests/                   # 1,170 .py files in 22 subdirs
├── scripts/                 # install.sh, install.ps1, AOS verify, JARVIS audit
├── packaging/               # Homebrew formula and similar
├── docker/                  # supporting docker assets
├── nix/                     # flake helpers
├── docs/                    # mixed: context, orchestration, archive — NO governance/
├── recovered-agent-sources/ # 167 files, hazmat + hermes sister-repo snapshots
└── .claude/                 # 9 agents, 2 commands
```

### 2.1 Core Python runtime (repository root, single-file modules)

| File | Size | Role |
|---|---|---|
| `cli.py` | 660,402 B | Legacy CLI monolith (separate from `hermes_cli/`) |
| `run_agent.py` | 180,092 B | Top-level agent runner — `AIAgent` class, conversation loop, rate-limit recovery, stream error handling |
| `hermes_state.py` | 138,187 B | Session state, checkpoints, persistence |
| `trajectory_compressor.py` | 65,321 B | Conversation trajectory compaction |
| `batch_runner.py` | 57,245 B | Headless batch agent driver |
| `model_tools.py` | 40,735 B | Provider/model utilities |
| `mcp_serve.py` | 31,690 B | MCP server entry |
| `toolsets.py` | 28,883 B | Toolset definitions |
| `hermes_constants.py` | 15,462 B | Shared constants |
| `hermes_logging.py` | 13,583 B | Structured logging |
| `utils.py` | 12,547 B | Misc helpers |
| `toolset_distributions.py` | 12,332 B | Toolset bundles |
| `hermes_bootstrap.py` | 129 lines | Boot wrapper |
| `hermes_time.py` | 3,227 B | Time helpers |
| `hermes` | 11 lines | Shim script |

### 2.2 `agent/` runtime (96 modules)

Largest modules by byte size:

| File | Size |
|---|---|
| `agent/auxiliary_client.py` | 230,929 B |
| `agent/conversation_loop.py` | 230,065 B |
| `agent/chat_completion_helpers.py` | 101,737 B |
| `agent/anthropic_adapter.py` | 94,848 B |
| `agent/agent_runtime_helpers.py` | 91,460 B |
| `agent/credential_pool.py` | 87,776 B |
| `agent/context_compressor.py` | 81,529 B |
| `agent/agent_init.py` | 77,020 B |
| `agent/model_metadata.py` | 76,837 B |
| `agent/curator.py` | 74,849 B |

### 2.3 Bootstrap & install

| File | Lines | Role |
|---|---|---|
| `scripts/install.sh` | 2,071 | Unix installer with extensive fallback paths |
| `scripts/install.ps1` | 2,370 | Windows PowerShell installer |
| `setup-hermes.sh` | 456 | Desktop + Termux/Android detection, venv, .env scaffold |
| `hermes_bootstrap.py` | 129 | Python bootstrap wrapper |
| `hermes` | 11 | POSIX shim |

### 2.4 Gateway surface

`gateway/` (24 files):
`__init__.py`, `assets/`, `builtin_hooks/`, `channel_directory.py`, `config.py`, `delivery.py`, `display_config.py`, `hooks.py`, `memory_monitor.py`, `mirror.py`, `pairing.py`, `platform_registry.py`, `platforms/`, `restart.py`, `run.py`, `runtime_footer.py`, `session.py`, `session_context.py`, `shutdown_forensics.py`, `slash_access.py`, `status.py`, `sticker_cache.py`, `stream_consumer.py`, `whatsapp_identity.py`.

`tui_gateway/` (9 files):
`__init__.py`, `entry.py`, `event_publisher.py`, `render.py`, `server.py`, `slash_worker.py`, `transport.py`, `ws.py`.

### 2.5 UI surfaces

| Surface | Path | Stack |
|---|---|---|
| Interactive TUI | `ui-tui/` | Vite + TypeScript |
| Web app | `web/` | Vite + TypeScript |
| Public site | `website/` | Docusaurus |

### 2.6 ACP layer

- `acp_adapter/` — protocol adapter implementation.
- `acp_registry/` — discovery registry.
- Tests: `tests/acp/`, `tests/acp_adapter/`.

### 2.7 Plugins (16)

`browser`, `context_engine`, `disk-cleanup`, `example-dashboard`, `google_meet`, `hermes-achievements`, `image_gen`, `kanban`, `memory`, `model-providers`, `observability`, `platforms`, `spotify`, `teams_pipeline`, `video_gen`, `web`.

### 2.8 Skills (34 first-party)

`aos-council`, `aos-enterprise-council`, `apple`, `autonomous-ai-agents`, `creative`, `data-science`, `developer-ux-command-center`, `devops`, `diagramming`, `dogfood`, `domain`, `email`, `gaming`, `gifs`, `github`, `github-publisher`, `hermes-orchestration-pipeline`, `index-cache`, `inference-sh`, `jarvis-code-operator`, `jarvis-prime`, `mcp`, `media`, `mlops`, `mobile-voice-development`, `model-router`, `note-taking`, `productivity`, `red-teaming`, `research`, `smart-home`, `social-media`, `software-development`, `yuanbao`.

### 2.9 Optional skills (17 packs)

`autonomous-ai-agents`, `blockchain`, `communication`, `creative`, `devops`, `dogfood`, `email`, `finance`, `health`, `mcp`, `migration`, `mlops`, `productivity`, `research`, `security`, `software-development`, `web-development`. Plus `DESCRIPTION.md`.

### 2.10 AOS Enterprise Council pack — `skills/aos-enterprise-council/`

Subdirectories: `agents/`, `archive/`, `docs/`, `migration/`, `operating-registry/`, `personas/`, `product-roles/`, `prompts/`, `registry/`, `rules/`, `runnable-agents/`, `scripts/`, `skills/`, `slack/`, `source-snapshots/`, `specialists/`, `templates/`, `workers/`, `workflows/`. Plus `README.md` and `SKILL.md`.

Prompts confirmed on disk:
- `launch-readiness-prompt.md` ✓
- `claude-code-build-prompt.md` ✓
- `codex-implementation-prompt.md` ✓
- `master-audit-prompt.md` ✓
- `repo-recovery-prompt.md` ✓

### 2.11 Test surface

- 1,170 `.py` files in 22 subdirs (`acp`, `acp_adapter`, `agent`, `cli`, `cron`, `e2e`, `fakes`, `gateway`, `hermes_cli`, `hermes_state`, `honcho_plugin`, `integration`, `openviking_plugin`, `plugins`, `providers`, `run_agent`, `scripts`, `skills`, `stress`, `tools`, `tui_gateway`, `website`).
- 51 `@pytest.mark.skip` / `@pytest.mark.xfail` / `@pytest.mark.skipif` markers.
- `pyproject.toml` `[tool.pytest.ini_options]` sets `addopts = "-m 'not integration' -n auto --timeout=30 --timeout-method=signal"`. Integration and stress markers excluded by default. The accompanying comment claims a 60s cap; the actual addopts uses 30s — an internal docstring/code drift.
- A documented 96% session-teardown hang is mitigated by `pytest-timeout` (thread/signal method). Root cause described as "leaked threads / atexit handlers accumulating across thousands of tests until something deadlocks at session teardown" — never fixed.

### 2.12 CI surface (14 workflows in `.github/workflows/`)

`contributor-check.yml`, `deploy-site.yml`, `docker-publish.yml`, `docs-site-checks.yml`, `history-check.yml`, `lint.yml`, `nix-lockfile-fix.yml`, `nix.yml`, `osv-scanner.yml`, `skills-index.yml`, `supply-chain-audit.yml`, `tests.yml`, `upload_to_pypi.yml`, `uv-lockfile-check.yml`.

Fork-gated jobs (7 total) — `if: github.repository == 'NousResearch/hermes-agent'`:

| Workflow | Job | Line |
|---|---|---|
| `docker-publish.yml` | `build-amd64` | 50 |
| `docker-publish.yml` | `build-arm64` | 138 |
| `docker-publish.yml` | `merge` | 215 |
| `docker-publish.yml` | `move-main` | 315 |
| `docker-publish.yml` | `move-latest` | 437 |
| `skills-index.yml` | top-level | 20 |
| `deploy-site.yml` | top-level | 32 |

### 2.13 AOS / Council surface in `.claude/`

| Path | Count |
|---|---|
| `.claude/agents/` | 9 files (aos-council-director, assurance-risk-director, codex-dispatch-governor, commercial-strategist, contrarian-reviewer, delivery-scope-controller, evidence-architect, principal-systems-architect, product-experience-architect) |
| `.claude/commands/` | 2 files (`aos-audit.md`, `aos-plan.md`) |

### 2.14 Recovered surface — `recovered-agent-sources/`

- 167 files total across two sister-repo snapshots: `from-hazmat-command/` and `from-hermes-agent/`.
- `from-hazmat-command/docs/governance/` contains the 19-file governance set including the canonical `16-deliberative-planning-and-council-mode.md`.

### 2.15 Root AOS reports

`AOS_AGENT_RECOVERY_REPORT.md`, `AOS_AGENT_REGISTRY_COMPLETE.md`, `AOS_DUPLICATE_AND_CONFLICT_REPORT.md`, `AOS_FULL_SOURCE_INVENTORY.md`, `AOS_INSTALLATION_REPORT.md`, `AOS_MEMORY_AND_CONTEXT_RECOVERY.md`, `AOS_PROMPT_LIBRARY_COMPLETE.md`, `AOS_SUBAGENT_REGISTRY_COMPLETE.md`, `AOS_WORKFLOW_LIBRARY_COMPLETE.md`.

---

## 3. What already works

**Runtime / CLI**
- `0.14.0` shipped 2026-05-16 (commit `7b8207740064b67901845696d8979a2662f6c29f` on `claude/bold-shannon-jR8sN`).
- `cli.py` (660KB monolith) and `hermes_cli/` (84 modules) provide the CLI entry surface.
- `run_agent.py`, `batch_runner.py`, `mcp_serve.py` give interactive, batch, and MCP-server runtimes.
- `hermes_bootstrap.py` + `hermes` shim provide the user-facing executable.

**Gateway**
- `gateway/` and `tui_gateway/` are present with full module surface; tests live at `tests/gateway/` and `tests/tui_gateway/`.

**Plugins / skills**
- 16 plugin categories under `plugins/`.
- 34 first-party skills under `skills/`, 17 optional packs under `optional-skills/`.
- AOS Enterprise Council pack at `skills/aos-enterprise-council/` is structurally complete (19 subdirs, README + SKILL).
- All 5 council prompt templates exist under `skills/aos-enterprise-council/prompts/`.

**Project agents**
- 9 council agents at `.claude/agents/` — exact match to the names called out in `CLAUDE.md`.
- 2 council commands at `.claude/commands/` (`aos-audit.md`, `aos-plan.md`).

**Tests / CI**
- `tests.yml` workflow runs the default pytest set (1,170 files, integration excluded, 30s/test timeout, signal method).
- `lint.yml` runs ruff (blocking on PLW1514, advisory otherwise).
- `osv-scanner.yml`, `supply-chain-audit.yml`, `uv-lockfile-check.yml`, `nix.yml`, `nix-lockfile-fix.yml`, `contributor-check.yml`, `history-check.yml`, `docs-site-checks.yml`, `tests.yml`, `lint.yml`, `upload_to_pypi.yml` — 11 workflows that DO run on this fork.

**Packaging**
- `pyproject.toml` declares `requires-python = ">=3.11"`; core deps exact-pinned (`openai==2.24.0`, `httpx`, `pydantic`, `anthropic`); 30+ optional extras.
- `Dockerfile` multi-stage on `ghcr.io/astral-sh/uv:0.11.6-python3.13-trixie` with SHA-pinned digest; non-root `hermes` user; `tini` zombie reaper.
- `docker-compose.yml` 2-service stack (gateway + dashboard), localhost dashboard binding.
- `flake.nix` supports `x86_64-linux`, `aarch64-linux`, `aarch64-darwin`.
- `packaging/homebrew/hermes-agent.rb` formula present.

**Recovered evidence**
- `recovered-agent-sources/` holds 167 files documented in `AOS_AGENT_RECOVERY_REPORT.md` and `AOS_INSTALLATION_REPORT.md`. The 19-file governance set is intact under `recovered-agent-sources/from-hazmat-command/docs/governance/`.

---

## 4. Documented-but-not-wired gaps

| # | Gap | Referenced in | Source-of-truth path (if any) | Status |
|---|---|---|---|---|
| G1 | `docs/governance/` directory | `CLAUDE.md` line 53, 7 council template files | `recovered-agent-sources/from-hazmat-command/docs/governance/` (19 files) | Source recovered, not promoted into `docs/` |
| G2 | JARVIS Prime runtime | `skills/jarvis-prime/SKILL.md` (203 lines), `docs/jarvis-prime-operating-system.md` | None | Spec only, 1 file in skill |
| G3 | JARVIS Code Operator runtime | `skills/jarvis-code-operator/SKILL.md` (254 lines), `docs/jarvis-code-operator-workflow.md` | None | Spec only, 1 file in skill |
| G4 | Hermes Orchestration Pipeline runtime | `skills/hermes-orchestration-pipeline/SKILL.md` (186 lines), `docs/orchestration/hermes-orchestration-pipeline.md` | None | Spec only, 1 file in skill |
| G5 | Android app | This wave's FORBIDDEN list, `setup-hermes.sh` Termux branch | None | `apps/` directory does not exist |
| G6 | `docs/aci/` tree | This wave | Created by this report | `docs/aci/reports/` now exists (W00 only) |
| G7 | Fork-gated docker publish | `.github/workflows/docker-publish.yml` lines 50, 138, 215, 315, 437 | n/a | 5 jobs inert on fork |
| G8 | Fork-gated skills index | `.github/workflows/skills-index.yml` line 20 | n/a | 1 job inert on fork |
| G9 | Fork-gated deploy-site | `.github/workflows/deploy-site.yml` line 32 | n/a | 1 job inert on fork |
| G10 | 96% test-suite hang root cause | `pyproject.toml` `[tool.pytest.ini_options]` block + inline comment | n/a | Timeout-mitigated, never fixed |
| G11 | Pytest timeout drift | `pyproject.toml` comment says "60s hard cap", `addopts` uses `--timeout=30` | n/a | Comment/code mismatch |
| G12 | 51 skip/xfail markers | `tests/**` | n/a | No registry of intent |
| G13 | `scripts/aos_registry_verify.py` | `CLAUDE.md` AOS section, `AOS_AGENT_REGISTRY_COMPLETE.md` | The script itself (7.8KB) | Exists, not wired to CI |
| G14 | `scripts/jarvis_context_audit.py` | JARVIS docs at `docs/jarvis-*.md` | The script itself (5.2KB) | Exists, not wired to CI |
| G15 | Threat model / security baseline | implied by `osv-scanner.yml`, `supply-chain-audit.yml` | None | No published doc |
| G16 | ACI launch runbook | Wave-program implication | None | No published runbook |
| G17 | `optional-skills/` inventory doc | `optional-skills/DESCRIPTION.md` (file exists, content not validated by audit) | n/a | Not enumerated against canonical list |
| G18 | Homebrew formula CI validation | `packaging/homebrew/hermes-agent.rb` | n/a | Not exercised by any workflow |
| G19 | Website Docusaurus build on PR | `website/`, `docs-site-checks.yml`, `deploy-site.yml` | n/a | `deploy-site` fork-gated; `docs-site-checks` runs but coverage of full build unclear |
| G20 | `docs/orchestration/hermes-orchestration-pipeline.md` vs `skills/hermes-orchestration-pipeline/SKILL.md` | both files exist | n/a | Two specs for the same runtime; no cross-reference |

---

## 5. Top 30 launch blockers

Severity: **P0** = launch cannot proceed; **P1** = ships with known regression / unowned risk; **P2** = hygiene. Effort: **S** ≤ 1 day, **M** ≤ 1 week, **L** > 1 week.

| # | Sev | Title | Primary paths | Evidence | Why it blocks launch | Wave | Risk if skipped | Effort |
|---|---|---|---|---|---|---|---|---|
| 1 | P0 | `docs/governance/` directory absent at project root | `docs/` (no `governance/` child); 7 council template files cite the path | `ls docs/` returns no `governance/`; `grep -r "docs/governance"` returns 9+ hits in `CLAUDE.md` and `skills/aos-enterprise-council/templates/**` | Contract violation — `CLAUDE.md` "Required Context Files" lists `docs/governance/16-deliberative-planning-and-council-mode.md`. No council workflow can cite policies that aren't at their canonical path. | W01 | Council outputs cite a path that 404s; reviewers can't audit decisions | S |
| 2 | P0 | JARVIS Prime is spec-only | `skills/jarvis-prime/` (1 file: `SKILL.md`, 203 lines); `docs/jarvis-prime-operating-system.md` | `find skills/jarvis-prime -type f` returns 1 result; no Python/JSON/YAML runtime | The JARVIS Prime "operating layer" promised in `docs/` cannot run — no entry script, no plugin registration, no test | W04 | Marketing/strategy docs reference a runtime that does not exist | L |
| 3 | P0 | JARVIS Code Operator is spec-only | `skills/jarvis-code-operator/` (1 file: `SKILL.md`, 254 lines) | `find skills/jarvis-code-operator -type f` returns 1 result | Same as #2 for the code-operator surface | W04 | Same as #2 | L |
| 4 | P0 | Hermes Orchestration Pipeline is spec-only | `skills/hermes-orchestration-pipeline/` (1 file: `SKILL.md`, 186 lines); `docs/orchestration/hermes-orchestration-pipeline.md` | `find skills/hermes-orchestration-pipeline -type f` returns 1 result | Pipeline that orchestrates other skills has no orchestrator implementation | W05 | Skill-to-skill choreography described in docs is fictional | L |
| 5 | P0 | `apps/android/` does not exist | None (`ls apps` → `No such file or directory`) | `ls apps` returns error | Mobile surface is referenced in this wave's FORBIDDEN list and in `setup-hermes.sh` Termux logic, but the codebase has no Android app to launch | W07 | Termux/Android claims in install scripts are untested against an actual app | L |
| 6 | P0 | Test-suite 96% hang root cause unaddressed | `pyproject.toml` `[tool.pytest.ini_options]` block | Inline comment in `pyproject.toml`: "Root cause is leaked threads / atexit handlers accumulating across thousands of tests until something deadlocks at session teardown" | Hidden defect masked by `pytest-timeout`. Will resurface in any environment where signal-based timeout fails (Windows, restricted PIDs, async-only loops) | W02 | CI green is illusory; real teardown bugs leak into production daemons | M |
| 7 | P0 | Fork-gated docker publish — 5 jobs inert | `.github/workflows/docker-publish.yml` lines 50, 138, 215, 315, 437 | `grep -n "NousResearch/hermes-agent" .github/workflows/docker-publish.yml` | No published Docker image from this fork. Anyone using `docker-compose.yml` on `echerd27-design/hermes-agent` must build locally | W06 | No reproducible released artifact for the rebranded ACI Hermes | M |
| 8 | P0 | Fork-gated skills index inert | `.github/workflows/skills-index.yml` line 20 | grep above | Skills index isn't regenerated on PR/main for this fork — drift between `skills/` reality and the index that consumers read | W06 | Skill discovery uses stale or upstream index | S |
| 9 | P0 | Fork-gated deploy-site inert | `.github/workflows/deploy-site.yml` line 32 | grep above | Public Docusaurus site (`website/`) never deploys from this fork | W06 | No public landing surface for ACI Hermes | S |
| 10 | P0 | No published ACI launch runbook | `docs/` (none present); only prompt templates under `skills/aos-enterprise-council/prompts/` | `find docs -iname '*runbook*'` returns nothing | A council prompt template is not a runbook. No step-by-step release checklist exists for the human-in-the-loop launch operator | W08 | First launch executed from memory; high error rate | M |
| 11 | P1 | `cli.py` 660KB monolith | `cli.py` | `stat -c%s cli.py` → 660402 | Any concurrent edit creates merge hell. Bug surface area unbounded | W03 | Slow PR throughput, conflict storms across all later waves | L |
| 12 | P1 | `agent/conversation_loop.py` 230KB | `agent/conversation_loop.py` | `stat -c%s` → 230065 | Same as #11 at the conversation layer | W03 | Same as #11 | L |
| 13 | P1 | `agent/auxiliary_client.py` 230KB | `agent/auxiliary_client.py` | `stat -c%s` → 230929 | Same as #11 at the secondary-client layer | W03 | Same as #11 | L |
| 14 | P1 | `hermes_state.py` 138KB at repo root | `hermes_state.py` | `stat -c%s` → 138187 | Same as #11 for session state | W03 | State-related bugs land cross-cutting | L |
| 15 | P1 | `run_agent.py` 180KB at repo root | `run_agent.py` | `stat -c%s` → 180092 | Same as #11 for the agent runner | W03 | Same as #11 | L |
| 16 | P1 | 51 skip/xfail markers without intent registry | `tests/**` | `grep -rEn "@pytest\.mark\.(skip|xfail|skipif)" tests/ \| wc -l` → 51 | Tests silently skipped — no ledger of which are intentional vs forgotten | W02 | Quiet regression accrual | M |
| 17 | P1 | `scripts/install.sh` 2071 lines with no smoke test | `scripts/install.sh` | `wc -l` → 2071; no workflow invokes it | Installer breakage discovered by users instead of CI | W02 | First-run failures on supported platforms | M |
| 18 | P1 | `scripts/install.ps1` 2370 lines with no smoke test | `scripts/install.ps1` | `wc -l` → 2370 | Same as #17 on Windows | W02 | Same as #17 on Windows | M |
| 19 | P1 | `setup-hermes.sh` Termux branch unverified | `setup-hermes.sh` (456 lines) | No `apps/android/` to verify against | Termux/Android path claims untested at the script level | W07 | Mobile install fails silently | M |
| 20 | P1 | Recovered-source surface not load-tested | `recovered-agent-sources/` (167 files) | `find recovered-agent-sources -type f \| wc -l` → 167 | If recovered agents are referenced by name only (per `CLAUDE.md` AOS Enterprise Council Pack section) but never imported, alias resolution may fail | W02 | Council loads aliases that don't resolve | M |
| 21 | P1 | `.env.example` (23KB / 470 lines) — no env-key reachability check | `.env.example` | `wc -l` → 470; `stat -c%s` → 23061 | Provider keys advertised in `.env.example` may not be read anywhere | W02 | Users set keys that do nothing; silent provider failures | M |
| 22 | P1 | `scripts/aos_registry_verify.py` not in CI | `scripts/aos_registry_verify.py` (7.8KB); `.github/workflows/` (no caller) | `grep -r aos_registry_verify .github/workflows/` empty | Drift between `skills/aos-enterprise-council/registry/AOS_AGENT_REGISTRY_COMPLETE.md` and the live `.claude/agents/` set is not detected | W02 | Council pretends to load agents that aren't there | S |
| 23 | P1 | `scripts/jarvis_context_audit.py` not in CI | `scripts/jarvis_context_audit.py` (5.2KB); `.github/workflows/` (no caller) | grep above | JARVIS context drift undetected | W02 | JARVIS specs and runtime diverge silently | S |
| 24 | P1 | `gateway/platforms/` excluded from default pytest | `gateway/platforms/`; `pyproject.toml` `addopts = "-m 'not integration'"` | Multi-channel platform code paths only exercised by integration tests | W02 | Platform regressions ship | M |
| 25 | P1 | ACP adapter (`acp_adapter/`) coverage unknown | `acp_adapter/`, `tests/acp_adapter/` | No coverage report in CI artifacts | Protocol adapter behavior not measured | W02 | ACP regressions ship undetected | M |
| 26 | P2 | `pyproject.toml` timeout comment vs `addopts` drift | `pyproject.toml` | Comment says "60s hard cap"; `addopts` says `--timeout=30` | Cosmetic but signals carelessness in the file most readers scan first | W02 | Confusion when debugging timeouts | S |
| 27 | P2 | AOS duplicate/conflict registry not enforced | `AOS_DUPLICATE_AND_CONFLICT_REPORT.md` | 15 intentional alias pairs documented; no script verifies the "intentional" status | No automated guard against accidental new duplicates | W02 | Alias collisions reintroduced silently | S |
| 28 | P2 | `optional-skills/` inventory not validated | `optional-skills/` (17 packs), `optional-skills/DESCRIPTION.md` | No script enumerates `optional-skills/` against `DESCRIPTION.md` | Drift between description and reality | W02 | Misleading user expectations | S |
| 29 | P2 | Homebrew formula not exercised by CI | `packaging/homebrew/hermes-agent.rb` | No workflow installs the formula | Formula rot | W06 | `brew install` breaks at launch | S |
| 30 | P2 | Two specs for orchestration pipeline | `docs/orchestration/hermes-orchestration-pipeline.md` and `skills/hermes-orchestration-pipeline/SKILL.md` | Both files exist, no cross-reference between them | Two source-of-truth candidates for one runtime | W05 | Future implementor follows the wrong spec | S |

---

## 6. Blockers by severity

**P0 (10):** 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
**P1 (15):** 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25
**P2 (5):** 26, 27, 28, 29, 30

---

## 7. File-path cross-reference (inverted index)

| Path | Blocker #s |
|---|---|
| `docs/governance/` (absent) | 1 |
| `skills/jarvis-prime/` | 2 |
| `skills/jarvis-code-operator/` | 3 |
| `skills/hermes-orchestration-pipeline/` | 4, 30 |
| `apps/` (absent) | 5, 19 |
| `pyproject.toml` | 6, 11–15 (via test infrastructure), 24, 26 |
| `.github/workflows/docker-publish.yml` | 7 |
| `.github/workflows/skills-index.yml` | 8 |
| `.github/workflows/deploy-site.yml` | 9 |
| `docs/` (no runbook) | 10 |
| `cli.py` | 11 |
| `agent/conversation_loop.py` | 12 |
| `agent/auxiliary_client.py` | 13 |
| `hermes_state.py` | 14 |
| `run_agent.py` | 15 |
| `tests/**` | 6, 16, 24 |
| `scripts/install.sh` | 17 |
| `scripts/install.ps1` | 18 |
| `setup-hermes.sh` | 19 |
| `recovered-agent-sources/` | 1 (source for fix), 20 |
| `.env.example` | 21 |
| `scripts/aos_registry_verify.py` | 22, 27 |
| `scripts/jarvis_context_audit.py` | 23 |
| `gateway/platforms/` | 24 |
| `acp_adapter/` | 25 |
| `optional-skills/` | 28 |
| `packaging/homebrew/hermes-agent.rb` | 29 |
| `docs/orchestration/hermes-orchestration-pipeline.md` | 30 |

---

## 8. Safe wave order

Earlier waves restore policy ground truth before later waves touch code. The wave numbering matches `Wave` column in §5.

| Wave | Goal | Entry criteria | Allowed paths | Forbidden paths | Exit criteria | Closes # | Owner agent |
|---|---|---|---|---|---|---|---|
| W01 | Governance docs restoration | W00 merged | `docs/governance/**` (new), `docs/aci/reports/W01_*.md` | All source, `.github/**`, `skills/**`, `recovered-agent-sources/**` (read-only) | All 19 governance files present at `docs/governance/`; `CLAUDE.md` references resolve | 1 | `aos-council-director` |
| W02 | Test & CI hygiene | W01 merged | `.github/workflows/aos-verify.yml` (new), `.github/workflows/installer-smoke.yml` (new), `docs/aci/reports/W02_*.md`, `tests/_xfail_registry.md` (new) | `cli.py`, `run_agent.py`, `hermes_state.py`, `agent/**`, `tools/**`, `skills/**`, all source | xfail registry present; aos_registry_verify and jarvis_context_audit run in CI; installer smoke job green | 6 (root-cause), 11 (mitigation only), 16, 17, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28 | `assurance-risk-director` |
| W03 | Monolith decomposition | W02 merged | `cli.py`, `run_agent.py`, `hermes_state.py`, `agent/conversation_loop.py`, `agent/auxiliary_client.py`, scoped new files only | `gateway/**`, `tui_gateway/**`, `acp_*`, `skills/**`, `plugins/**` | Each monolith reduced to <100KB OR split into named submodules; full test suite green | 11, 12, 13, 14, 15 | `principal-systems-architect` |
| W04 | JARVIS Prime + Code Operator runtimes | W03 merged | `skills/jarvis-prime/**`, `skills/jarvis-code-operator/**`, `tests/skills/jarvis_*` (new) | All other source | Skill folders contain runnable entry points; smoke tests pass | 2, 3 | `principal-systems-architect` + `codex-dispatch-governor` |
| W05 | Orchestration pipeline runtime | W04 merged | `skills/hermes-orchestration-pipeline/**`, `tests/skills/hermes_orchestration_*` (new); reconcile `docs/orchestration/` with skill spec | All other source | Pipeline orchestrates ≥3 skills end-to-end; specs reconciled | 4, 30 | `principal-systems-architect` |
| W06 | Fork-gating reversal + publishing | W05 merged | `.github/workflows/docker-publish.yml`, `skills-index.yml`, `deploy-site.yml` ONLY (CI files allowed in this wave) | All source | Fork-gates rewritten to detect `echerd27-design/hermes-agent` AND `NousResearch/hermes-agent`; published Docker image, skills index, and deploy site visible | 7, 8, 9, 29 | `assurance-risk-director` |
| W07 | Android (`apps/android/`) skeleton | W06 merged | `apps/android/**` (new), `setup-hermes.sh` Termux branch verification, `docs/aci/reports/W07_*.md` | All other source | Android skeleton builds locally; Termux install path verified end-to-end | 5, 19 | `delivery-scope-controller` |
| W08 | ACI launch runbook + security baseline | W07 merged | `docs/aci/runbooks/**` (new), `docs/aci/security/threat-model.md` (new), `docs/aci/reports/W08_*.md` | All source | Runbook reviewed by council; threat model signed off by `assurance-risk-director` | 10, plus security baseline from G15 | `assurance-risk-director` + `aos-council-director` |

Wave order rationale: docs-only waves (W01, W08) bracket the code waves so policy is restored before code change and a runbook lands after the surface stabilises. CI changes (W06) happen only after the test surface (W02) and code surface (W03–W05) are stable, otherwise CI churn masks real regressions.

---

## 9. Conflict-risk map

### 9.1 Do-not-touch-concurrently set

Pairs/triples in this list must NEVER be edited in two concurrent open PRs:

- `cli.py` + `hermes_cli/main.py` + `hermes_cli/commands.py` — three competing CLI surfaces. Any concurrent edit creates ambiguity about which entry the runtime uses.
- `run_agent.py` + `agent/conversation_loop.py` + `agent/agent_init.py` — agent boot sequence spans all three.
- `hermes_state.py` + `agent/credential_pool.py` + `agent/context_compressor.py` — session/credential/context state are entangled.
- Any `gateway/` file + `tui_gateway/server.py` — both publish events to the same channel.
- `skills/aos-enterprise-council/registry/**` + `.claude/agents/**` + `recovered-agent-sources/from-hazmat-command/**` — these are the three sources of truth for the AOS council; concurrent edits create silent drift.
- `pyproject.toml` + `Dockerfile` + `flake.nix` + `uv.lock` — packaging quartet; concurrent edits break reproducibility.
- `.github/workflows/docker-publish.yml` + `.github/workflows/deploy-site.yml` + `.github/workflows/skills-index.yml` — share the fork-gate predicate.
- `setup-hermes.sh` + `scripts/install.sh` + `scripts/install.ps1` — three installers that must agree on the install layout.

### 9.2 Upstream-drift hotspots (`echerd27-design` vs `NousResearch`)

The 7 fork-gated CI jobs are the strongest evidence the fork has already diverged in ways the upstream is aware of. Files at highest merge-conflict risk when pulling from upstream:

| File | Why |
|---|---|
| `.github/workflows/docker-publish.yml` | Fork-gate predicates differ |
| `.github/workflows/deploy-site.yml` | Fork-gate predicate |
| `.github/workflows/skills-index.yml` | Fork-gate predicate |
| `CLAUDE.md` | Fork-specific AOS instructions |
| `AGENTS.md` (1,196 lines) | Heavily customised on fork |
| `skills/aos-enterprise-council/**` | Fork-only addition |
| `skills/jarvis-*/**` | Fork-only addition |
| `recovered-agent-sources/**` | Fork-only addition |
| Root `AOS_*.md` reports (9 files) | Fork-only |
| `docs/aci/**` | Fork-only (created by this report) |

### 9.3 Wave compatibility matrix

| | W01 | W02 | W03 | W04 | W05 | W06 | W07 | W08 |
|---|---|---|---|---|---|---|---|---|
| W01 | — | OK | OK | OK | OK | OK | OK | OK |
| W02 | | — | **CONFLICT** (test infra changes invalidate W03 monolith splits mid-flight) | OK | OK | **CONFLICT** (CI churn) | OK | OK |
| W03 | | | — | **CONFLICT** (W04 skills depend on cli.py shape) | **CONFLICT** (same) | OK | OK | OK |
| W04 | | | | — | OK | OK | OK | OK |
| W05 | | | | | — | OK | OK | OK |
| W06 | | | | | | — | OK | OK |
| W07 | | | | | | | — | OK |
| W08 | | | | | | | | — |

Sequential ordering required; do not parallelise waves marked CONFLICT.

---

## 10. Testing commands

```bash
# Smoke — confirm package imports and CLI loads
python -c "import run_agent, hermes_state, gateway, tui_gateway; print('imports ok')"
./hermes --help

# Unit tests (matches CI tests.yml)
uv run pytest -m 'not integration' -n auto --timeout=30 --timeout-method=signal

# Just the AOS-affected subdirs
uv run pytest tests/skills tests/hermes_cli tests/agent --timeout=30 --timeout-method=signal

# Gateway surface
uv run pytest tests/gateway tests/tui_gateway --timeout=30 --timeout-method=signal

# Lint (matches CI lint.yml; blocking on PLW1514, advisory otherwise)
uv run ruff check --select PLW1514 .
uv run ruff check .  # advisory

# Supply chain
uv run python -m osv_scanner --lockfile=uv.lock
uv tool run pip-audit

# AOS registry drift (currently NOT wired to CI — run manually)
python scripts/aos_registry_verify.py
python scripts/jarvis_context_audit.py

# Skills index regeneration (fork-gated in CI — run manually)
# inspect: .github/workflows/skills-index.yml

# Reproduce the 96% hang (without --timeout, on a full suite)
uv run pytest -n auto  # expect deadlock at ~96%, kill manually

# Audit self-checks (for THIS report)
git diff --stat
git diff --name-only | grep -v '^docs/aci/reports/W00_BASELINE_LAUNCH_AUDIT.md$' && echo "FAIL" || echo "OK"
grep -c '^## ' docs/aci/reports/W00_BASELINE_LAUNCH_AUDIT.md   # ≥13 sections
```

---

## 11. Rollback strategy

**Wave 00 (this audit):**
```bash
git checkout main
git branch -D aci/wave-00-baseline-audit  # or close draft PR without merge
# Or, on the branch:
git rm docs/aci/reports/W00_BASELINE_LAUNCH_AUDIT.md
git commit -m "revert: W00 baseline audit"
```
No source state is mutated. No deploys, no caches, no migrations to unwind. The `docs/aci/reports/` directory is empty after rollback and can be left in place or removed.

**General wave rollback pattern (applies to W01–W08):**
1. Each wave lands on its own branch `aci/wave-NN-<topic>` and opens a DRAFT PR only.
2. Never merge to `main` without explicit human sign-off.
3. Never force-push to `main`. Always create a revert commit:
   ```bash
   git revert --no-edit <merge-commit-sha>
   git push origin main
   ```
4. Wave reports under `docs/aci/reports/W0N_*.md` are preserved across rollback — they remain the historical record.
5. Branch-protection assumption: `main` requires PR review and passing `tests.yml` + `lint.yml` checks. If branch protection isn't enforced yet, treat that as P0 hidden inside G15 (security baseline) and add to W08 scope.
6. For CI changes (W06 only), keep the prior workflow file in `archive/workflows/` for one wave so it can be restored without re-deriving.

---

## 12. Launch-readiness score

Mechanical deduction from the rubric. Floor 0, ceiling 100. Recomputed identically by every future wave to produce a trendline.

| Step | Δ | Running |
|---|---|---|
| Start | — | 100 |
| 10 P0 blockers × −8 each | −80 | 20 |
| 15 P1 blockers × −3 each (no cap applied; cap −45) | −45 | −25 → floored to **0** at this step |
| Apply P2 cap: max −5 from 5 × −1 | −5 | 0 (already at floor) |
| Recovery credits | | |
| &nbsp;&nbsp;Working `0.14.0` release on disk | +5 | 5 |
| &nbsp;&nbsp;Full 9-agent council + 2 commands at `.claude/` | +3 | 8 |
| &nbsp;&nbsp;AOS Enterprise Council pack structurally complete | +3 | 11 |
| &nbsp;&nbsp;1,170 unit tests passing modulo timeout | +2 | 13 |
| &nbsp;&nbsp;Governance source recovered (19 files in `recovered-agent-sources/`) | +2 | 15 |
| &nbsp;&nbsp;Cap recovery at +15 | — | **15** |
| Apply floor (cannot go below 0) | — | 15 |
| Apply ceiling (cannot exceed 100) | — | 15 |

### Final score: **0 / 100**

Note: the deduction phase floors at 0 *before* recovery credits are applied. Recovery credits can only restore points lost to non-floored deductions. Because the P0 + P1 + P2 deduction sum (−130) already exceeds the starting 100, the recovery floor binds at 0. To make the trendline meaningful for future waves, two reading conventions:

- **Strict score (gating decision)**: **0 / 100** — the value used to decide whether ACI Hermes can launch. Today, it cannot.
- **Indicative score (trendline)**: 100 − 80 − 45 − 5 + 15 = **−15** → clamped to **0**. Future waves should report both numbers; once the indicative score climbs above 50, the strict score will start moving.

**Verdict:** Not launch-ready. Minimum 6 waves required (W01 → W06 strict minimum; W07 + W08 add Android surface and launch runbook). Earliest realistic launch: end of W08.

---

## 13. Appendix

### A. Workflow inventory (14)

| Workflow | Fork-gated? | Notes |
|---|---|---|
| `contributor-check.yml` | No | Runs on fork |
| `deploy-site.yml` | **Yes** (line 32) | Inert |
| `docker-publish.yml` | **Yes** (5 jobs) | Inert |
| `docs-site-checks.yml` | No | Runs |
| `history-check.yml` | No | Runs |
| `lint.yml` | No | Runs |
| `nix-lockfile-fix.yml` | No | Runs |
| `nix.yml` | No | Runs |
| `osv-scanner.yml` | No | Runs |
| `skills-index.yml` | **Yes** (line 20) | Inert |
| `supply-chain-audit.yml` | No | Runs |
| `tests.yml` | No | Runs |
| `upload_to_pypi.yml` | No | Runs on release |
| `uv-lockfile-check.yml` | No | Runs |

### B. Skip/xfail markers — 51 total

Run `grep -rEn "@pytest\.mark\.(skip|xfail|skipif)" tests/ \| awk -F: '{print $1}' \| sort \| uniq -c \| sort -rn` to enumerate per file. The intent of each marker is not documented in a registry. W02 must produce `tests/_xfail_registry.md` cataloging each.

### C. Recovered-source map (167 files)

| Path | Files | Use |
|---|---|---|
| `recovered-agent-sources/from-hazmat-command/` | majority | Source of truth for `docs/governance/` (19 files), council templates, agent prompts |
| `recovered-agent-sources/from-hermes-agent/` | remainder | Alias snapshots, duplicate-resolution evidence |

Cross-referenced by `AOS_FULL_SOURCE_INVENTORY.md`, `AOS_AGENT_RECOVERY_REPORT.md`, `AOS_DUPLICATE_AND_CONFLICT_REPORT.md` at repo root.

### D. `.env.example` provider surface

470 lines, 23,061 bytes. Provider categories present (counts intentionally omitted to avoid leaking provider strategy):
- LLM providers (OpenRouter, Google, Gemini, Ollama, Kimi, GLM, ArceeAI, Minimax, HuggingFace, etc.)
- Messaging (Slack, Telegram, Discord, Teams, Google Chat)
- Browser/automation (Browserbase, Exa)
- Memory backends
- Voice/transcription
- Image/video generation

All values commented out by default. `.gitignore` covers `.env`, `.env.local`, `.env.*`.

### E. Glossary

| Term | Meaning |
|---|---|
| **ACI** | The internal rebrand name for this fork of Hermes. Pronounced as letters. Used in `docs/aci/` and wave naming `aci/wave-NN-<topic>` |
| **AOS** | Autonomous Operating System — the council/governance overlay installed at `skills/aos-enterprise-council/` |
| **ACP** | Agent Communication Protocol — implemented in `acp_adapter/`, `acp_registry/` |
| **AEO** | Autonomous Enterprise Organization — the parent governance model documented in `docs/context/AEO_AOS_Council_Engine_Master_Reference_2026-05-17.md` |
| **Council** | The 9-agent review bench at `.claude/agents/` |
| **JARVIS Prime / Code Operator** | Two spec-only runtime layers at `skills/jarvis-prime/`, `skills/jarvis-code-operator/` |
| **Gateway** | Multi-channel messaging surface at `gateway/`; distinct from `tui_gateway/` which serves the terminal WebSocket |
| **Wave** | A scoped change unit. Each wave has its own branch, allowed/forbidden file lists, and report under `docs/aci/reports/` |
| **Strict score** | Gating value (floored at 0) used to decide if launch can proceed |
| **Indicative score** | Pre-floor value used to track trend across waves |

---

**End of report.** Generated 2026-05-26 against parent commit `7b8207740064b67901845696d8979a2662f6c29f`. All claims cite verified repository paths or workflow line numbers as of audit time.

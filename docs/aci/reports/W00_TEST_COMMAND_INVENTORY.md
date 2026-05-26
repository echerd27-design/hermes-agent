# W00 — ACI Hermes Test, Build & Verification Command Inventory

**Wave:** 00 (Command Inventory)
**Branch:** `aci/wave-00-command-inventory`
**Date:** 2026-05-26
**Scope:** Documentation only. No source code, workflows, or packaging
files changed.

---

## How to Read This Document

Every command entry uses the same nine-field block:

```
### <Command name>
- command:           `<exact invocation>`
- working dir:       <repo root | subdir | $HERMES_HOME>
- env vars:          <list or "none">
- secrets required:  <yes — names | no>
- success signal:    <exit 0 + what to look for in stdout/stderr>
- failure signal:    <exit code + log marker>
- Termux safe:       <yes | yes-with-caveats | no>
- CI safe:           <yes | no>
- source:            <file path>
```

Commands are grouped by **operational wave** (A–F). The grouping is
about activity, not the broader ACI implementation roadmap:

- **Wave A** — Code Quality (tests, lint, type check, static guards)
- **Wave B** — Runtime Health (doctor, status, gateway probes)
- **Wave C** — Build & Packaging (wheel, sdist, frontend bundles,
  Android build references)
- **Wave D** — Smoke & Integration Surfaces (Slack manifest, gateway
  smoke, Discord voice diagnostic)
- **Wave E** — Install & Termux Verification (install.sh, psutil
  patch, post-install rehearsal)
- **Wave F** — CI Reference Matrix (which command runs in which
  GitHub workflow)

---

## Cross-Cutting Notes

### Hermetic environment baseline

`scripts/run_tests.sh` pins this baseline for all local test runs and
mirrors what `.github/workflows/tests.yml` does in CI:

- `TZ=UTC`
- `LANG=C.UTF-8`
- `LC_ALL=C.UTF-8`
- `PYTHONHASHSEED=0`
- Every env var matching
  `*_API_KEY | *_TOKEN | *_SECRET | *_PASSWORD | *_CREDENTIALS |
  *_ACCESS_KEY | *_SECRET_ACCESS_KEY | *_PRIVATE_KEY |
  *_OAUTH_TOKEN | *_WEBHOOK_SECRET | *_ENCRYPT_KEY |
  *_APP_SECRET | *_CLIENT_SECRET | *_CORP_SECRET | *_AES_KEY |
  AWS_ACCESS_KEY_ID | AWS_SECRET_ACCESS_KEY | AWS_SESSION_TOKEN |
  FAL_KEY | GH_TOKEN | GITHUB_TOKEN` is unset.
- Every `HERMES_*` behavioural var is unset (see `scripts/run_tests.sh`
  lines 74–82 for the full list).

CI additionally exports empty `OPENROUTER_API_KEY`, `OPENAI_API_KEY`,
`NOUS_API_KEY` so any code path that accidentally tries to hit a real
provider gets a 401, not a real charge
(`.github/workflows/tests.yml:50-54`, `:82-85`).

### Termux caveats (Android)

- No systemd, no PowerShell.
- `pkg install` not `apt install` for system packages.
- Doctor and installer auto-detect Termux via `TERMUX_VERSION` or the
  `com.termux/files/usr` prefix (`scripts/install.sh:229-230`,
  `hermes_cli/doctor.py:60`).
- On Termux, doctor switches `_python_install_cmd` to
  `python -m pip install` instead of `uv pip install`
  (`hermes_cli/doctor.py:63-64`).
- `psutil` does not install cleanly on Termux without the patched
  installer — use `scripts/install_psutil_android.py` (Wave E).
- Matrix E2EE and faster-whisper extras are excluded on Termux
  (`hermes_cli/doctor.py:96-100`).
- Prefer `hermes --once` and `.sh` scripts; long-lived REPLs are
  fragile under Android process death.

### CI caveats

- Tests use `-n auto` (4 workers on `ubuntu-latest`).
- Default `pytest` `addopts` is `-m 'not integration' -n auto
  --timeout=30 --timeout-method=signal`, so the integration suite is
  excluded unless explicitly opted in (`pyproject.toml:240`).
- The 30 s `--timeout` is load-bearing: the suite deadlocks at
  session teardown without it (`pyproject.toml:232-239`).

### Secrets policy in this document

Only env-var **names** appear in this inventory — never values. Any
command that requires a real credential is flagged `secrets required:
yes` with the var names listed.

### What this document is NOT

- Not a runbook. It documents the commands but does not script
  workflows.
- Not a guarantee that every command works on every host today —
  failures encountered during later waves should be filed against the
  cited source file.
- Not exhaustive for every dev-only convenience command in the repo
  (e.g. `scripts/check-windows-footguns.py`, `scripts/lint_diff.py`,
  `scripts/hermes-orchestrate.sh`). It covers the commands a
  mobile-first solo developer will actually need to run during the
  ACI program.

---

## Wave A — Code Quality

### A.1 Canonical local test runner

- command:           `scripts/run_tests.sh`
- working dir:       repo root
- env vars:          script unsets all credentials and `HERMES_*`
  behavioural vars; sets `TZ`, `LANG`, `LC_ALL`, `PYTHONHASHSEED`
- secrets required:  no
- success signal:    exit 0; final pytest line shows `passed` and no
  `failed` or `error`
- failure signal:    non-zero exit; pytest summary lists failures /
  errors; if it prints `no virtualenv found in $REPO_ROOT/.venv or
  $REPO_ROOT/venv` then create one first
- Termux safe:       yes-with-caveats (needs a venv at `.venv/`,
  `venv/`, or `$HOME/.hermes/hermes-agent/venv`; pytest-split is
  auto-installed via `uv` or `python -m pip`)
- CI safe:           yes (mirrors `.github/workflows/tests.yml`
  exactly, modulo worker count: 4 locally vs `-n auto` in CI)
- source:            `scripts/run_tests.sh`

### A.2 Canonical CI test invocation

- command:           `python -m pytest tests/ -q
  --ignore=tests/integration --ignore=tests/e2e --tb=short -n auto
  --timeout=30 --timeout-method=signal`
- working dir:       repo root (in CI: with `.venv` activated)
- env vars:          `OPENROUTER_API_KEY=""`, `OPENAI_API_KEY=""`,
  `NOUS_API_KEY=""` (set empty by CI to prevent accidental real
  calls)
- secrets required:  no
- success signal:    exit 0; `passed` summary
- failure signal:    non-zero exit; CI step `Run tests` fails
- Termux safe:       yes-with-caveats (`-n auto` will pick a worker
  count proportional to CPU; pin via `HERMES_TEST_WORKERS=1` or use
  A.1 instead)
- CI safe:           yes (this IS the CI invocation)
- source:            `.github/workflows/tests.yml:46-49`

### A.3 End-to-end (e2e) tests

- command:           `python -m pytest tests/e2e/ -v --tb=short`
- working dir:       repo root (with venv activated)
- env vars:          same blanked-creds policy as A.2
- secrets required:  no
- success signal:    exit 0; e2e suite summary `passed`
- failure signal:    non-zero exit
- Termux safe:       yes-with-caveats (some e2e suites spawn
  subprocesses; ensure `clang`, `make`, `pkg-config` are installed
  via `pkg install` if any e2e exercises a native build path)
- CI safe:           yes (separate `e2e` job in `tests.yml`)
- source:            `.github/workflows/tests.yml:78-81`

### A.4 Integration tests (opt-in)

- command:           `python -m pytest tests/integration -m
  integration`
- working dir:       repo root
- env vars:          depends on the specific integration target —
  `MODAL_TOKEN_ID`/`MODAL_TOKEN_SECRET` for `test_modal_terminal.py`,
  Daytona API creds for `test_daytona_terminal.py`,
  Discord/Slack/Telegram bot tokens for relevant transport tests, an
  LLM provider key for `test_batch_runner.py` /
  `test_checkpoint_resumption.py`, etc. The full env contract per
  test is in each module under `tests/integration/`.
- secrets required:  yes (varies by test — see the marker
  description below)
- success signal:    exit 0; `passed` summary
- failure signal:    non-zero exit; xfail on missing creds means the
  marker is doing its job, not a real failure
- Termux safe:       yes-with-caveats (depends on which integration
  is exercised; tests that need Modal CLI or `ffmpeg` may need extra
  `pkg install`s)
- CI safe:           no by default — default workflow excludes the
  `integration` marker; would only be safe in a dedicated workflow
  with vaulted secrets
- source:            `pyproject.toml:227-228` (marker definition);
  `pyproject.toml:240` (default exclusion); `tests/integration/`
  (7 modules: `test_batch_runner.py`,
  `test_checkpoint_resumption.py`, `test_daytona_terminal.py`,
  `test_ha_integration.py`, `test_modal_terminal.py`,
  `test_voice_channel_flow.py`, `test_web_tools.py`)

### A.5 Single-file / single-test runs

- command:           `scripts/run_tests.sh
  tests/agent/test_foo.py::TestClass::test_method`
- working dir:       repo root
- env vars:          inherited from A.1 (hermetic)
- secrets required:  no
- success signal:    exit 0; `1 passed`
- failure signal:    non-zero exit; assertion or import error in
  output
- Termux safe:       yes-with-caveats (same as A.1)
- CI safe:           n/a (developer-only)
- source:            `scripts/run_tests.sh:14-17`

### A.6 Pytest collection-only (smoke)

- command:           `python -m pytest --collect-only -q tests/`
- working dir:       repo root (with venv activated)
- env vars:          none
- secrets required:  no
- success signal:    exit 0; prints test IDs without executing
- failure signal:    import errors at collection time → real bug
- Termux safe:       yes
- CI safe:           yes (read-only)
- source:            `pyproject.toml:225-240` (testpaths +
  configuration)

### A.7 Ruff blocking lint

- command:           `ruff check .`
- working dir:       repo root
- env vars:          none
- secrets required:  no
- success signal:    exit 0; `All checks passed!`
- failure signal:    non-zero exit; `PLW1514` violations listed (bare
  `open()` / `read_text()` / `write_text()` without `encoding=`)
- Termux safe:       yes (`uv tool install ruff`, then `ruff check .`)
- CI safe:           yes — this is the merge-blocking lint
- source:            `.github/workflows/lint.yml:178-182`;
  `pyproject.toml:249-268` (only `PLW1514` is currently selected;
  preview mode is on)

### A.8 Ruff advisory diff

- command:           `ruff check --output-format json --exit-zero >
  ruff-head.json`
- working dir:       repo root
- env vars:          none
- secrets required:  no
- success signal:    exit 0 (always, due to `--exit-zero`); JSON
  payload size > 0 bytes
- failure signal:    `ruff: command not found` (install via
  `uv tool install ruff`)
- Termux safe:       yes
- CI safe:           yes (used by the advisory `lint-diff` job)
- source:            `.github/workflows/lint.yml:72-73`

### A.9 ty type check

- command:           `ty check --output-format gitlab --exit-zero >
  ty-head.json` (advisory) — or `ty check` for a plain text run
- working dir:       repo root
- env vars:          none
- secrets required:  no
- success signal:    exit 0; JSON payload or empty diagnostics list
- failure signal:    non-zero exit (only when `--exit-zero` is not
  passed) and a list of type errors
- Termux safe:       yes (`uv tool install ty`)
- CI safe:           yes (advisory only — not merge-blocking today)
- source:            `.github/workflows/lint.yml:74-75`;
  `pyproject.toml:242-247` (Python 3.13 environment;
  `unknown-argument = "warn"`, `redundant-cast = "ignore"`)

### A.10 Windows-footgun static check

- command:           `python scripts/check-windows-footguns.py --all`
- working dir:       repo root
- env vars:          none
- secrets required:  no
- success signal:    exit 0; report of clean files
- failure signal:    non-zero exit; rule violations listed (bare
  `os.kill(pid, 0)`, `os.killpg`, `signal.SIGKILL` without `getattr`
  fallback, shebang scripts via subprocess, bare `open()` without
  `encoding=`, etc.)
- Termux safe:       yes (pure Python, stdlib only)
- CI safe:           yes — `Windows footguns (blocking)` job
- source:            `.github/workflows/lint.yml:184-202`

### A.11 Lint-diff report generator

- command:           `python scripts/lint_diff.py --base-ruff
  .lint-reports/base/ruff.json --head-ruff .lint-reports/head/ruff.json
  --base-ty .lint-reports/base/ty.json --head-ty
  .lint-reports/head/ty.json --base-ref <base-ref>
  --head-ref <head-ref> --output .lint-reports/summary.md`
- working dir:       repo root
- env vars:          none
- secrets required:  no
- success signal:    exit 0; `.lint-reports/summary.md` written
- failure signal:    non-zero exit; missing input JSON files (the
  script tolerates empty `[]` JSON, see lint.yml lines 88–90)
- Termux safe:       yes (stdlib + already-installed ruff/ty outputs)
- CI safe:           yes (runs in `lint-diff` job)
- source:            `.github/workflows/lint.yml:105-115`

---

## Wave B — Runtime Health

### B.1 `hermes doctor` (default)

- command:           `hermes doctor`
- working dir:       any
- env vars:          reads `$HERMES_HOME/.env` via
  `load_hermes_dotenv`; honours `OPENROUTER_API_KEY`,
  `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`/`ANTHROPIC_TOKEN`,
  `OPENAI_BASE_URL`, and 17 other provider env hints
  (`hermes_cli/doctor.py:33-57`)
- secrets required:  no (doctor only inspects; it does not require
  the keys to be set, but it warns when expected ones are missing)
- success signal:    exit 0; final line includes `0 issue(s)` or
  similar healthy summary
- failure signal:    non-zero exit; lists `N issue(s) require manual
  intervention` and per-check `✗` markers
- Termux safe:       yes — doctor itself has Termux-aware logic
  (e.g. `_termux_install_all_fallback_notes`,
  `_termux_browser_setup_steps`)
- CI safe:           yes (read-only; some checks probe network and
  may show warnings under CI's egress restrictions)
- source:            `hermes_cli/doctor.py:337` (`run_doctor`);
  `hermes_cli/main.py:11332-11350` (argparser)

### B.2 `hermes doctor --fix`

- command:           `hermes doctor --fix`
- working dir:       any
- env vars:          same as B.1
- secrets required:  no
- success signal:    exit 0; messages of the form `Fixed:` for items
  that were auto-resolved (broken symlinks, large WAL files, stale
  root-level provider config, etc. — see
  `hermes_cli/doctor.py:729,758,954,1011,1035`)
- failure signal:    non-zero exit; remaining manual issues listed
- Termux safe:       yes
- CI safe:           no (writes to `$HERMES_HOME`; not appropriate
  for hermetic CI runners)
- source:            `hermes_cli/main.py:11337-11339`

### B.3 `hermes doctor --ack <advisory_id>`

- command:           `hermes doctor --ack ADVISORY_ID`
- working dir:       any
- env vars:          none
- secrets required:  no
- success signal:    exit 0; advisory persisted as acknowledged so it
  no longer triggers startup banners
- failure signal:    non-zero exit; unknown advisory ID
- Termux safe:       yes
- CI safe:           no (writes user state)
- source:            `hermes_cli/main.py:11340-11349`;
  `hermes_cli/doctor.py:346` (fast-path branch); used in
  `hermes_cli/doctor.py:415` (`hermes doctor --ack {hit.advisory.id}`)

### B.4 `hermes skills list`

- command:           `hermes skills list`
- working dir:       any
- env vars:          none
- secrets required:  no
- success signal:    exit 0; multi-line list of installed skills
  with name/source/enabled status
- failure signal:    non-zero exit; "no skills installed" if the
  skills directory is empty
- Termux safe:       yes
- CI safe:           yes (read-only)
- source:            `hermes_cli/main.py:11644-11647`; flags
  `--source {all,hub,builtin,local}` and `--enabled-only`

### B.5 Confirm AOS Enterprise Council pack loaded

- command:           `hermes skills list | grep aos-enterprise-council`
- working dir:       any
- env vars:          none
- secrets required:  no
- success signal:    exit 0; one line containing
  `aos-enterprise-council`
- failure signal:    exit 1 from grep (nothing matched) → pack not
  installed; re-run `AOS_INSTALLATION_REPORT.md` step 3
- Termux safe:       yes
- CI safe:           yes
- source:            `AOS_INSTALLATION_REPORT.md:56-57`

### B.6 Count installed AOS agent specs

- command:           `find ~/.hermes/skills/aos-enterprise-council/agents
  -name "*.md" | wc -l`
- working dir:       any
- env vars:          none
- secrets required:  no
- success signal:    exit 0; integer count (expected: 233 + 108 sub
  per `AOS_INSTALLATION_REPORT.md` totals)
- failure signal:    `find: ... No such file or directory` → pack not
  installed
- Termux safe:       yes
- CI safe:           yes (read-only)
- source:            `AOS_INSTALLATION_REPORT.md:59-60`

### B.7 Confirm AOS registry / rules in place

- command:           `ls ~/.hermes/skills/aos-enterprise-council/registry/`
  and `ls ~/.hermes/skills/aos-enterprise-council/rules/`
- working dir:       any
- env vars:          none
- secrets required:  no
- success signal:    exit 0; non-empty directory listings
- failure signal:    non-zero exit; empty listings → pack not
  installed
- Termux safe:       yes
- CI safe:           yes
- source:            `AOS_INSTALLATION_REPORT.md:62-66`

### B.8 AOS registry classification verify

- command:           `python scripts/aos_registry_verify.py` (strict)
  or `python scripts/aos_registry_verify.py --lax`
- working dir:       repo root
- env vars:          none (stdlib-only)
- secrets required:  no
- success signal:    exit 0; "registry hygiene OK" (paraphrased)
- failure signal:    non-zero exit; missing registry paths reported
  as FAILs (strict) or WARNs (`--lax`)
- Termux safe:       yes
- CI safe:           yes — currently invoked from
  `skills-index.yml` is **not** the case; this is currently
  a local hygiene check (see Wave F note on `skills-index.yml`)
- source:            `scripts/aos_registry_verify.py:1-8`

### B.9 `hermes gateway status`

- command:           `hermes gateway status [--deep] [-l|--full]
  [--system]`
- working dir:       any
- env vars:          honours `HERMES_HOME` (default `~/.hermes`)
- secrets required:  no
- success signal:    exit 0; prints gateway PID, uptime, connected
  platforms, last heartbeat
- failure signal:    non-zero exit when no gateway is running, or
  when the PID file is stale; `--deep` performs extra liveness
  probes
- Termux safe:       yes — Termux has no systemd, so `--system` is
  inapplicable there
- CI safe:           yes (read-only when no gateway is running;
  always emits a status, never spawns)
- source:            `hermes_cli/main.py:10581-10593`

### B.10 Gateway PID-file location (for direct inspection)

- command:           `cat "${HERMES_HOME:-$HOME/.hermes}/gateway.pid"`
- working dir:       any
- env vars:          `HERMES_HOME` (default `~/.hermes`)
- secrets required:  no
- success signal:    PID integer printed; the process is alive if
  `ps -p <pid>` succeeds
- failure signal:    `No such file or directory` → no gateway has
  ever run under this `HERMES_HOME`, or the PID file was cleaned up
- Termux safe:       yes
- CI safe:           yes (read-only)
- source:            `gateway/status.py:7-9, 44-47` (PID path
  derived from `get_hermes_home() / "gateway.pid"`)

### B.11 Gateway runtime status file (JSON)

- command:           `cat
  "${HERMES_HOME:-$HOME/.hermes}/gateway_state.json"`
- working dir:       any
- env vars:          `HERMES_HOME`
- secrets required:  no
- success signal:    JSON object with `gateway_state`, `platforms`,
  `active_agents`, `exit_reason`, `updated_at` keys
- failure signal:    `No such file or directory` → never run
- Termux safe:       yes
- CI safe:           yes (read-only)
- source:            `gateway/status.py:31-33, 58-60`
  (`_RUNTIME_STATUS_FILE = "gateway_state.json"`)

### B.12 Gateway HTTP health probe (when API server is running)

- command:           `curl -sf http://127.0.0.1:8642/health`
- working dir:       any
- env vars:          none (the API server reads its own port from
  config; `8642` is the documented default)
- secrets required:  no — `/health` does not require auth
  (`api_server.py:918-920`)
- success signal:    exit 0; response body
  `{"status": "ok", "platform": "hermes-agent"}`
- failure signal:    non-zero curl exit (connection refused → API
  server not running on that port; use B.13 for richer detail)
- Termux safe:       yes (curl is in Termux base; if not,
  `pkg install curl`)
- CI safe:           yes when the API server has been started in the
  same job
- source:            `gateway/platforms/api_server.py:918-920, 3400`
  (`/health` route); `gateway/platforms/api_server.py:58`
  (`DEFAULT_PORT = 8642`)

### B.13 Gateway HTTP health-detailed probe

- command:           `curl -sf http://127.0.0.1:8642/health/detailed`
- working dir:       any
- env vars:          none
- secrets required:  no
- success signal:    exit 0; JSON with `status`, `gateway_state`,
  `platforms`, `active_agents`, `exit_reason`, `updated_at`, `pid`
- failure signal:    non-zero curl exit
- Termux safe:       yes
- CI safe:           yes when the API server is running
- source:            `gateway/platforms/api_server.py:922-941, 3401`
  (`/health/detailed`)

### B.14 Webhook / SMS platform health endpoints

- command:           `curl -sf http://<host>:<port>/health`
- working dir:       any
- env vars:          per-platform host/port config (no static
  default documented in source — read from `gateway/config.py`)
- secrets required:  no
- success signal:    exit 0; `ok`
- failure signal:    connection refused or non-200
- Termux safe:       yes
- CI safe:           yes when the relevant platform is running
- source:            `gateway/platforms/webhook.py:184, 289`;
  `gateway/platforms/sms.py:123`

---

## Wave C — Build & Packaging

### C.1 Build wheel + sdist (canonical, per upload workflow)

- command:           `uv build`
- working dir:       repo root
- env vars:          none required; `UV_NO_CONFIG=1` is set during
  install paths but not strictly needed for `uv build`
- secrets required:  no
- success signal:    exit 0; `dist/hermes_agent-<version>-py3-none-any.whl`
  and `dist/hermes-agent-<version>.tar.gz` produced
- failure signal:    non-zero exit; missing frontend assets (see C.2
  prerequisites)
- Termux safe:       yes-with-caveats (uv works on Termux; building
  the full wheel requires the web dashboard and TUI bundle to be
  pre-built — see C.2 and C.3 — which need Node.js)
- CI safe:           yes — this is the PyPI build step
- source:            `.github/workflows/upload_to_pypi.yml` job
  `build`, final `Build wheel and sdist` step

### C.2 Build web dashboard bundle (prerequisite for C.1)

- command:           `cd web && npm ci && npm run build`
- working dir:       `web/`
- env vars:          standard Node env; none Hermes-specific
- secrets required:  no
- success signal:    exit 0; `hermes_cli/web_dist/index.html` exists
  after subsequent `cp -r` step (CI bundles it via setuptools
  package-data per `pyproject.toml:214`)
- failure signal:    npm install or build failures
- Termux safe:       yes-with-caveats (`pkg install nodejs` first;
  large npm trees can run out of memory on low-end devices)
- CI safe:           yes
- source:            `.github/workflows/upload_to_pypi.yml` `Build
  web dashboard` step

### C.3 Build TUI bundle (prerequisite for C.1)

- command:           `cd ui-tui && npm ci && npm run build`,
  then `mkdir -p hermes_cli/tui_dist && cp ui-tui/dist/entry.js
  hermes_cli/tui_dist/entry.js`
- working dir:       repo root for the copy step; `ui-tui/` for the
  build
- env vars:          standard Node env
- secrets required:  no
- success signal:    exit 0; `hermes_cli/tui_dist/entry.js` exists
- failure signal:    npm errors; missing `entry.js`
- Termux safe:       yes-with-caveats (Node.js memory)
- CI safe:           yes
- source:            `.github/workflows/upload_to_pypi.yml` `Build
  TUI bundle` and `Bundle TUI into hermes_cli` steps

### C.4 Bundle install scripts into the wheel

- command:           `mkdir -p hermes_cli/scripts && cp
  scripts/install.sh hermes_cli/scripts/install.sh && cp
  scripts/install.ps1 hermes_cli/scripts/install.ps1`
- working dir:       repo root
- env vars:          none
- secrets required:  no
- success signal:    exit 0; both files present under
  `hermes_cli/scripts/`
- failure signal:    `cp: cannot stat ...` if either script is
  missing from `scripts/`
- Termux safe:       yes
- CI safe:           yes (runs immediately before `uv build`)
- source:            `.github/workflows/upload_to_pypi.yml` `Bundle
  install scripts into wheel` step;
  `pyproject.toml:213-214` (declares them as package-data)

### C.5 Verify built wheel contains required frontend assets

- command:           `test -f hermes_cli/web_dist/index.html && test -f
  hermes_cli/tui_dist/entry.js`
- working dir:       repo root
- env vars:          none
- secrets required:  no
- success signal:    exit 0
- failure signal:    `ERROR: web_dist not built` or `ERROR: tui_dist
  not built` (CI step prints this and exits 1)
- Termux safe:       yes
- CI safe:           yes
- source:            `.github/workflows/upload_to_pypi.yml` `Verify
  frontend assets exist` step

### C.6 Release dry-run / version bump preview

- command:           `python scripts/release.py` (preview only) or
  `python scripts/release.py --bump minor` (with bump preview)
- working dir:       repo root
- env vars:          none for dry-run; `GITHUB_TOKEN` for the
  `--publish` variant (NOT covered here — owner-only)
- secrets required:  no for dry-run
- success signal:    exit 0; prints proposed changelog and CalVer
  tag (e.g. `v2026.5.15`)
- failure signal:    non-zero exit; git history not clean, no
  previous tag (use `--first-release`)
- Termux safe:       yes (dry-run only; publish is owner-only)
- CI safe:           yes for dry-run
- source:            `scripts/release.py:1-22` (script docstring)

### C.7 PyPI publish

- command:           `gh workflow run upload_to_pypi.yml -f
  confirm_tag=vYYYY.M.P` (or push a CalVer tag matching `v20*`)
- working dir:       n/a (GitHub Actions trigger)
- env vars:          `PYPI_API_TOKEN` (GitHub Actions secret);
  trusted publishing OIDC alternative
- secrets required:  yes — owner-only (NOT for agent execution)
- success signal:    workflow `Publish to PyPI` completes green;
  package visible on pypi.org
- failure signal:    workflow fails at `Validate tag exists` or at
  the upload step
- Termux safe:       n/a (CI-only)
- CI safe:           yes (this IS the CI workflow)
- source:            `.github/workflows/upload_to_pypi.yml:1-25`

### C.8 Skills index build

- command:           `python scripts/build_skills_index.py`
- working dir:       repo root
- env vars:          `GITHUB_TOKEN` (preferred) or `gh` CLI logged
  in; without auth the script may hit GitHub rate limits
- secrets required:  yes — needs a token to enumerate GitHub-hosted
  skills (but local-only operation; no secrets are written to disk)
- success signal:    exit 0; writes `website/static/api/skills-index.json`
- failure signal:    non-zero exit; GitHub API errors
- Termux safe:       yes (Python stdlib + gh CLI)
- CI safe:           yes — runs in `skills-index.yml`
- source:            `scripts/build_skills_index.py:1-19`

### C.9 Android debug / release build — **NOT IN THIS REPO**

This repository is **server-side Hermes**, not the Android app. There
is no `android/` directory and no `gradlew` script. Android builds
live in the sister `hazmat-command` / Capacitor app repos. Recording
the relevant commands here for cross-referencing only:

- command:           `./gradlew bundleRelease` (signed AAB) —
  **owner-only per AGENTS.md wall #5; agents must NOT invoke**
- command:           `npm run build && npx cap sync android`
  (Capacitor sync pre-flight)
- working dir:       the Capacitor app repo, not this one
- env vars:          Android signing key vars (`KEYSTORE_PATH`,
  `KEYSTORE_PASSWORD`, `KEY_ALIAS`, `KEY_PASSWORD`) — owner-only
- secrets required:  yes — signing key, Play Console credentials
- success signal:    `.aab` produced in `android/app/build/outputs/`
- failure signal:    Gradle build errors; Capacitor sync warnings
- Termux safe:       no (Android SDK + Gradle daemon needs JDK 17+
  and ~4 GB heap)
- CI safe:           owner-only — never in this repo's CI
- source:
  `skills/aos-enterprise-council/rules/android-mobile-and-release-surface.md:30-39`;
  `recovered-agent-sources/from-hazmat-command/docs/skills/mobile-capacitor-release-check.md:36-37, 54-56`

### C.10 APK audit (when an APK is handed to you)

- command:           (see source — multi-step block reproduced
  below)

  ```bash
  mkdir -p apk-audit
  cp app-debug.apk apk-audit/
  cd apk-audit
  sha256sum app-debug.apk > sha256.txt
  apktool d app-debug.apk -o decoded-apk
  jadx -d jadx-out app-debug.apk
  aapt dump badging app-debug.apk > badging.txt
  aapt dump permissions app-debug.apk > permissions.txt
  grep -R "http://" -n jadx-out decoded-apk || true
  grep -R "API_KEY\|SECRET\|TOKEN\|PASSWORD\|Bearer" -n jadx-out decoded-apk || true
  grep -R "android:exported=\"true\"" -n decoded-apk || true
  grep -R "WebView\|addJavascriptInterface\|setJavaScriptEnabled" -n jadx-out || true
  ```

- working dir:       any (it creates `apk-audit/`)
- env vars:          none
- secrets required:  no (but the APK itself may embed secrets — the
  audit's purpose is to surface them)
- success signal:    grep outputs are empty for the secret-scan
  lines
- failure signal:    matches found → real finding; or
  `apktool: command not found` / `jadx: command not found`
- Termux safe:       yes-with-caveats (`pkg install apktool aapt` —
  jadx needs JDK; on Termux it is fiddly)
- CI safe:           yes (with the tools installed)
- source:            `docs/orchestration/hermes-orchestration-pipeline.md:290-307`

---

## Wave D — Smoke & Integration Surfaces

### D.1 Slack manifest — stdout

- command:           `hermes slack manifest`
- working dir:       any
- env vars:          none required for generation (the manifest is
  built from `COMMAND_REGISTRY`)
- secrets required:  no (manifest only; bot/app tokens are needed
  separately to actually run a Slack bot)
- success signal:    exit 0; valid JSON written to stdout (`{`
  through `}` block; metadata, display_information, features,
  oauth_config, settings)
- failure signal:    non-zero exit; import errors from
  `hermes_cli.commands`
- Termux safe:       yes
- CI safe:           yes (read-only, no network)
- source:            `hermes_cli/slack_cli.py:106-159`

### D.2 Slack manifest — write to file

- command:           `hermes slack manifest --write` (default path
  `$HERMES_HOME/slack-manifest.json`), or
  `hermes slack manifest --write /path/to/manifest.json`
- working dir:       any
- env vars:          `HERMES_HOME` controls default path
- secrets required:  no
- success signal:    exit 0; `Slack manifest written to: <path>` on
  stderr; file present on disk
- failure signal:    non-zero exit; permission denied writing to
  target directory
- Termux safe:       yes
- CI safe:           no (writes outside the workspace by default
  unless `--write <path>` is supplied)
- source:            `hermes_cli/slack_cli.py:129-156`

### D.3 Slack manifest — slash-commands only

- command:           `hermes slack manifest --slashes-only`
- working dir:       any
- env vars:          none
- secrets required:  no
- success signal:    exit 0; JSON array of slash-command definitions
- failure signal:    non-zero exit
- Termux safe:       yes
- CI safe:           yes
- source:            `hermes_cli/slack_cli.py:120-123`

### D.4 Slack manifest — custom name / description

- command:           `hermes slack manifest --name "Hermes-Bot"
  --description "Your Hermes agent on Slack"`
- working dir:       any
- env vars:          none
- secrets required:  no
- success signal:    exit 0; manifest JSON contains the requested
  display name (truncated to 35 chars) and description (140 chars)
- failure signal:    non-zero exit
- Termux safe:       yes
- CI safe:           yes
- source:            `hermes_cli/slack_cli.py:115-119, 46-49`

### D.5 Slack smoke test — **NO DEDICATED SCRIPT IN REPO**

There is no `scripts/slack_smoke.py` or equivalent. The de-facto
smoke path is:

1. `hermes slack manifest` (D.1) — confirms generation succeeds.
2. `hermes doctor` (B.1) — surfaces missing `SLACK_BOT_TOKEN` /
   `SLACK_APP_TOKEN` (or whatever the user named them in their
   `.env`).
3. `hermes --once` against a configured Slack workspace — for an
   end-to-end round-trip, send a test message in DM to the bot and
   confirm a reply. This needs real credentials and is therefore
   owner-only / not CI-safe.

The PowerShell installer carries the only file currently named
`smoke` in this repo
(`scripts/tests/test-install-ps1-stage-protocol.ps1`), and that
covers the installer, not the Slack integration.

### D.6 Gateway smoke — start, probe, stop

- command:           three-step (Termux REPL or shell session):
  1. `hermes gateway` (foreground) — or `hermes gateway start`
     (background service install on Linux/macOS).
  2. `curl -sf http://127.0.0.1:8642/health` (B.12) — confirm
     `{"status":"ok"}`.
  3. `hermes gateway stop`.
- working dir:       any
- env vars:          gateway platform vars per `gateway/config.py`
  (Discord/Telegram/Slack bot tokens if the gateway is asked to
  connect those platforms — but `hermes gateway` with no platforms
  configured still binds the API server and answers `/health`)
- secrets required:  no for a bare API-server-only gateway; yes if
  attaching platforms
- success signal:    `/health` returns 200; `hermes gateway status`
  reports a live PID
- failure signal:    curl connection refused; PID file stale
- Termux safe:       yes (foreground; Termux has no systemd so
  `start`/`stop` fall back to a foreground supervisor)
- CI safe:           yes for the API-server-only variant; risky for
  full-platform variants because they hold long-lived sockets
- source:            `hermes_cli/main.py:8-13` (subcommand list);
  `hermes_cli/main.py:10508-10729` (subparser definitions);
  `gateway/platforms/api_server.py:58, 918-920, 3400`

### D.7 Discord voice doctor

- command:           `python scripts/discord-voice-doctor.py`
  (or `.venv/bin/python scripts/discord-voice-doctor.py`)
- working dir:       repo root (script self-adjusts via `SCRIPT_DIR`)
- env vars:          reads `DISCORD_BOT_TOKEN` if set, for
  permission probing; otherwise runs read-only checks
- secrets required:  no for dependency / config checks; yes for
  bot-permission probes
- success signal:    exit 0; "All dependency checks passed"
  (paraphrased — see script output)
- failure signal:    non-zero exit; missing `discord.py`, missing
  `libopus`, missing `ffmpeg`, or bot lacks voice permissions
- Termux safe:       yes-with-caveats (`pkg install ffmpeg`; libopus
  is shipped on Termux)
- CI safe:           yes (read-only checks; no real Discord
  connection required for the static parts)
- source:            `scripts/discord-voice-doctor.py:1-10`

### D.8 Hermes orchestrator smoke

- command:           four-line block:
  ```bash
  python -m py_compile hermes_cli/*.py || true
  bash -n scripts/hermes-orchestrate.sh
  scripts/hermes-orchestrate.sh --help
  scripts/hermes-orchestrate.sh "test orchestration job"
  ```
- working dir:       repo root
- env vars:          none
- secrets required:  no
- success signal:    `--help` prints; the test orchestration job
  emits `.hermes-orchestrator/jobs/...` files
- failure signal:    syntax errors in CLI files, bash parse errors,
  or job tree empty after the test run
- Termux safe:       yes (pure bash + Python)
- CI safe:           yes
- source:            `docs/orchestration/hermes-orchestration-pipeline.md:282-288`

---

## Wave E — Install & Termux Verification

### E.1 Hermes installer (Termux + Linux + macOS)

- command:           `bash scripts/install.sh` (or pipe-from-curl per
  the README, but local file is preferred for ACI work)
- working dir:       repo root (or anywhere; the script self-locates
  via `BASH_SOURCE`)
- env vars:          unsets `PYTHONPATH` and `PYTHONHOME` for the
  duration; sets `UV_NO_CONFIG=1`; reads
  `TERMUX_VERSION` / `PREFIX` for Termux detection
- secrets required:  no
- success signal:    exit 0; final message indicates `hermes` is on
  PATH; `hermes doctor` clean run succeeds afterwards
- failure signal:    non-zero exit; per-stage error messages
- Termux safe:       **yes** — this is the canonical Termux install
  path; switches to stdlib `venv + pip` on Termux instead of `uv`
- CI safe:           yes (no destructive operations; idempotent)
- source:            `scripts/install.sh:1-7, 16-33, 229-230, 254`
  (Termux detection and venv backend selection); install.sh full
  flow runs through to line 700+

### E.2 Termux package prerequisites

- command:           `pkg install clang rust make pkg-config libffi
  openssl ca-certificates curl` (and optionally `ripgrep`, `ffmpeg`)
- working dir:       any (Termux)
- env vars:          none
- secrets required:  no
- success signal:    `pkg install` exit 0; each package listed as
  installed
- failure signal:    `pkg install` non-zero; "stale mirrors" usually
  means `termux-change-repo` is needed
- Termux safe:       yes — Termux-only
- CI safe:           no (Termux-specific)
- source:            `scripts/install.sh:731-739`

### E.3 psutil-on-Termux patched install

- command:           `python scripts/install_psutil_android.py
  [--pip "/path/to/pip"] [--uv]`
- working dir:       repo root
- env vars:          none
- secrets required:  no
- success signal:    exit 0; `python -c "import psutil; print(psutil.__version__)"`
  succeeds afterwards
- failure signal:    non-zero exit; "platform android is not
  supported" if the patch did not apply
- Termux safe:       yes — purpose-built for Termux
- CI safe:           no (Termux-specific patch)
- source:            `scripts/install_psutil_android.py:1-22`

### E.4 AOS enterprise council pack install (post-install)

- command:           multi-step block, abbreviated:
  ```bash
  cd ~/hermes-agent
  git fetch origin <recovery-branch>
  git checkout <recovery-branch>
  mkdir -p ~/.hermes/skills
  cp -r ~/hermes-agent/skills/aos-enterprise-council ~/.hermes/skills/
  hermes skills list
  hermes doctor
  ```
- working dir:       `~/hermes-agent` for git steps; any for the
  rest
- env vars:          none (git uses ambient identity)
- secrets required:  no (assumes already-cloned repo)
- success signal:    `hermes skills list` shows
  `aos-enterprise-council`; `hermes doctor` exits 0
- failure signal:    skill not in list; doctor reports missing
  skill
- Termux safe:       yes
- CI safe:           yes
- source:            `AOS_INSTALLATION_REPORT.md:21-51`

### E.5 AOS activation rehearsal

- command:           `echo "/aos-enterprise-council audit this repo"
  | hermes --once 2>&1 | head -40`
- working dir:       repo root (or anywhere with valid HERMES_HOME)
- env vars:          provider creds (`OPENROUTER_API_KEY` or
  equivalent) — `hermes --once` makes a real LLM call
- secrets required:  yes — needs at least one provider API key set
- success signal:    Hermes prints the routing decision plus the
  council's todo list within the first 40 lines
- failure signal:    auth errors; missing skill error
- Termux safe:       yes
- CI safe:           no (requires real LLM credentials)
- source:            `AOS_INSTALLATION_REPORT.md:68-69`

### E.6 `hermes doctor` as universal post-install gate

See B.1. After any install step (E.1–E.5), running `hermes doctor`
and getting `0 issue(s)` is the contract that "the install
succeeded".

---

## Wave F — CI Reference Matrix

Which command runs in which `.github/workflows/*.yml` file:

| Workflow file | Workflow name | Commands |
| --- | --- | --- |
| `tests.yml` | Tests | A.2, A.3 |
| `lint.yml` | Lint (ruff + ty) | A.7, A.8, A.9, A.10, A.11 |
| `upload_to_pypi.yml` | Publish to PyPI | C.1, C.2, C.3, C.4, C.5, C.7 |
| `skills-index.yml` | Build Skills Index | C.8 |
| `osv-scanner.yml` | OSV-Scanner | (dependency CVE scan; out of scope here — no developer-facing command) |
| `supply-chain-audit.yml` | Supply Chain Audit | (CycloneDX + provenance; CI-only) |
| `uv-lockfile-check.yml` | uv.lock check | `uv lock --check` (no other manual command) |
| `nix.yml` | Nix | Nix flake build/check; not relevant for Termux work |
| `nix-lockfile-fix.yml` | Nix Lockfile Fix | Nix-specific autoupdate |
| `docs-site-checks.yml` | Docs Site Checks | website link/markdown checks |
| `history-check.yml` | History Check | git history hygiene |
| `contributor-check.yml` | Contributor Attribution Check | git author / CONTRIBUTORS hygiene |
| `docker-publish.yml` | Docker Build and Publish | (docker image; CI-only) |
| `deploy-site.yml` | Deploy Site | Vercel deploy (CI-only; owner-only per release rules) |

Notes:
- `tests.yml` and `lint.yml` are the two workflows whose failure
  blocks merge for ACI work. Everything else is advisory or
  produces an artifact.
- `upload_to_pypi.yml` only runs on CalVer tag push or manual
  `workflow_dispatch` — agents must not trigger it (owner-only).
- `osv-scanner.yml`, `supply-chain-audit.yml`,
  `uv-lockfile-check.yml`, `docker-publish.yml`, `deploy-site.yml`
  do not have a developer-facing single command exposed for local
  reproduction inside this inventory's scope. If a later wave needs
  to reproduce them locally, add the entry in that wave's report
  rather than here.

---

## Open Items for Later Waves

These were discovered during the inventory pass but are out of
scope for Wave 00 (which only documents existing commands):

1. **No Slack smoke script.** D.5 documents the gap. A later wave
   could add `scripts/slack_smoke.py` that posts a fixed message via
   the configured bot token and asserts an echo.
2. **Gateway port discovery.** B.12 hard-codes `8642` as
   `DEFAULT_PORT` from `api_server.py:58`. A later wave could expose
   the active port via `hermes gateway status` so smoke scripts
   don't need to assume the default.
3. **APK audit tooling.** C.10 lists commands but none are installed
   by default on Termux. A later wave could add a `pkg install`
   bootstrap inside `scripts/install.sh --with-apk-audit` (or
   similar).
4. **Integration test marker matrix.** A.4 lists modules but not
   the exact env-var contract per module. A later wave could
   formalize a `tests/integration/REQUIREMENTS.md`.

---

## Verification (this wave)

- `git diff --stat` — expect exactly one added file:
  `docs/aci/reports/W00_TEST_COMMAND_INVENTORY.md`
- `git status --short` — expect only the new file as untracked /
  staged
- Spot checks performed during authoring (read-only):
  - `hermes doctor` argparser inspection
    (`hermes_cli/main.py:11332-11350`)
  - `hermes slack manifest` argparser inspection
    (`hermes_cli/slack_cli.py:106-159`)
  - `gateway/status.py:1-100` and
    `gateway/platforms/api_server.py:918-941, 3400-3402` for health
    endpoints
  - `.github/workflows/tests.yml` and `lint.yml` full read for CI
    invocations

## Rollback

`rm docs/aci/reports/W00_TEST_COMMAND_INVENTORY.md` and
`rmdir docs/aci/reports docs/aci` (if no other files were added).
No source code, config, or workflow was changed; nothing else to
undo.

# W12 — Dependency & Supply-Chain Posture Review

**Wave:** 12 — Dependency Review (launch readiness)
**Branch:** `aci/wave-12-dependency-review`
**Scope:** Read-only audit. No dependency files were modified.
**Report owner:** Wave 12 builder
**Date:** 2026-05-26
**Commit at review:** see `git log -1` on this branch

---

## 1. Summary

Hermes ships with an unusually disciplined dependency posture. Every direct
Python dependency is exact-pinned (`==X.Y.Z`); `uv.lock` controls the entire
transitive graph; the Docker base images are pinned by SHA-256 digest;
Dependabot's source-ecosystem updaters are deliberately disabled to prevent
ranges from sneaking back in; and the 2026-05-12 mistralai supply-chain
incident has already been responded to in code (the extra was removed). The
JS side committed lockfiles at every site (`root`, `web/`, `ui-tui/`,
`ui-tui/packages/hermes-ink/`). No Android/Gradle module exists at this
commit — the Android attack surface is therefore *future work*, not a
current dependency.

**Launch verdict from the dependency perspective:** ready. The principal
residual risk is human error during pin-bump PRs, which is mitigated by
enforcing the **"dependency changes require a separate PR"** rule recorded
in §7 below.

---

## 2. Python Dependencies

### 2.1 Pinning strategy

100 % exact pinning on direct deps. Representative lines from
`pyproject.toml` `[project] dependencies`:

```toml
"openai==2.24.0",
"httpx[socks]==0.28.1",
"pydantic==2.12.5",
"requests==2.33.0",        # CVE-2026-25645
"PyJWT[crypto]==2.12.1",   # CVE-2026-32597
"psutil==7.2.2",
```

The file carries an inline policy statement (`pyproject.toml` lines 14-28)
that codifies the rule: *"every direct dep is exact-pinned to ==X.Y.Z (no
ranges)"*. Rationale given: the Mini Shai-Hulud worm hitting `mistralai
2.4.6` on 2026-05-12 — a range like `mistralai>=2.3.0,<3` would have caught
it; exact pins did not. Per the same comment block, **new ranges may not be
introduced without a written justification**.

Two narrow exceptions are permitted by the pinning policy and visible in
the file:

- `tzdata==2025.3; sys_platform == 'win32'` — platform marker, not a range.
- `setuptools>=61.0` in `[build-system].requires` — build-time only, not a
  runtime pin.

### 2.2 Lock files

- **`uv.lock`** — committed. Source of truth for transitive resolution.
- **`uv sync --frozen --no-install-project --extra all --extra messaging`**
  is invoked from the Dockerfile, guaranteeing the container build cannot
  drift from the lock.
- **`.github/workflows/uv-lockfile-check.yml`** runs drift detection on CI
  so a `pyproject.toml` change without a matching `uv.lock` regen will
  fail the PR.

### 2.3 Optional extras — exact vs ranged, risk class

Every extra is also exact-pinned. Inventory (from
`[project.optional-dependencies]`):

| Extra | What it pulls | External surface | Risk class |
|---|---|---|---|
| `anthropic` | `anthropic==0.86.0` | Anthropic API | external-service |
| `exa` | `exa-py==2.10.2` | Exa search | external-service |
| `firecrawl` | `firecrawl-py==4.17.0` | Firecrawl | external-service |
| `parallel-web` | `parallel-web==0.4.2` | Parallel | external-service |
| `fal` | `fal-client==0.13.1` | fal.ai image gen | external-service |
| `edge-tts` | `edge-tts==7.2.7` | Microsoft TTS | external-service |
| `modal` | `modal==1.3.4` | Modal compute | external-service |
| `daytona` | `daytona==0.155.0` | Daytona | external-service |
| `vercel` | `vercel==0.5.7` | Vercel | external-service |
| `hindsight` | `hindsight-client==0.6.1` | Hindsight memory | external-service |
| `dev` | `pytest`, `pytest-asyncio/xdist/split/timeout`, `ruff`, `ty`, `debugpy`, `mcp` (all pinned) | local | low |
| `messaging` | `python-telegram-bot[webhooks]==22.6`, `discord.py[voice]==2.7.1`, `aiohttp==3.13.3`, `brotlicffi==1.2.0.1`, `slack-bolt/slack-sdk`, `qrcode` | multiple platforms | external-service + native (`brotlicffi`, voice codecs) |
| `slack` | `slack-bolt==1.27.0`, `slack-sdk==3.40.1`, `aiohttp==3.13.3` | Slack | external-service |
| `matrix` | `mautrix[encryption]==0.21.0`, `Markdown==3.10.2`, `aiosqlite==0.22.1`, `asyncpg==0.31.0`, `aiohttp-socks==0.11.0` | Matrix homeservers | **native-build** (`python-olm` Linux-only wheels — file comments note Windows/macOS will fail) |
| `cli` | `simple-term-menu==1.6.6` | local | low |
| `tts-premium` | `elevenlabs==1.59.0` | ElevenLabs | external-service |
| `voice` | (faster-whisper et al — see lines 90-96) | local + models | native-build |
| `pty` | terminal PTY libs (lines 97-100) | local | native-build |
| `honcho` | `honcho-ai==2.0.1` | Honcho memory | external-service |
| `mcp` | `mcp==1.26.0` | MCP servers | external-service |
| `homeassistant`, `sms` | `aiohttp==3.13.3` | local HA / SMS bridges | external-service |
| `computer-use` | `mcp==1.26.0` | local | low |
| `acp` | `agent-client-protocol==0.9.0` | local | low |
| `bedrock` | `boto3==1.42.89` | AWS | external-service |
| `azure-identity` | `azure-identity==1.25.3` | Azure | external-service |
| `dingtalk` | `dingtalk-stream==0.24.3`, `alibabacloud-dingtalk==2.2.42`, `qrcode==7.4.2` | DingTalk | external-service |
| `feishu` | `lark-oapi==1.5.3`, `qrcode==7.4.2` | Feishu | external-service |
| `google` | `google-api-python-client==2.194.0`, `google-auth-oauthlib==1.3.1`, `google-auth-httplib2==0.3.1` | Google Workspace | external-service |
| `youtube` | `youtube-transcript-api==1.2.4` | YouTube | external-service |
| `web` | `fastapi==0.133.1`, `uvicorn[standard]==0.41.0` | local HTTP surface | low |
| `termux` | re-exports `cron`, `cli`, `pty`, `mcp`, `honcho`, `acp` + Telegram | Termux/Android | **see §2.4** |
| `termux-all` | re-exports `termux`, `google`, `homeassistant`, `sms`, `web` | Termux/Android | **see §2.4** |
| `all` | re-exports `cron`, `cli`, `dev`, `pty`, `mcp`, `homeassistant`, `sms`, `acp`, `google`, `web`, `youtube` | curated, OS-portable | low |

**Two git dependencies — explicitly excluded from `[all]`:** the policy
comment at `pyproject.toml` lines ~170-185 notes that `rl` and `yc-bench`
extras pull from git (e.g. `atroposlib`, `tinker`, `torch`, `wandb`).
These are research-only and must never enter the production `[all]`
extra. Honor that.

**Lazy-install:** `tools/lazy_deps.py` opt-in pulls platform backends at
first use rather than baking them into the container image. The policy
note in `[all]` (lines 170-204) is explicit: an extra that lazy-loads
**must** be removed from `[all]` so a quarantined PyPI release of any one
provider cannot brick `uv sync --locked` for everyone.

### 2.4 Termux / Android incompatibility surface

Termux is the only Android packaging path that exists today. The repo
maintains:

- A **`[termux]` extra** with the minimum eager set
  (`python-telegram-bot[webhooks]==22.6`, `cron`, `cli`, `pty`, `mcp`,
  `honcho`, `acp`) and a **`[termux-all]` extra** that layers `google`,
  `homeassistant`, `sms`, `web` on top.
- A **`constraints-termux.txt`** companion file that pins:
  ```
  ipython<10
  jedi>=0.18.1,<0.20
  parso>=0.8.4,<0.9
  stack-data>=0.6,<0.7
  pexpect>4.3,<5
  matplotlib-inline>=0.1.7,<0.2
  asttokens>=2.1,<3
  ```
  Documented install path: `python -m pip install -e '.[termux]' -c
  constraints-termux.txt`. These constraints absorb the gap between modern
  PyPI releases and the Termux wheel set; without them, IPython/jedi/parso
  upgrades break the Android install path.

**Packages that historically broke on Termux/Android and are kept out of
the eager Android profile:**

- `python-olm` (transitive of `mautrix[encryption]` via the `matrix`
  extra) — Linux-only wheels, no Termux path. **Not in `[termux*]`.**
- `python-olm`, `faster-whisper` (`voice` extra), `discord.py[voice]`
  (PyNaCl + libsodium) — native builds that don't cross to Android
  cleanly. **Not in `[termux*]`.**
- Anything pulling `numpy` / `torch` / `tokenizers` from the `rl` /
  `yc-bench` git extras — Android wheels not published.

**Native-extension packages that *are* in the core set and do work on
Termux** (because Termux ships wheels or aarch64 builds exist):

- `cryptography` (transitive of `PyJWT[crypto]==2.12.1`) — Rust wheel
  available on Termux.
- `pyyaml==6.0.3` — C-accelerated, Termux ships wheel.
- `psutil==7.2.2` — C, Termux ships wheel.
- `brotlicffi` (via `messaging`) — C, works under Termux but `messaging`
  is **not** in `[termux*]`, so this is moot for that profile.

If a future change adds a Rust- or C-extension dependency to the core
list, it must be validated against Termux explicitly before merging.

---

## 3. Android Dependencies

**No Gradle / Android module exists at this commit.** A repo-wide scan
for `build.gradle`, `build.gradle.kts`, `settings.gradle*`,
`gradle.properties`, and `libs.versions.toml` returned zero matches.
Android availability today is solely via **Termux** — covered in §2.4 —
not a native Android app.

### Forward-looking requirement (sets expectation for later waves)

If a later wave introduces an Android Studio module, F-Droid build, or
APK packaging, the following posture must arrive **in the same wave**, in
a single dep-only PR (per §7):

- A `libs.versions.toml` version catalog with **exact** versions; ranges
  banned, same policy as Python.
- Gradle dependency-lock files (`gradle.lockfile`) committed for every
  configuration that resolves dependencies.
- Dependabot ecosystem `gradle` enabled in `.github/dependabot.yml`
  **only** if it does not violate the no-source-ecosystem rule the repo
  currently enforces — likelier outcome: leave Dependabot off and rely on
  CVE-driven security-update PRs plus CI scanning (mirrors the Python
  posture).
- OSV-Scanner extended over `gradle.lockfile`.
- SBOM (CycloneDX) emitted for the Android artifact in CI.
- Reproducible builds: `--no-daemon`, fixed JDK, `org.gradle.caching=true`,
  Kotlin compiler bumps go through a dep-only PR.
- Signing keys in Actions Secrets (never in the repo), with the
  pre-launch DO-NOT list in the wave header still in force.
- Code-signing posture documented before the first store/F-Droid upload.

Until that wave lands, **Android dependencies = nil**, and the only
launch-blocking Android question is whether the Termux install path
works against the current `[termux-all]` extra + `constraints-termux.txt`
combination. That smoke test belongs to QA, not this report.

---

## 4. JS / Node Dependencies

### 4.1 Locations

- `package.json` + `package-lock.json` at repo root
- `web/package.json` + `web/package-lock.json` (Hermes dashboard SPA)
- `ui-tui/package.json` + `ui-tui/package-lock.json`
- `ui-tui/packages/hermes-ink/package.json` (workspace)

Every site has a committed lockfile. The Dockerfile invokes
`npm install --prefer-offline --no-audit` against the root lockfile,
relying on the lockfile for reproducibility rather than the network at
build time.

### 4.2 Risk and controls

- **Transitive blast radius:** the npm tree is broad by nature. Defense
  is `package-lock.json` plus CI OSV scanning
  (`.github/workflows/osv-scanner.yml`) which covers npm lockfiles.
- **`--no-audit` rationale:** audit runs in CI, not at image build, to
  keep build deterministic and offline-tolerant. Don't remove
  `--no-audit` from the Dockerfile without re-thinking the build's
  network assumptions.
- **No `npm ci` in Docker:** `npm install` is used because the runtime
  user (`hermes`) needs a writable `node_modules` for runtime
  `_tui_need_npm_install()` flow noted in the Dockerfile comments.
  Changing this is a Wave-13+ topic, not a casual edit.
- **Range tolerance:** unlike Python's strict `==`, JS package.json
  files routinely carry `^` / `~` ranges; the lockfile is what locks
  resolution. **Never delete a `package-lock.json`** — it is the only
  thing standing between us and resolver drift.

---

## 5. Container & Nix

### 5.1 Dockerfile base-image pinning

```dockerfile
FROM ghcr.io/astral-sh/uv:0.11.6-python3.13-trixie@sha256:b3c543b6c4f23a5f2df22866bd7857e5d304b67a564f4feab6ac22044dde719b AS uv_source
FROM tianon/gosu:1.19-trixie@sha256:3b176695959c71e123eb390d427efc665eeb561b1540e82679c15e992006b8b9 AS gosu_source
FROM debian:13.4
```

Two of three FROM lines pin by **SHA-256 digest**, not by tag — that's the
strict form. `debian:13.4` is tag-only; promoting it to a digest pin is a
recommended hardening in §8.

### 5.2 Nix flake

- `flake.nix` + `flake.lock` are committed.
- Uses `uv2nix` + `pyproject-nix` + `pyproject-build-systems` —
  `pyproject.toml` is the single source of truth; Nix consumes it.
- **`.github/workflows/nix-lockfile-fix.yml`** keeps `flake.lock`
  coherent with `pyproject.toml`/`uv.lock` movement.
- **`.github/workflows/nix.yml`** runs the Nix build path on PRs.

---

## 6. Supply-Chain Controls Already In Place

CI workflows present under `.github/workflows/` (read-only confirmation —
file contents not opened in this wave):

| Workflow | Role |
|---|---|
| `osv-scanner.yml` | OSV vulnerability scanning across lockfiles |
| `supply-chain-audit.yml` | Repo-wide supply-chain audit |
| `uv-lockfile-check.yml` | `uv.lock` drift detection on PRs |
| `nix-lockfile-fix.yml` | `flake.lock` drift detection |
| `nix.yml` | Nix build validation |
| `docker-publish.yml` | Container publish (gates Docker image) |
| `tests.yml`, `lint.yml` | Functional gates |
| `contributor-check.yml`, `history-check.yml` | Identity / hygiene |
| `upload_to_pypi.yml` | PyPI release path |
| `docs-site-checks.yml`, `deploy-site.yml`, `skills-index.yml` | Docs/skills |

**Dependabot** (`.github/dependabot.yml`):

- Enabled **only** for `github-actions`. Comment block at top of the file
  states the rationale verbatim: *"We do NOT enable Dependabot for pip /
  npm / any source-dependency ecosystem because we pin source
  dependencies exactly … Automatic version-bump PRs against those pins
  would undermine the strategy — pins are moved deliberately, after
  review, not on a schedule."*
- Action pins use **full commit SHAs** (per supply-chain policy).
- Repo-level Dependabot **security-update** PRs (CVE-driven, not
  schedule-driven) handle CVE fan-out separately, per the file's
  comments.

**Already-evidenced incident response:** `pyproject.toml` records the
2026-05-12 removal of the `mistral` extra following the Mini Shai-Hulud
PyPI worm. Treat this as the repo's working precedent for how to react to
a future PyPI-side incident: remove or repin in a dedicated PR, regen
locks, push.

---

## 7. Update Policy / What Must Not Be Changed Casually

### 7.1 Hard rule — dependency changes require a separate PR

> **Any change to `pyproject.toml`, `uv.lock`, `constraints-termux.txt`,
> `package.json`, `package-lock.json` (at any path), `flake.nix`,
> `flake.lock`, `Dockerfile` base-image digests/tags, or
> `.github/dependabot.yml` MUST land in a dedicated PR that touches no
> source code, no docs, no workflows, and no other configuration. The
> reviewer of record signs off on supply-chain risk, not feature scope.**

This rule exists because:

- Bundled PRs hide dep movement behind unrelated diffs.
- Reverting a bad pin must not require reverting unrelated features.
- A dep-only PR is small enough to actually read every changed line.

### 7.2 Pin-move discipline

- Move a pin only for: a published CVE on the current version, a
  reproducible upstream bug blocking a user, or deliberate compatibility
  work (e.g., Python version bump).
- Never batch pin moves with feature changes.
- Always regenerate locks (`uv lock`, the relevant
  `npm install`/`package-lock.json` regen, `nix flake update` only for
  the affected input) in the same PR.
- CI lockfile checks must be green before merge.
- For any first-time addition of a package, evaluate Termux availability
  (§2.4) and platform wheels (Linux x86_64, Linux aarch64, macOS,
  Windows) before merge.

### 7.3 Forbidden without explicit reviewer sign-off

- Removing exact pins or swapping `==` for `>=,<` ranges in
  `pyproject.toml`.
- Enabling Dependabot for `pip` or `npm` ecosystems in
  `.github/dependabot.yml`.
- Deleting any committed lockfile (`uv.lock`, any `package-lock.json`,
  `flake.lock`).
- Replacing a digest-pinned Docker `FROM` with a tag-only `FROM`.
- Introducing a new git-dep (`pip install
  git+https://...`) without recording it next to the existing
  precedent (`rl`, `yc-bench`) and **keeping it out of `[all]`**.
- Running `pip install --upgrade` against a running container without
  regenerating `uv.lock` afterward and committing the result.
- Re-introducing the `mistral` extra without first checking the latest
  PyPI release status and updating the inline policy comment in
  `pyproject.toml`.

---

## 8. Recommended CI Checks (Gap Analysis — Not Implemented This Wave)

The current controls (§6) are strong; the gaps below are hardening, not
remediation. **Each one of these is a separate later-wave PR** — do not
bundle.

1. **SBOM emission per release.** Generate CycloneDX (or SPDX) for both
   the Python wheel and the Docker image on each tag. Confirm whether
   `supply-chain-audit.yml` already covers; if not, add a step using
   `cyclonedx-py` (Python) and `syft` (image).
2. **Sigstore / cosign signing of the published container image.**
   `docker-publish.yml` should sign with `cosign --keyless` and publish
   the attestation. Verification step in `docker-publish.yml` post-push.
3. **`pip-audit --strict` against the frozen `uv.lock`** as a
   belt-and-braces alongside OSV-Scanner (different vuln databases).
4. **`npm audit --omit=dev` against each lockfile**, informational
   (non-blocking) so it doesn't break PRs but does surface advisories
   that OSV missed.
5. **License inventory pass** (e.g. `pip-licenses`, `license-checker`
   for npm) emitted as a job artifact per release. Useful for the
   eventual third-party-notices doc.
6. **PR-level "dep-only PR" enforcement.** Add a CODEOWNERS / labeler
   rule that auto-tags any PR touching the protected files in §7.1 and
   requires a dep-reviewer approval. Optionally, a check that blocks the
   PR if the diff touches both protected files *and* non-protected files
   in the same PR.
7. **Promote `debian:13.4` `FROM` to a digest pin.** Mechanical change;
   needs a dep-only PR per §7.1.
8. **OSV-Scanner over the Nix flake closure** if not already in
   `osv-scanner.yml` — Nix doesn't go through PyPI/npm so it's a
   separate scan path.
9. **Reproducibility check:** rebuild the published image from the same
   commit in CI and diff the layer digests. Surfaces non-deterministic
   build steps.
10. **Termux smoke test in CI** (containerized aarch64 with Termux's
    base image) running `pip install -e '.[termux-all]' -c
    constraints-termux.txt` against every PR that touches
    `pyproject.toml` or `constraints-termux.txt`.

---

## 9. Open Items / Things Discovered That Need Other Waves

Per the wave non-overlap contract, anything below was **not edited** in
this wave. Each is a candidate work item for a future wave's dep-only PR.

1. **`debian:13.4` FROM not digest-pinned** in `Dockerfile`. Hardening,
   not remediation — see §8 item 7.
2. **No explicit license inventory artifact** in CI — see §8 item 5.
3. **No SBOM artifact attached to releases** unless
   `supply-chain-audit.yml` covers it (file not opened this wave) —
   see §8 item 1.
4. **No CODEOWNERS / labeler rule** enforcing the §7.1 dep-only-PR rule
   procedurally — today it's a documented contract, not a tooling
   gate.
5. **No Termux smoke test in CI** — manual install path, regressions
   only caught at user-report time.

None of the above is a launch blocker on its own; together they
represent the next slice of supply-chain maturation after launch.

---

## Wave Report Footer

**Changed files:**
- `docs/aci/reports/W12_DEPENDENCY_SUPPLY_CHAIN_REVIEW.md` (this file, new)

**Tests run:** None. This wave is documentation-only; no code paths
were touched. `git diff --stat` against the wave base shows exactly one
added file; no dependency manifest, lockfile, source file, workflow, or
Dockerfile was modified.

**Remaining risks:**
- Human-error on future pin moves (mitigated by the §7.1 dep-only-PR
  rule, which still depends on reviewer vigilance, not tooling).
- §9 open items (none launch-blocking).

**Rollback plan:** delete
`docs/aci/reports/W12_DEPENDENCY_SUPPLY_CHAIN_REVIEW.md`, close the draft
PR, delete the `aci/wave-12-dependency-review` branch. No other repo
state is touched, so rollback is a no-op for everything else.

**PR summary:**

> ACI Wave 12 — Dependency & Supply-Chain Posture Review (read-only).
> Documents Python exact-pinning posture, `uv.lock` strategy, optional
> extras risk classes, Termux-incompatible packages, JS/Node lockfile
> coverage, Dockerfile digest pinning, Nix flake, existing CI controls
> (`osv-scanner`, `supply-chain-audit`, `uv-lockfile-check`,
> `nix-lockfile-fix`, Dependabot scoped to `github-actions` only),
> dep-only-PR update rule, recommended next-wave CI checks, and open
> items. **No dependency files were modified.** Draft PR.

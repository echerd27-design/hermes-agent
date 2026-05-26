# Wave 13 — ACI Product Workspace Schema

## Wave

Wave 13 / Workspace Schema. First ACI wave to land under
`hermes_cli/jarvis_prime/`.

## Branch

`aci/wave-13-workspace-schema` — created off `origin/main` at
`7b82077`. Draft PR only; no merge to main.

## Changed files

Only the four ALLOWED FILES listed in the wave brief were touched:

- `hermes_cli/jarvis_prime/workspaces.py` — new module.
- `hermes_cli/jarvis_prime/__init__.py` — new package init that
  re-exports the public surface.
- `tests/test_jarvis_prime_workspaces.py` — 42 stdlib-only pytest cases
  covering registry, validation, serialization, derivation, and a
  stdlib-only import guard.
- `docs/aci/reports/W13_WORKSPACE_SCHEMA.md` — this report. The
  `docs/aci/reports/` directory was created as part of this wave.

No other file was modified. `git diff --name-only origin/main...HEAD`
will show exactly those four paths.

## Schema

`Workspace` is a `@dataclass(frozen=True)` record with twelve fields.
Collection-shaped fields are tuples so the record is hashable and safe
to share across threads; `to_dict` converts them to lists for JSON.

| Field | Type | Notes |
| --- | --- | --- |
| `workspace_id` | `str` | Lowercase slug, `^[a-z0-9][a-z0-9-]*$`. |
| `product_name` | `str` | Human-readable product name; required. |
| `repo_full_name` | `Optional[str]` | `"owner/repo"` or `None`. |
| `product_brief` | `str` | One- or two-sentence product framing. |
| `default_branch` | `str` | Defaults to `"main"`. |
| `build_commands` | `tuple[str, ...]` | May be empty. |
| `test_commands` | `tuple[str, ...]` | May be empty. |
| `deploy_commands` | `tuple[str, ...]` | May be empty. |
| `risk_rules` | `tuple[str, ...]` | Imperative guardrails JARVIS must respect. |
| `specialists` | `tuple[str, ...]` | Default specialist bench. |
| `memory_namespace` | `str` | Namespace under `aci/`. Required. |
| `release_checklist` | `tuple[str, ...]` | Imperative release gates. |

Public helpers:

- `list_workspace_templates() -> tuple[str, ...]` — sorted ids.
- `get_workspace_template(workspace_id) -> Workspace` — `KeyError`
  with valid ids on miss.
- `create_workspace_from_template(workspace_id, **overrides) -> Workspace` —
  derives a customized workspace via `dataclasses.replace`; built-in
  template is never mutated.
- `Workspace.to_dict()` / `Workspace.from_dict()` — JSON-safe
  serialization. `from_dict` ignores unknown keys for
  forward-compatibility and raises `ValueError` on missing required
  fields.

## Templates

Five built-in templates, all on `default_branch = "main"` and namespaced
under `aci/<workspace_id>`:

- **Nourish** — personalized nutrition guidance; risk rules enforce no
  medical claims, no diagnosis or treatment language.
- **HazMat Command** — shipping paper OCR audit + correction trail;
  risk rules preserve the audit log and reviewer identity on every
  correction.
- **Hey Jay** — voice-first low-clearance assistant for truck drivers;
  risk rules forbid suppressing low-clearance warnings or proposing
  routes that ignore truck restrictions.
- **Hermes Core** — the Hermes agent runtime itself
  (`echerd27-design/hermes-agent`); pins `scripts/run_tests.sh` as the
  canonical test command and `python -m compileall hermes_cli` as the
  build check.
- **ACI Internal** — wave reports, planning artifacts, and the
  cross-product registry; risk rules keep production data and customer
  PII out of fixtures and reports.

## Tests run

Verification before the draft PR:

- `python -m compileall hermes_cli/jarvis_prime/workspaces.py` → exit 0.
- `pytest tests/test_jarvis_prime_workspaces.py -q -o addopts=""` →
  42 passed in ~1.5s.
- `python -c "from hermes_cli.jarvis_prime import ...; print(list_workspace_templates())"`
  prints `('aci-internal', 'hazmat-command', 'hermes-core', 'hey-jay',
  'nourish')`.

The repo's canonical runner `scripts/run_tests.sh` needs the project
venv (with `pytest-xdist` + `pytest-timeout`); in this remote container
that venv is not provisioned, so the bare-`pytest` invocation above
mirrors what the canonical runner would do for this single file and
matches the VERIFY block in the wave brief.

## Remaining risks

- Schema is frozen-in-code: a future field addition needs a coordinated
  bump because `from_dict` only ignores *unknown* keys, not new
  required ones. Mitigation: keep new fields optional with sensible
  defaults until the next major wave.
- No CLI surface yet — adding `hermes workspace list/show` would touch
  `hermes_cli/commands.py`, which is outside this wave's allowed files.
- No persistence yet — workspaces live only in code. Persistence
  (`~/.hermes/workspaces.json` or similar) is deferred to a later wave.
- Templates' `build_commands` / `test_commands` / `deploy_commands` are
  intentionally minimal or empty for the non-Hermes products since
  their toolchains are not yet committed to this repo. Those tuples
  will tighten in later waves once the corresponding repos are wired.

## Rollback

Delete `hermes_cli/jarvis_prime/` and the new test + report files:

```
rm -r hermes_cli/jarvis_prime/
rm tests/test_jarvis_prime_workspaces.py
rm docs/aci/reports/W13_WORKSPACE_SCHEMA.md
rmdir docs/aci/reports docs/aci 2>/dev/null || true
```

Nothing outside the package depends on it, so removal is a no-op for
the rest of the codebase.

## PR summary

Draft PR opened against `main`. The PR body summarizes:

- Adds the ACI product workspace schema (`Workspace` dataclass +
  serialization helpers) at `hermes_cli/jarvis_prime/workspaces.py`.
- Ships five built-in templates: Nourish, HazMat Command, Hey Jay,
  Hermes Core, ACI Internal.
- 42 stdlib-only pytest cases.
- Stdlib-only module; no external calls, no new dependencies, no edits
  to `pyproject.toml`, `uv.lock`, `README.md`, or any CI/gateway file.
- Draft only; not for merge.

## Out-of-scope items discovered

Per the non-overlap contract, any change that would have required
editing files outside ALLOWED FILES is recorded here instead of being
made:

- **CLI subcommand surface** — a `hermes workspace list/show` UX would
  be useful but needs `hermes_cli/commands.py` and `hermes_cli/main.py`
  edits. Deferred to a follow-up wave.
- **Toolset / plugin registration** — exposing workspaces to the
  Hermes agent loop would need `hermes_cli/toolsets.py` or a plugin
  hook. Deferred.
- **Persistence layer** — reading/writing user-defined workspaces under
  `HERMES_HOME` would need `hermes_constants` integration. Deferred.
- **Wider product docs** — `docs/jarvis-prime-operating-system.md`
  could grow a "workspace registry" section pointing at this module;
  not edited because product docs sit outside this wave's scope.

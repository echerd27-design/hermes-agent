# W05 — Build Packet Schema

## Wave summary

Wave 05 introduces `hermes_cli/jarvis_prime/build_packets.py`, a strict,
stdlib-only Python schema for briefing JARVIS Prime worker tasks
(Claude Code Builder, Codex Reviewer, Codex Bounded Fix Worker, Local
Test Runner). Before this wave, briefs to those workers were
improvised: every handoff re-derived mission, allowed files, forbidden
files, and acceptance criteria from prose. That improvisation was the
most common source of non-overlap violations (a builder edited a
forbidden file) and silent acceptance drift (a builder declared done
without meeting criteria).

The `BuildPacket` schema, the `Worker` enum, and the `BuildPacketError`
exception now sit in a new `hermes_cli/jarvis_prime/` subpackage. The
schema supports `to_dict` / `from_dict` for persistence and transport,
`validate()` for strict pre-dispatch checks, and `to_markdown()` for a
prompt-ready packet the operator can paste directly into a worker
session. This is the typed foundation that later waves
(dispatcher into `kanban_swarm`, packet-from-intent generation,
kanban integration) will build on.

## Scope

**In scope (this wave):**

- Stdlib-only `BuildPacket` dataclass and `Worker` enum.
- `validate()`: required-field and allowed/forbidden overlap checks.
- `to_dict()` / `from_dict()`: strict on type mismatches, lenient on
  unknown keys.
- `to_markdown()`: prompt-ready packet with a fixed section order and
  `(none)` placeholders for empty optional sections.
- pytest coverage including missing-required-field and
  forbidden-overlap-detection tests.

**Out of scope (deferred to later waves):**

- Persistence (no kanban / sqlite hookup).
- Dispatch (no execution of packets — just the contract).
- Packet generation from natural-language intent.
- Secret-pattern scan over `allowed_files`.
- Length-budget enforcement on `mission` / `rollback_plan`.
- Integration with the universal-header preamble (callers compose).

## Schema reference

### `BuildPacket` fields

| field                 | type        | required (non-empty)? | notes |
|-----------------------|-------------|-----------------------|-------|
| `mission`             | `str`       | yes                   | one-sentence statement of intent |
| `repo_root`           | `str`       | yes                   | absolute path the worker should treat as root |
| `branch`              | `str`       | yes                   | wave branch the worker may push to |
| `worker`              | `Worker`    | yes                   | see enum table below |
| `allowed_files`       | `list[str]` | yes (≥1)              | safety contract — non-overlap protection |
| `acceptance_criteria` | `list[str]` | yes (≥1)              | definition of done |
| `verification_commands` | `list[str]` | yes (≥1)            | renders as a fenced code block; required so every brief carries a falsifiable verify step |
| `rollback_plan`       | `str`       | yes                   | required so every brief carries an undo path; renders as `(none specified)` only in `validate=False` previews |
| `forbidden_files`     | `list[str]` | no                    | glob patterns supported; `**` normalized to `*` |
| `non_goals`           | `list[str]` | no                    | explicit anti-scope statements |
| `owner_gated_actions` | `list[str]` | no                    | actions that require explicit authorization |

### `Worker` enum

The four enum values mirror the Worker list in
`docs/jarvis-prime-operating-system.md`:

| enum                          | value                  | role |
|-------------------------------|------------------------|------|
| `Worker.CLAUDE_CODE_BUILDER`  | `claude_code_builder`  | primary builder |
| `Worker.CODEX_REVIEWER`       | `codex_reviewer`       | reviewer / second-pass engineer |
| `Worker.CODEX_BOUNDED_FIX`    | `codex_bounded_fix`    | scoped fix worker |
| `Worker.LOCAL_TEST_RUNNER`    | `local_test_runner`    | local verification runner |

The enum subclasses `str`, so instances serialize transparently
through `json.dumps` and accept string round-trip via `Worker(value)`.

## Design decisions

1. **Validation lives in a separate `validate()` method, not in
   `__post_init__`.** Rationale: `from_dict` needs to support draft
   packets (partial, edited in flight). Validation happens at the
   gates the operator owns — explicitly via `validate()`, and
   implicitly inside `to_markdown()` so a malformed brief never
   reaches a worker.

2. **`Worker` is a `str`-mixed `Enum`.** JSON-roundtrips natively
   (the `str` base means `json.dumps(worker)` emits the value
   directly), supports `Worker("claude_code_builder")` coercion, and
   keeps runtime introspection (`list(Worker)`). `Literal` would
   lose introspection; a plain `Enum` would force `.value` coercion
   in every serializer.

3. **Allowed/forbidden overlap detection is glob-aware by default
   with an opt-out toggle.** `validate(strict_globs=True)` (default)
   uses bidirectional `fnmatch` so a literal path on either side
   conflicts with a matching glob on the other; `**` is normalized
   to `*` before `fnmatchcase`, because `fnmatch` has no native
   recursive-glob support. `validate(strict_globs=False)` falls back
   to a pure literal-string set intersection — useful when entries
   are already concrete paths and glob semantics would generate
   noise. The toggle is forwarded by `to_markdown(strict_globs=…)`.
   This is a documented approximation; callers needing full
   `pathspec`/`.gitignore` semantics should normalize first.

4. **Required-non-empty fields are `mission`, `repo_root`, `branch`,
   `worker`, `allowed_files`, `acceptance_criteria`,
   `verification_commands`, and `rollback_plan`.** This is the
   "maximal" interpretation: every dispatched packet carries a
   stated mission, the routing fields, the non-overlap contract
   (`allowed_files`), the definition-of-done
   (`acceptance_criteria`), at least one falsifiable verify command
   (`verification_commands`), and an undo path (`rollback_plan`).
   The three remaining fields (`forbidden_files`, `non_goals`,
   `owner_gated_actions`) are optional and render `(none)`
   placeholders when empty.

5. **Markdown structure is fixed and section order is stable.** The
   layout mirrors the universal-header style: Mission → Worker →
   Repo (Root/Branch) → Allowed Files → Forbidden Files → Non-Goals
   → Acceptance Criteria (rendered as `- [ ]` checkboxes) →
   Verification Commands (fenced code block) → Rollback Plan →
   Owner-Gated Actions. Empty optional sections render `(none)` so
   the field is visibly considered, not silently absent.

6. **`from_dict` is lenient on unknown keys and strict on type
   mismatches.** Unknown keys are silently dropped so future schema
   additions do not break old persisted packets; wrong types
   (`allowed_files` as a string, `worker` as an unknown value, etc.)
   raise `BuildPacketError` with a specific message. `from_dict`
   intentionally does *not* call `validate()` so draft packets can
   be deserialized and edited.

## Verification evidence

### pytest

```
$ pytest tests/test_jarvis_prime_build_packets.py
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-9.0.3
configfile: pyproject.toml
collected 42 items

tests/test_jarvis_prime_build_packets.py::TestWorkerEnum::test_enum_values_match_operating_doc PASSED
tests/test_jarvis_prime_build_packets.py::TestWorkerEnum::test_worker_constructable_from_string PASSED
tests/test_jarvis_prime_build_packets.py::TestWorkerEnum::test_worker_rejects_unknown_value PASSED
tests/test_jarvis_prime_build_packets.py::TestBuildPacketValidation::test_minimal_valid_packet_validates PASSED
tests/test_jarvis_prime_build_packets.py::TestBuildPacketValidation::test_missing_mission_raises PASSED
tests/test_jarvis_prime_build_packets.py::TestBuildPacketValidation::test_blank_mission_raises PASSED
tests/test_jarvis_prime_build_packets.py::TestBuildPacketValidation::test_missing_repo_root_raises PASSED
tests/test_jarvis_prime_build_packets.py::TestBuildPacketValidation::test_missing_branch_raises PASSED
tests/test_jarvis_prime_build_packets.py::TestBuildPacketValidation::test_empty_allowed_files_raises PASSED
tests/test_jarvis_prime_build_packets.py::TestBuildPacketValidation::test_allowed_files_with_only_blanks_raises PASSED
tests/test_jarvis_prime_build_packets.py::TestBuildPacketValidation::test_empty_acceptance_criteria_raises PASSED
tests/test_jarvis_prime_build_packets.py::TestBuildPacketValidation::test_empty_verification_commands_raises PASSED
tests/test_jarvis_prime_build_packets.py::TestBuildPacketValidation::test_empty_rollback_plan_raises PASSED
tests/test_jarvis_prime_build_packets.py::TestBuildPacketValidation::test_blank_rollback_plan_raises PASSED
tests/test_jarvis_prime_build_packets.py::TestBuildPacketValidation::test_worker_not_enum_member_raises PASSED
tests/test_jarvis_prime_build_packets.py::TestBuildPacketValidation::test_overlap_literal_path_raises PASSED
tests/test_jarvis_prime_build_packets.py::TestBuildPacketValidation::test_overlap_glob_forbidden_shadows_allowed_raises PASSED
tests/test_jarvis_prime_build_packets.py::TestBuildPacketValidation::test_overlap_glob_allowed_shadows_forbidden_raises PASSED
tests/test_jarvis_prime_build_packets.py::TestBuildPacketValidation::test_no_overlap_passes PASSED
tests/test_jarvis_prime_build_packets.py::TestBuildPacketValidation::test_validate_strict_globs_false_skips_glob_check PASSED
tests/test_jarvis_prime_build_packets.py::TestBuildPacketValidation::test_validate_strict_globs_false_still_catches_literal_overlap PASSED
tests/test_jarvis_prime_build_packets.py::TestBuildPacketValidation::test_multiple_errors_combined_in_message PASSED
tests/test_jarvis_prime_build_packets.py::TestSerialization::test_to_dict_then_from_dict_roundtrips PASSED
tests/test_jarvis_prime_build_packets.py::TestSerialization::test_to_dict_serializes_worker_as_string_value PASSED
tests/test_jarvis_prime_build_packets.py::TestSerialization::test_from_dict_accepts_string_worker PASSED
tests/test_jarvis_prime_build_packets.py::TestSerialization::test_from_dict_ignores_unknown_keys PASSED
tests/test_jarvis_prime_build_packets.py::TestSerialization::test_from_dict_rejects_wrong_type_for_list_field PASSED
tests/test_jarvis_prime_build_packets.py::TestSerialization::test_from_dict_rejects_non_string_list_entry PASSED
tests/test_jarvis_prime_build_packets.py::TestSerialization::test_from_dict_rejects_unknown_worker_value PASSED
tests/test_jarvis_prime_build_packets.py::TestSerialization::test_from_dict_rejects_non_mapping PASSED
tests/test_jarvis_prime_build_packets.py::TestSerialization::test_from_dict_does_not_call_validate PASSED
tests/test_jarvis_prime_build_packets.py::TestMarkdownRendering::test_markdown_contains_all_section_headers PASSED
tests/test_jarvis_prime_build_packets.py::TestMarkdownRendering::test_markdown_section_order_is_stable PASSED
tests/test_jarvis_prime_build_packets.py::TestMarkdownRendering::test_markdown_acceptance_criteria_rendered_as_checkboxes PASSED
tests/test_jarvis_prime_build_packets.py::TestMarkdownRendering::test_markdown_verification_commands_rendered_in_code_block PASSED
tests/test_jarvis_prime_build_packets.py::TestMarkdownRendering::test_markdown_empty_optional_sections_show_none_placeholder PASSED
tests/test_jarvis_prime_build_packets.py::TestMarkdownRendering::test_markdown_blank_rollback_shows_placeholder_in_draft_mode PASSED
tests/test_jarvis_prime_build_packets.py::TestMarkdownRendering::test_markdown_includes_repo_root_and_branch PASSED
tests/test_jarvis_prime_build_packets.py::TestMarkdownRendering::test_markdown_includes_worker_value PASSED
tests/test_jarvis_prime_build_packets.py::TestMarkdownRendering::test_to_markdown_raises_when_packet_invalid PASSED
tests/test_jarvis_prime_build_packets.py::TestMarkdownRendering::test_to_markdown_validate_false_skips_check PASSED
tests/test_jarvis_prime_build_packets.py::TestMarkdownRendering::test_to_markdown_forwards_strict_globs_flag PASSED

============================== 42 passed in 0.72s ==============================
```

### compileall

```
$ python -m compileall hermes_cli/jarvis_prime/build_packets.py
Compiling 'hermes_cli/jarvis_prime/build_packets.py'...
$ echo $?
0
```

### Sample `to_dict()` output

```json
{
  "mission": "Create a strict build packet schema for Claude Code builder tasks.",
  "repo_root": "/home/user/hermes-agent",
  "branch": "aci/wave-05-build-packet-schema",
  "worker": "claude_code_builder",
  "allowed_files": [
    "hermes_cli/jarvis_prime/build_packets.py",
    "hermes_cli/jarvis_prime/__init__.py",
    "tests/test_jarvis_prime_build_packets.py",
    "docs/aci/reports/W05_BUILD_PACKET_SCHEMA.md"
  ],
  "acceptance_criteria": [
    "Can convert to/from dict.",
    "Can validate required fields.",
    "Can produce a prompt-ready markdown packet.",
    "Tests cover missing required fields.",
    "Tests cover forbidden overlap detection."
  ],
  "verification_commands": [
    "pytest tests/test_jarvis_prime_build_packets.py",
    "python -m compileall hermes_cli/jarvis_prime/build_packets.py"
  ],
  "rollback_plan": "Delete build_packets.py and revert __init__.py.",
  "forbidden_files": [
    "gateway/**",
    "apps/android/**",
    "pyproject.toml",
    "uv.lock",
    "README.md"
  ],
  "non_goals": [
    "Persistence layer for packets.",
    "Dispatcher into kanban_swarm.",
    "Packet-from-intent generation."
  ],
  "owner_gated_actions": [
    "push to remote",
    "open draft PR"
  ]
}
```

### Sample `to_markdown()` output

````markdown
# Build Packet

## Mission
Create a strict build packet schema for Claude Code builder tasks.

## Worker
claude_code_builder

## Repo
- Root: /home/user/hermes-agent
- Branch: aci/wave-05-build-packet-schema

## Allowed Files
- hermes_cli/jarvis_prime/build_packets.py
- hermes_cli/jarvis_prime/__init__.py
- tests/test_jarvis_prime_build_packets.py
- docs/aci/reports/W05_BUILD_PACKET_SCHEMA.md

## Forbidden Files
- gateway/**
- apps/android/**
- pyproject.toml
- uv.lock
- README.md

## Non-Goals
- Persistence layer for packets.
- Dispatcher into kanban_swarm.
- Packet-from-intent generation.

## Acceptance Criteria
- [ ] Can convert to/from dict.
- [ ] Can validate required fields.
- [ ] Can produce a prompt-ready markdown packet.
- [ ] Tests cover missing required fields.
- [ ] Tests cover forbidden overlap detection.

## Verification Commands
```
pytest tests/test_jarvis_prime_build_packets.py
python -m compileall hermes_cli/jarvis_prime/build_packets.py
```

## Rollback Plan
Delete build_packets.py and revert __init__.py.

## Owner-Gated Actions
- push to remote
- open draft PR
````

## Non-overlap audit

Files touched on this branch are restricted to the wave's ALLOWED list:

- `hermes_cli/jarvis_prime/__init__.py`
- `hermes_cli/jarvis_prime/build_packets.py`
- `tests/test_jarvis_prime_build_packets.py`
- `docs/aci/reports/W05_BUILD_PACKET_SCHEMA.md`

The wave's FORBIDDEN list (`gateway/**`, `apps/android/**`,
`pyproject.toml`, `uv.lock`, `README.md`) is untouched, confirmed by
`git diff --stat` on the branch.

## Risks and follow-ups

- **`fnmatch` lacks native `**` semantics.** `**` is normalized to a
  single `*` for overlap detection. Common shapes
  (`gateway/**`, `apps/android/**`) work; pathological globs may not.
  Documented; full `pathspec` semantics deferred.
- **No length budget on `mission` / `rollback_plan`.** Operators can
  paste an essay. Add max-length enforcement in W06+ if it becomes an
  issue.
- **No secret-pattern scan over `allowed_files`.** A future wave can
  reject packets that allow `.env`, `*credentials*`, etc.
- **`from_dict` silently drops unknown keys.** Forward-compat win,
  but typos in handwritten dicts won't be flagged. Acceptable for
  v1; revisit if it bites.
- **`Worker` enum is closed.** Adding a worker (e.g., the GitHub PR
  Publisher named in the operating-system doc) is a coordinated
  schema change. `test_enum_values_match_operating_doc` will fail
  until the enum is updated, which is the intended forcing
  function.

## Rollback

```
rm -rf hermes_cli/jarvis_prime/
rm tests/test_jarvis_prime_build_packets.py
rm docs/aci/reports/W05_BUILD_PACKET_SCHEMA.md
git push origin --delete aci/wave-05-build-packet-schema   # only after PR closure
```

No other module imports `hermes_cli.jarvis_prime.*` yet, so removal is
safe and leaves no dangling references.

## PR summary

- Branch: `aci/wave-05-build-packet-schema`
- Draft PR title: `wave 05: build packet schema`
- Tests run: 42 passed (`pytest tests/test_jarvis_prime_build_packets.py`).
- Compile check: `python -m compileall hermes_cli/jarvis_prime/build_packets.py` exit 0.
- Remaining risks: those listed in **Risks and follow-ups** above.
- Rollback: as listed above.

## Next wave hooks

- **W06** — dispatcher that consumes a `BuildPacket` and enqueues
  work into `kanban_swarm`, enforcing per-worker concurrency rules
  from the operating-system doc (no Claude Code + Codex on the same
  branch).
- **W07** — packet-from-intent renderer: turn a one-line operator
  intent + repo context into a draft `BuildPacket` for review before
  dispatch.

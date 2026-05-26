# Hermes Native Engineer

The Native Engineer is the isolated, stdlib-only authoring harness that
lets Hermes / Jarvis Prime begin proposing and validating its own code
changes under explicit safety contracts.

This document covers the W14 core. The core is intentionally **not wired**
into the router, model registry, `jarvis_prime` runtime, or `context` /
`memory_tree` layers. Those integrations land in later sprints.

## Purpose

Jarvis Prime is the Android body / Hermes brain product surface. As the
agent begins to author its own code, it needs a bench that:

1. Can read the repo into a structured map.
2. Knows what files it is and is not allowed to touch on a given mission.
3. Renders proposed changes as diffs without applying them to disk.
4. Dispatches tests under bounded subprocess control and parses their output.
5. Translates failures into deterministic next-step repair instructions
   (no model call needed).
6. Captures successful runs as reusable Standard Operating Procedures.
7. Evaluates the resulting evidence against the mission contract before
   anything is reported as "done".

The Native Engineer is the bench. Future sprints will graft this onto the
agent loop. W14 ships just the bench, plus tests.

## Isolation contract

| Guarantee | How it is enforced |
| --- | --- |
| Stdlib only | No imports outside the Python standard library. |
| Not wired in | The package is not imported by any router, model registry, jarvis_prime, context, or memory_tree module. |
| Validate-only patches | `patch_engine` has no `apply()`. It only validates and renders diffs. |
| Allow / deny path enforcement | `WorkPacket.is_path_allowed` rejects out-of-scope paths and lets forbidden globs win on conflict. |
| Bounded test execution | `test_runner.run` is the only subprocess entry point; `TestCommand` is a structured dataclass, not a string, so commands cannot be built from untrusted strings by accident. |
| Deterministic repair loop | `repair_loop.derive_instructions` is pure-function — no LLM, no I/O. |
| External owner gate (future) | Anything destructive — merges, deploys, publishing, real disk writes from the engine — remains outside this package and will require an owner-approval step when wiring lands. |

The Native Engineer is also **not** allowed to:

- Merge branches.
- Deploy or publish.
- Edit files outside `hermes_cli/native_engineer/**`,
  `tests/test_native_engineer_*.py`,
  `docs/aci/native-engineer/**`, and `docs/aci/reports/W*.md`.
- Treat self-modification as anything other than a branch-only proposal.

## Module map

```
hermes_cli/native_engineer/
├── __init__.py          # public surface re-exports
├── repo_map.py          # scan + classify + ast-based symbol extraction
├── work_packet.py       # mission / branch / allow / deny / criteria contract
├── patch_engine.py      # validate-only patch envelope + unified diff
├── test_runner.py       # TestCommand / TestResult + bounded subprocess.run
├── repair_loop.py       # deterministic failure → repair instructions
├── sop_miner.py         # successful job → SOPRecord + markdown rendering
└── evaluator.py         # evidence → pass/fail verdict against packet
```

### `repo_map`

Walks the repo with `os.walk`, classifies each file into
`source / test / doc / config / android / risky / other`, and extracts
top-level imports / classes / functions from Python files via `ast`. Risky
files (lockfiles, `.github/`, `.env*`, `*credentials*`, Gradle files) are
flagged so the engine has visibility into blast radius before proposing
edits.

### `work_packet`

`WorkPacket` is a frozen dataclass holding `mission`, `branch`,
`allowed_files`, `forbidden_files`, `acceptance_criteria`,
`verification_commands`, `rollback_plan`, and a tuple-of-pairs `metadata`
bag (kept as pairs so the packet is hashable). `is_path_allowed` is the
sole authority on "may we touch this path". Forbidden wins on conflict.

### `patch_engine`

`Patch` describes a proposed `create` / `modify` / `delete`.
`validate(patch, packet)` returns a `PatchValidationResult` with `allowed`,
a `reason`, and a unified-diff `dry_run_diff`. No disk writes in W14.
`rollback_notes` summarises the inverse of a patch sequence.

### `test_runner`

`TestCommand` is a structured dataclass; `run(command)` shells out via
`subprocess.run` with capture + timeout. `subprocess.TimeoutExpired` is
caught and surfaces as `returncode=None` plus `parsed["timed_out"] = True`.
`parse_pytest_output` and `parse_unittest_output` extract pass / fail /
error counts from captured text. `make_pytest_command` and
`make_compileall_command` are the small set of curated builders.

### `repair_loop`

`derive_instructions(test_result)` produces a tuple of `RepairInstruction`
records. Rules: green → `()`; `ImportError` / `ModuleNotFoundError` → one
`high` instruction targeting the missing module; each `FAILED <nodeid>`
line → one `medium` instruction targeting the test path; timeout → one
`medium` instruction asking to increase timeout or split the run.

### `sop_miner`

`mine(packet, patches, test_results)` returns an `SOPRecord` with title
(first 80 chars of mission), ordered patch steps, sorted-unique artifact
paths, verification commands carried from the packet, and heuristic tags
(`android`, `docs`, `tests`, `hermes_cli`, plus any explicit `tag(s)` in
metadata). `to_markdown` renders it for inclusion in reports.

### `evaluator`

`evaluate(packet, evidence)` returns a `Verdict`. The job passes when:

1. Every `PatchValidationResult.allowed` is `True`, **and**
2. At least one `TestResult.returncode == 0` exists **or**
   `metadata["test_skip_reason"]` is set, **and**
3. Every acceptance criterion appears (case-insensitive) in at least one
   patch rationale or metadata value.

## Public API quick reference

```python
from hermes_cli.native_engineer import (
    # repo map
    scan, classify, extract_python_symbols, RepoMap, FileEntry,
    # work contract
    WorkPacket,
    # patches
    Patch, PatchValidationResult, validate, dry_run_diff, rollback_notes,
    # test dispatch
    TestCommand, TestResult, run,
    parse_pytest_output, parse_unittest_output,
    make_pytest_command, make_compileall_command,
    # repair loop
    RepairInstruction, derive_instructions,
    # SOP capture
    SOPRecord, mine, to_markdown,
    # evidence gate
    Evidence, Verdict, evaluate,
)
```

## Verification

From repo root:

```
python -m compileall hermes_cli/native_engineer
python -m pytest tests/test_native_engineer_*.py -q
```

Both must exit `0`. The pytest run should report 50+ passing tests with no
failures.

## What is out of scope for W14

- Wiring into `hermes_cli/model_router.py`, `hermes_cli/jarvis_prime/*`,
  `hermes_cli/context/*`, or `hermes_cli/memory_tree/*`.
- Actual on-disk patch application (deferred behind a future owner gate).
- Android-side changes (`apps/android/**`).
- Skill registration under `skills/`.
- CI workflow changes under `.github/`.

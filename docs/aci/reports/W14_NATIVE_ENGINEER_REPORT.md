# W14 — Hermes Native Engineer Core: Sprint Report

## Mission

Create the isolated Hermes Native Engineer core so Jarvis Prime can begin
building code through its own controlled harness, without wiring the
engine into the router, model registry, `jarvis_prime` runtime, or
`context` / `memory_tree` layers.

## Scope

Validate-only bench: scan the repo, scope a work packet, validate
proposed patches against an allow / deny contract, dispatch tests under
bounded subprocess control, parse output, derive deterministic repair
instructions, mine SOPs from successful jobs, and evaluate evidence
against the contract. Stdlib only. No disk-writing patch application in
this sprint.

## Branch

`aci/jarvis-prime-14-hermes-native-engineer-core` (from `origin/main`).

## Files changed

**Source (8):**

```
hermes_cli/native_engineer/__init__.py
hermes_cli/native_engineer/evaluator.py
hermes_cli/native_engineer/patch_engine.py
hermes_cli/native_engineer/repair_loop.py
hermes_cli/native_engineer/repo_map.py
hermes_cli/native_engineer/sop_miner.py
hermes_cli/native_engineer/test_runner.py
hermes_cli/native_engineer/work_packet.py
```

**Tests (7):**

```
tests/test_native_engineer_evaluator.py
tests/test_native_engineer_patch_engine.py
tests/test_native_engineer_repair_loop.py
tests/test_native_engineer_repo_map.py
tests/test_native_engineer_sop_miner.py
tests/test_native_engineer_test_runner.py
tests/test_native_engineer_work_packet.py
```

**Docs (2):**

```
docs/aci/native-engineer/HERMES_NATIVE_ENGINEER.md
docs/aci/reports/W14_NATIVE_ENGINEER_REPORT.md   (this file)
```

No files outside the sprint's allowed list were touched.

## Tests run

```
$ python -m compileall hermes_cli/native_engineer
Listing 'hermes_cli/native_engineer'...
Compiling 'hermes_cli/native_engineer/__init__.py'...
Compiling 'hermes_cli/native_engineer/evaluator.py'...
Compiling 'hermes_cli/native_engineer/patch_engine.py'...
Compiling 'hermes_cli/native_engineer/repair_loop.py'...
Compiling 'hermes_cli/native_engineer/repo_map.py'...
Compiling 'hermes_cli/native_engineer/sop_miner.py'...
Compiling 'hermes_cli/native_engineer/test_runner.py'...
Compiling 'hermes_cli/native_engineer/work_packet.py'...
(exit 0)

$ python -m pytest tests/test_native_engineer_*.py -q
52 passed in ~1.3s
```

Coverage by module:

| Module | Tests |
| --- | --- |
| `repo_map` | 11 (classification + AST extraction + scan + ignore pruning) |
| `work_packet` | 7 (round-trip, glob allow / deny, forbidden-wins, hashability) |
| `patch_engine` | 9 (out-of-scope reject, missing before / after, unknown op, diff content, rollback notes) |
| `test_runner` | 9 (pytest + unittest parsers, run, non-zero exit, mocked timeout, builders) |
| `repair_loop` | 5 (green, import error, FAILED lines, timeout, fallback) |
| `sop_miner` | 5 (unique sorted artifacts, title truncation, tags, steps, markdown) |
| `evaluator` | 5 (pass, rejected validation, no green & no skip, skip reason gate, missing criteria) |

Isolation check — confirmed no module outside the package imports it:

```
$ grep -RIn "from hermes_cli.native_engineer\|import hermes_cli.native_engineer" \
       hermes_cli/ tests/ | \
   grep -v "hermes_cli/native_engineer/\|tests/test_native_engineer_"
(no output)
```

## Risks

- **Classification heuristics.** `repo_map.classify` may misflag exotic
  files. Mitigated by representative test coverage; the classifier is a
  pure function and future tuning will not break callers.
- **Subprocess timeout signalling.** `subprocess.TimeoutExpired` triggers
  a `SIGKILL` on the child, which the project's conftest live-system
  guard would block if the test exercised it with a real sleeping
  subprocess. The timeout test mocks `subprocess.run` instead, so the
  guard does not fire. Production callers of `run` are unaffected: the
  guard only intercepts PIDs outside the test process's own subtree, and
  any real callers manage their own children.
- **Glob translation.** `WorkPacket.is_path_allowed` translates `**`
  recursive globs to `*` for `fnmatch`. This is documented and covered
  by tests; future callers should pass repo-relative POSIX paths.

## Rollback

```
git rm -r hermes_cli/native_engineer tests/test_native_engineer_*.py \
          docs/aci/native-engineer docs/aci/reports/W14_NATIVE_ENGINEER_REPORT.md
```

No other files were touched.

## Draft PR

Title: `W14: Add Hermes Native Engineer core`

(Draft PR link appended after `git push`.)

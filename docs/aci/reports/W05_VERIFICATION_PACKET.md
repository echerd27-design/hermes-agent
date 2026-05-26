# Wave 05 — Local Verification Packet

## Mission

Standardize how JARVIS Prime records test/verification evidence so the JARVIS
Test Gate and Release Gate (`docs/jarvis-verification-gates.md`) can summarize
results from a single, structured shape. This wave adds a stdlib-only helper
package (`hermes_cli.jarvis_prime`) that captures one entry per verification
command. It does **not** execute commands — a future wave will add a runner
that calls these helpers; for now operators (or coding agents) build packets
by hand from observed results.

## Branch

`aci/wave-05-verification-packet` (off `7b82077`, draft PR only — not for
merge to main).

## Changed files

- `hermes_cli/jarvis_prime/__init__.py` — new subpackage re-exporting the
  public API (`VerificationEntry`, `VerificationPacket`, `summarize_text`,
  and the `PASSED` / `FAILED` / `SKIPPED` status constants).
- `hermes_cli/jarvis_prime/verification.py` — the dataclass-based packet
  module. Stdlib only (`dataclasses`, `datetime`, `json`, `typing`).
- `tests/test_jarvis_prime_verification.py` — 34 pytest cases covering
  pass/fail/skipped construction, validation, packet aggregation, JSON
  output shape, the `summarize_text` helper, and the acceptance guardrail
  that the module does not import `subprocess` / `os.system` / `os.execv`.
- `docs/aci/reports/W05_VERIFICATION_PACKET.md` — this report.

No other files were modified. `hermes_cli/__init__.py` was not touched
(Python auto-discovers subpackages with their own `__init__.py`).

## Tests run

| Command | Result |
| --- | --- |
| `uv run pytest tests/test_jarvis_prime_verification.py -v` | 34 passed in 3.02s |
| `uv run python -m compileall hermes_cli/jarvis_prime/verification.py -q` | exit 0 (no warnings) |

## Acceptance criteria mapping

| Criterion | Where it's satisfied |
| --- | --- |
| Stdlib-only | `hermes_cli/jarvis_prime/verification.py` imports only `json`, `dataclasses`, `datetime`, `typing`. |
| Tests cover pass/fail/skipped | `TestVerificationEntry` and `TestVerificationPacket` in the test file exercise all three statuses individually and in combination, plus validation errors for the invalid combinations (skip without reason, skip_reason on non-skip entries, invalid status strings). |
| Output can feed JARVIS gates | `VerificationPacket.to_dict()` / `to_json()` produce `{"entries": [...], "counts": {passed, failed, skipped}, "gate_result": "passed"\|"failed"}` — the exact shape the Test Gate row of the Gate Summary Template needs to roll up. `gate_result()` returns `"failed"` if any entry failed, else `"passed"`. |
| Does not execute commands itself yet | `TestModuleDoesNotExecuteCommands` asserts the module namespace contains no `subprocess`, `Popen`, `run`, `system`, or `execv`. Manual review confirms there are no command-execution call sites. |

## Gate Summary

```text
GATE SUMMARY
Planning gate: passed — mission, branch, allowed/forbidden files, acceptance
  criteria, and verify commands were enumerated from the wave prompt before
  any file was created.
Build gate: passed — three source files plus this report; stdlib only; no
  changes to pyproject.toml, uv.lock, or any forbidden path.
Review gate: passed (self-review) — module is ~120 lines of dataclass code
  with a single responsibility; public surface is re-exported through
  __init__.py; no dead code introduced. No external reviewer assigned for
  the draft PR yet.
Test gate: passed — `pytest tests/test_jarvis_prime_verification.py` →
  34 passed. Per-command evidence is captured by VerificationPacket itself
  (the data shape underneath this row).
Security gate: passed — no secrets read, written, or logged; no network or
  filesystem access from the module; the module cannot execute commands by
  design and a test enforces that property.
Release gate: not applicable — draft PR only, no merge, no deploy.
Owner approval gate: pending — draft PR will be opened for echerd27 to
  review before any merge decision.
Rollback gate: passed — see Rollback plan below; revert is a single-commit
  delete of four new files.
Result: passed for the changes proposed in this draft.
Remaining risk: see Remaining risks below.
```

## Remaining risks

- **Producer-only today.** Nothing in Hermes currently *calls* these
  helpers. Until a runner exists, the only way to populate a packet is by
  hand — so the consistency benefit lands only when operators or a future
  wave wire it in. Failure mode: the module sits unused and packets keep
  being free-text in PR descriptions. Mitigation: a follow-up wave should
  add a thin runner (subprocess-based) and a `jarvis verify` CLI surface.
- **No content guarantees on summaries.** `stdout_summary` and
  `stderr_summary` are free strings. A careless caller could paste a raw
  secret into them; the packet has no scrubber. The `summarize_text`
  helper just truncates. Mitigation today: callers are responsible; the
  Security Gate of the operator's workflow remains the backstop. Future
  wave should add a redaction pass (env-var-name detection, base64
  heuristics, etc.) before this is exposed to any non-local sink.
- **Timestamp is wall-clock UTC.** `__post_init__` calls
  `datetime.now(timezone.utc)`. Reproducible-build replay scenarios that
  need deterministic timestamps must pass `timestamp=` explicitly; tests
  rely on this.
- **`gate_result()` semantics are permissive on skip-only packets.** A
  packet with only skipped entries returns `"passed"` because no command
  failed. The Test Gate doc says "skipped tests are explained" — that
  explanation lives in the wave report (this section), not in the data
  shape. A reviewer or runner that wants to require at least one passing
  entry must enforce that separately.

## Rollback plan

To revert this wave:

```
git checkout main   # or whichever base branch the PR was opened against
git branch -D aci/wave-05-verification-packet
# OR, if already merged (it should not be — this is a draft PR):
git revert <merge-commit>
```

Manual cleanup (only needed if the branch was partially applied):

```
rm hermes_cli/jarvis_prime/verification.py
rm hermes_cli/jarvis_prime/__init__.py
rmdir hermes_cli/jarvis_prime
rm tests/test_jarvis_prime_verification.py
rm docs/aci/reports/W05_VERIFICATION_PACKET.md
rmdir docs/aci/reports docs/aci 2>/dev/null || true
```

No runtime state, no migrations, no external services to roll back.
`hermes_cli/__init__.py` was not modified, so no revert is needed there.

## PR summary

Adds `hermes_cli.jarvis_prime.verification` — a stdlib-only helper that
records one structured entry per verification command (command, cwd, exit
code, optional duration, stdout/stderr summary, pass/fail/skipped status,
skip reason, artifacts, timestamp) and aggregates entries into a packet
whose `to_dict()` / `to_json()` output feeds the JARVIS Test Gate row of
the Gate Summary Template. The module does not execute commands and a
test enforces that property; the next wave can add a runner on top.
Covered by 34 pytest cases; `python -m compileall` clean. Draft PR — not
for merge until owner review.

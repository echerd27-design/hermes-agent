# W02 — Risk Class Model for JARVIS Work Packets

Wave: `aci/wave-02-risk-class-model`
Status: Draft PR (do not merge to main)
Date: 2026-05-26

## Mission

Give JARVIS Prime a deterministic, dependency-free way to label any
free-text intent or work packet with one of five risk classes so the
operator layer can pick the right gates, the right workers, and the right
authorization flow before acting.

The JARVIS operating-system doc already lists `"Risk class"` as a required
slot in the Coding/Operator response format at
`docs/jarvis-prime-operating-system.md:193`, but does not enumerate the
values. W02 fills that gap as a leaf module — no integration into routing
yet, so the new helper can be reviewed, tested, and iterated on in
isolation before later waves wire it in.

## Scope

In scope:
- `hermes_cli/jarvis_prime/risk.py` — RC0–RC4 enum, signal table, and the
  deterministic helpers `classify`, `is_owner_gated`, `owner_gates_for`,
  `max_class_for`.
- `hermes_cli/jarvis_prime/__init__.py` — re-export the public surface so
  callers can `from hermes_cli.jarvis_prime import classify`.
- `tests/test_jarvis_prime_risk.py` — pytest coverage for per-tier inputs,
  common ACI/Hermes commands, owner-gate alignment, edge cases, and
  determinism.
- This report.

Out of scope:
- Wiring `classify()` into the JARVIS routing layer or operator-mode
  response template (planned for a later wave).
- Updates to the operating-system doc to reference the new module
  (deliberate — the wave contract limits writes to four files).
- Any change to `pyproject.toml`, `uv.lock`, `README.md`, `gateway/**`,
  `apps/android/**`, or other waves' files.

## Risk classes

| Class | Meaning | Examples |
| --- | --- | --- |
| RC0 | Answer only, no side effects | "What does RC3 mean?", small talk |
| RC1 | Local planning, drafting, docs | `/plan`, `/audit`, `draft a release note` |
| RC2 | Code changes inside the working tree | `refactor helper`, `fix bug`, `edit hermes_cli/foo.py` |
| RC3 | Repo mutations, PRs, deps, network, credentials | `git push`, `pip install`, `curl https://…`, `open pr` |
| RC4 | Deploy, publish, merge, DNS, money, app store, regulated claims | `deploy`, `merge to main`, `npm publish`, `force push`, regulated/HIPAA/FDA |

## Design

### Signal table

A single ordered `tuple[RiskSignal, ...]` is the source of truth. Each row
carries a pattern, a risk class, a human-readable label, an `owner_gate`
boolean, and a `whole_word` flag. Rows are ordered RC4 → RC1 so that
`matched_signals` keeps owner-gated phrases at the front of the tuple.

Why a single table rather than parallel keyword tuples per tier:
- Adding a signal touches one place.
- The `label` and `owner_gate` columns give `RiskAssessment` its
  `matched_signals` and `owner_gates` fields for free.
- Tests can iterate the table to assert invariants (e.g. owner-gated rows
  must be RC4).

### Matching algorithm

1. Coerce `None` → `""`. Empty/whitespace input returns RC0 with empty
   tuples.
2. Lowercase the input once.
3. For each `RiskSignal`, match by either:
   - regex word-boundary (`\b…\b`) when `whole_word=True`, or
   - plain substring search when `whole_word=False` (needed for phrases
     like `merge to main` and flags like `--force`).
4. Collect every matching signal in table order.
5. `risk_class = max(matched.risk_class)`; `matched_signals` and
   `owner_gates` are dedup'd label tuples preserving table order.
6. Build a one-line rationale: `"RCN: matched a, b (owner gates: x, y)."`

Time complexity is linear in `len(SIGNALS) * len(text)` (a couple hundred
small regex / substring checks per call) — fast enough to call inline on
every JARVIS turn.

### Owner gate vs RC4

`is_owner_gated(text)` is **not** the same as
`classify(text).risk_class == RC4`. Regulated/compliance claims classify
as RC4 because of their severity, but they are not owner-approval-gated
in the same way as a deploy or merge. `is_owner_gated` returns `True`
only when a signal with `owner_gate=True` fires, which lets the routing
layer decide between "needs careful drafting" (regulated claim) and
"halt for explicit authorization" (deploy / merge / spend money).

## Owner gate alignment

The owner-gated phrases in the operating-system doc
(`docs/jarvis-prime-operating-system.md`, lines 293–306) and the
verification-gates doc (`docs/jarvis-verification-gates.md`, Owner
Approval Gate section) each map to at least one signal in the table:

| Doc phrase | Signal label(s) | Risk class | Owner-gated |
| --- | --- | --- | --- |
| spending money | `money` | RC4 | yes |
| posting publicly | `public posting` | RC4 | yes |
| creating third-party accounts | `third-party account` | RC4 | yes |
| OAuth or credential changes | `credential change`, `secret rotation` | RC4 | yes |
| production deploys | `deploy` | RC4 | yes |
| DNS changes | `dns change` | RC4 | yes |
| main-branch merges | `merge to main` | RC4 | yes |
| package publishing | `publish`, `package publish` | RC4 | yes |
| app store submissions | `app store submission` | RC4 | yes |
| force-pushes | `force push`, `destructive git` | RC4 | yes |
| legal/compliance/health/financial/regulated claims | `regulated claim` | RC4 | no (severity-only) |

The test `TestOwnerGateAlignment` in `tests/test_jarvis_prime_risk.py`
locks every phrase above into RC4 and asserts the right gate label fires.

## Known limitations

- **No negation handling.** `"don't deploy yet"` still classifies RC4.
  This is intentional and documented in the module docstring; the
  classifier signals "deserves owner review", not "will execute". A test
  pins this behavior so it cannot regress silently.
- **No code-block stripping.** A risky command wrapped in fenced ``` ```
  ``` blocks still classifies on the full text. A `git push --force`
  inside a Markdown sample is still a real signal.
- **Pattern-based, not intent-parsed.** The classifier matches English/CLI
  strings; it does not parse ASTs or call an LLM. It will miss novel
  phrasings (e.g. `"send it to production"` does match `production`, but
  `"ship it"` does not match anything). Adding more phrasings is a
  one-line table edit.
- **Word boundary caveat.** Single-word patterns use `\b` boundaries so
  e.g. `deploy` does not fire on `redeploys`. Multi-word and flag-style
  patterns (`--force`, `git push`) use plain substring search; they may
  match inside larger words. The test suite includes a regression case.

## Verification

Both commands from the wave spec ran clean locally on the branch:

```
pytest tests/test_jarvis_prime_risk.py
python -m compileall hermes_cli/jarvis_prime
```

Exit codes for both commands are recorded in the PR description.

## Rollback

All four files added in this wave are net-new. To roll back:

1. `git checkout main -- :^` (no-op for these paths — they don't exist on
   `main`).
2. `rm hermes_cli/jarvis_prime/risk.py hermes_cli/jarvis_prime/__init__.py`
3. `rmdir hermes_cli/jarvis_prime` (now empty).
4. `rm tests/test_jarvis_prime_risk.py`
5. `rm docs/aci/reports/W02_RISK_CLASS_MODEL.md`
6. `rmdir docs/aci/reports docs/aci` if the directories are empty.
7. Close the draft PR without merging.

No in-place edits to revert; no callers yet depend on this module.

## Follow-ups (not part of W02)

- Wire `classify()` into JARVIS routing / operator-mode response template
  so the "Risk class" slot at
  `docs/jarvis-prime-operating-system.md:193` becomes data-driven.
- Reconcile the wave-report directory. Existing wave-style reports live
  at `docs/plans/2026-MM-DD-*.md`; the W02 wave contract pinned
  `docs/aci/reports/`. Before W03, decide whether to consolidate the two
  trees or keep them separate (e.g. `docs/aci/` for ACI-program waves,
  `docs/plans/` for general plans). Surface to owner; do not silently
  fork the convention further.
- Consider richer signals: regex patterns for `gh pr merge`, `vercel`,
  `cloudflare`, branch-name heuristics, etc. Each is a single-row
  addition.

## Remaining risk

- The classifier is regex-only. Anything the table does not literally
  encode falls through to RC0. The follow-up to wire it into JARVIS
  routing must not treat RC0 as "no risk" — only as "no recognised
  signal".
- The owner-gate table reflects the docs as of `2026-05-26`. If the
  operating-system doc adds new gates, the table and the
  `TestOwnerGateAlignment` constants both need an update — keep them in
  the same PR.

## Changed files

- `hermes_cli/jarvis_prime/risk.py` (new)
- `hermes_cli/jarvis_prime/__init__.py` (new)
- `tests/test_jarvis_prime_risk.py` (new)
- `docs/aci/reports/W02_RISK_CLASS_MODEL.md` (new, this file)

No files outside the wave allowlist were modified.

## PR summary

Title: `W02: risk class model for JARVIS work packets`

Body covers: mission, files added (all four are new), the RC0–RC4
contract with one example per tier, owner-gate alignment with the
existing JARVIS docs, the two verification commands, remaining risks
(regex-only, no integration), rollback (delete-only), and explicit
`Draft / do not merge` marker.

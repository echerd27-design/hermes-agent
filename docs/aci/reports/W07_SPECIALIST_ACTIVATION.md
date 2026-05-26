# Wave 07 — Specialist Activation Matrix

| Field         | Value                                       |
| ------------- | ------------------------------------------- |
| Wave          | W07                                         |
| Logical name  | `aci/wave-07-specialist-activation`         |
| Branch pushed | `claude/awesome-goldberg-zrzaA`             |
| Date          | 2026-05-26                                  |
| Status        | Draft PR (no merge to main, no deploy)      |

## Mission

Create a deterministic helper that maps free-form text and optional context
to the JARVIS Prime specialist set. The router itself is owned by a later
wave; W07 only delivers the matrix and tests so the router has a stable,
testable input to call.

## Files changed

- `hermes_cli/jarvis_prime/specialists.py` — new module. Frozen `Specialist`
  dataclass, immutable `SPECIALISTS` tuple of nine entries, and the
  `activate_specialists(text, *, context=None)` function.
- `hermes_cli/jarvis_prime/__init__.py` — new package init. Re-exports
  `Specialist`, `SPECIALISTS`, `activate_specialists`. Does **not** import
  `router.py` (forbidden for this wave).
- `tests/test_jarvis_prime_specialists.py` — new pytest suite, 81 cases,
  class-grouped + parametrized to match `tests/test_hermes_constants.py`.
- `docs/aci/reports/W07_SPECIALIST_ACTIVATION.md` — this file.

No files outside the allowed list were touched.

## Specialist matrix

Canonical order (also the return order of `activate_specialists`). Trigger
phrases are stored lowercase; matching is case-insensitive and uses
word/phrase boundaries.

| # | ID                              | Display name                   | Representative triggers                                                       |
| - | ------------------------------- | ------------------------------ | ----------------------------------------------------------------------------- |
| 1 | `hazmat-command-specialist`     | HazMat Command Specialist      | `hazmat`, `49 cfr`, `tdg`, `erg`, `placarding`, `shipping paper`, `audit ledger`, `compliance claim`, `driver safety` |
| 2 | `nourish-product-specialist`    | Nourish Product Specialist     | `nourish`, `nutrition`, `recipe`, `meal logging`, `behavior change`, `nutrient math`, `health claim`, `food privacy` |
| 3 | `logistics-domain-specialist`   | Logistics Domain Specialist    | `logistics`, `hey jay`, `trucking`, `dispatch`, `fleet`, `terminal`, `driver workflow`, `ltl`, `carrier` |
| 4 | `security-compliance-reviewer`  | Security / Compliance Reviewer | `security`, `compliance`, `secret`, `credential`, `oauth`, `cve`, `vulnerability`, `regulated`, `trust boundary`, `authz`, `authn` |
| 5 | `product-ux-reviewer`           | Product UX Reviewer            | `ux`, `user experience`, `onboarding`, `demo`, `user journey`, `usability`, `friction`, `adoption` |
| 6 | `qa-release-gate`               | QA Release Gate                | `release`, `release readiness`, `go/no-go`, `pre-release`, `ship`, `launch`, `deploy`, `production deploy`, `qa gate`, `test coverage` |
| 7 | `memory-evidence-curator`       | Memory Evidence Curator        | `evidence`, `audit`, `citation`, `memory`, `durable memory`, `source of truth`, `fact verification` |
| 8 | `career-strategy-specialist`    | Career Strategy Specialist     | `career`, `promotion`, `resume`, `cv`, `interview`, `job offer`, `hiring negotiation`, `leveling`, `career positioning` |
| 9 | `contrarian-reviewer`           | Contrarian Reviewer            | `contrarian`, `red team`, `red-team`, `devil's advocate`, `critique`, `blind spot`, `weak assumption`, `push back` |

Source of truth: `docs/jarvis-prime-operating-system.md` ("Operating
Hierarchy" + "Specialist Activation Rules"). Council-side roles (4–9)
also reference the active subagent files in `.claude/agents/`.

## Determinism contract

* Same `(text, context)` always returns the same tuple, in the canonical
  order above.
* Matching is case-insensitive (input lowercased once).
* Triggers match on word/phrase boundaries. `ship` does not fire inside
  `shipping`; `cv` does not fire inside `cve`. Multi-word triggers like
  `shipping paper` disambiguate domain overlap with QA Release Gate.
* Smallest useful set: a specialist only enters the result when one of
  its own triggers fires, or it appears in `context["force"]`.
* Exclusion wins over inclusion: an ID in both `force` and `exclude` is
  excluded.
* Unknown IDs in `force` or `exclude` are silently ignored.
* `None` / non-string input is coerced to empty and yields `()`.

## Verification

All from repo root, on branch `claude/awesome-goldberg-zrzaA`:

```bash
python -m compileall hermes_cli/jarvis_prime/specialists.py hermes_cli/jarvis_prime/__init__.py
python -c "from hermes_cli.jarvis_prime import activate_specialists, SPECIALISTS; \
  assert len(SPECIALISTS) == 9; \
  assert activate_specialists('placarding 49 CFR review')[0].id == 'hazmat-command-specialist'; \
  print('ok')"
pytest -o addopts="" tests/test_jarvis_prime_specialists.py -v
```

Results:

- `compileall` — both files compiled cleanly (no syntax errors).
- Smoke import — printed `ok`.
- pytest — **81 passed in 2.02s**, 0 failed, 0 skipped. (Run with
  `-o addopts=""` to bypass the repo-level `-n auto`/`--timeout=…`
  arguments that depend on `pytest-xdist` / `pytest-timeout`, which are
  not installed in this container. With those plugins installed, the
  default `pytest tests/test_jarvis_prime_specialists.py` invocation
  from the task `VERIFY` block works identically.)

## Out of scope / next waves

- `hermes_cli/jarvis_prime/router.py` is intentionally untouched. W08 (or
  whichever wave owns the router) imports `activate_specialists` from
  this package and decides how to act on the returned tuple.
- No wiring into the Hermes gateway / delivery layer.
- No new specialists beyond the documented 9. Adding any new specialist
  requires updating `docs/jarvis-prime-operating-system.md` first.

## Risks

- **Trigger drift.** Triggers were derived from the operating-system
  document; if that doc is later edited, this matrix must be re-aligned.
  Mitigation: the doc is the linked source of truth, and the wave report
  enumerates every trigger family for easy diff review.
- **Over-activation on long mission text.** A long prompt that name-drops
  every domain word will activate all nine specialists. This is correct
  behavior, but downstream waves should still respect "smallest useful
  set" when constructing prompts.
- **No I18N.** Triggers are English-only and case-folded; non-ASCII or
  translated text will under-activate. Intentional for this wave.

## Rollback

The package is new and the router is not yet wired:

```bash
git rm -r hermes_cli/jarvis_prime
git rm tests/test_jarvis_prime_specialists.py
git rm docs/aci/reports/W07_SPECIALIST_ACTIVATION.md
git commit -m "revert: wave-07 specialist activation"
```

Then close the draft PR. No external state to undo (no deploy, no DNS, no
secrets, no third-party calls).

## PR summary (for the draft PR body)

- **Wave:** W07 — deterministic specialist activation matrix.
- **What it adds:** a pure-stdlib helper that maps text → specialists.
- **What it does not touch:** the router, skills/, gateway/, mobile,
  config, packaging.
- **Tests:** 81 cases covering all six required domains (HazMat,
  Nourish, Hey Jay/logistics, security, release, career) plus
  determinism, ordering, idempotence, force/exclude, and word-boundary
  guards.
- **Status:** draft, no merge, no deploy.

## Open questions

None remaining; all three planning questions (branch, `dispatch`
trigger, `__init__.py` re-exports) were resolved with the owner before
implementation.

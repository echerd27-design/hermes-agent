"""Single trivial test to force the tests workflow to run on this baseline PR.

This file is a diagnostic-only addition that should be deleted before this
branch is merged. It exists to verify whether main's full test suite
currently passes when the only delta from main is a single passing test
file in a new path.
"""


def test_ci_baseline_smoke():
    assert 1 + 1 == 2

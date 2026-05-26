"""JARVIS Prime helpers used by Hermes routing.

This package currently exposes only the deterministic specialist
activation matrix; the router itself lives in a sibling module added
by a later wave and is intentionally not imported here.
"""

from hermes_cli.jarvis_prime.specialists import (
    SPECIALISTS,
    Specialist,
    activate_specialists,
)

__all__ = ["Specialist", "SPECIALISTS", "activate_specialists"]

"""JARVIS Prime — orchestrator layer above the AOS Council.

Surfaces:

- :mod:`hermes_cli.jarvis_prime.modes` — deterministic mode classifier
  (Companion / Strategy / Critic / Builder / Mobile Voice) plus
  specialist activation (HazMat / Nourish / Logistics).

See ``docs/jarvis-prime-operating-system.md`` for the full surface
contract; this package ships the runtime pieces wave-by-wave.
"""

from hermes_cli.jarvis_prime.modes import (
    Classification,
    Mode,
    classify,
    classify_mode,
)

__all__ = ["Classification", "Mode", "classify", "classify_mode"]

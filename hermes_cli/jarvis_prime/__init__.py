"""JARVIS Prime — AOS Council schema and orchestration primitives.

Public types are re-exported here so consumers can write::

    from hermes_cli.jarvis_prime import FinalRecommendation, DecisionStatus

instead of reaching into the ``aos`` submodule.
"""

from hermes_cli.jarvis_prime.aos import (
    ContrarianObjection,
    CouncilDecision,
    CouncilPerspective,
    CouncilQuestion,
    DecisionStatus,
    FinalRecommendation,
    SpecialistFinding,
)

__all__ = (
    "ContrarianObjection",
    "CouncilDecision",
    "CouncilPerspective",
    "CouncilQuestion",
    "DecisionStatus",
    "FinalRecommendation",
    "SpecialistFinding",
)

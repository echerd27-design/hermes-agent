"""JARVIS Prime durable job model (Wave 06).

Data-model-only. Not yet wired into the gateway. See
``docs/jarvis-prime-operating-system.md`` and
``docs/jarvis-verification-gates.md``.
"""

from hermes_cli.jarvis_prime.jobs import (
    SCHEMA_VERSION,
    CyclicDependencyError,
    DependencyBlockedError,
    GateEvidence,
    GateOutcome,
    GateType,
    InvalidTransitionError,
    Job,
    JobEvent,
    JobModelError,
    Task,
    TaskDependency,
    TaskStatus,
    UnknownTaskError,
    WorkerAssignment,
    validate_transition,
)

__all__ = [
    "SCHEMA_VERSION",
    "TaskStatus",
    "GateType",
    "GateOutcome",
    "TaskDependency",
    "WorkerAssignment",
    "GateEvidence",
    "JobEvent",
    "Task",
    "Job",
    "JobModelError",
    "InvalidTransitionError",
    "DependencyBlockedError",
    "UnknownTaskError",
    "CyclicDependencyError",
    "validate_transition",
]

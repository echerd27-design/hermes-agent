"""JARVIS Prime durable job model (Wave 06).

Stdlib-only data model for JARVIS Prime jobs, tasks, workers, gates,
and event logs. This module is intentionally NOT wired into the
gateway or any persistence layer — Wave 06 establishes the model and
its invariants only; later waves carry it into runtime systems.

See:
- ``docs/jarvis-prime-operating-system.md`` — JARVIS Prime operating
  hierarchy, modes, worker lanes.
- ``docs/jarvis-verification-gates.md`` — the eight verification
  gate types whose vocabulary ``GateType`` mirrors.

Invariants:
- Stdlib only (``dataclasses``, ``enum``, ``json``, ``uuid``,
  ``datetime``, ``typing``).
- All mutation goes through the ``Job`` API — task status is never
  reassigned outside ``Job.transition_task``.
- The event log on a ``Job`` is append-only by convention; every
  mutating ``Job`` method emits exactly one ``JobEvent``.
- Serialization round-trips deeply: ``Job.from_json(j.to_json())``
  yields a structurally identical ``Job`` for any well-formed input.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


SCHEMA_VERSION = 1


# ── Exceptions ─────────────────────────────────────────────────────────────


class JobModelError(Exception):
    """Base error for the jarvis_prime jobs model."""


class InvalidTransitionError(JobModelError):
    """A status transition is not in the allowed table."""


class DependencyBlockedError(JobModelError):
    """A task cannot start because blocking predecessors are unfinished."""

    def __init__(self, task_id: str, blocking_ids: list[str]) -> None:
        self.task_id = task_id
        self.blocking_ids = list(blocking_ids)
        super().__init__(
            f"task {task_id!r} cannot start; blocked by {self.blocking_ids}"
        )


class UnknownTaskError(JobModelError):
    """A task id was referenced that is not present on the job."""


class CyclicDependencyError(JobModelError):
    """Adding a dependency would create a cycle in the task DAG."""


# ── Enums ──────────────────────────────────────────────────────────────────


class TaskStatus(Enum):
    PLANNED = "planned"
    RUNNING = "running"
    VALIDATING = "validating"
    BLOCKED = "blocked"
    FAILED = "failed"
    DONE = "done"
    CANCELLED = "cancelled"


class GateType(Enum):
    PLANNING = "planning"
    BUILD = "build"
    REVIEW = "review"
    TEST = "test"
    SECURITY = "security"
    RELEASE = "release"
    OWNER_APPROVAL = "owner_approval"
    ROLLBACK = "rollback"


class GateOutcome(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"
    OWNER_APPROVED = "owner_approved"


# ── Helpers ────────────────────────────────────────────────────────────────


def _new_id() -> str:
    return uuid.uuid4().hex


def _utcnow_iso() -> str:
    # Always a trailing 'Z' so the wire format is unambiguous.
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(s: str) -> datetime:
    # Accept both '...Z' and '+00:00' encodings.
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _coerce_enum(enum_cls: type, value: Any):
    if isinstance(value, enum_cls):
        return value
    return enum_cls(value)


# ── Status transition table ────────────────────────────────────────────────
#
# Audited "middle" semantics: failed must re-queue through PLANNED (so
# dependencies are re-evaluated) but a soft VALIDATING miss may rerun
# in place. DONE and CANCELLED are terminal. CANCELLED is reachable
# from every non-terminal state (operator override).

_VALID_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.PLANNED: frozenset({
        TaskStatus.RUNNING, TaskStatus.BLOCKED, TaskStatus.CANCELLED,
    }),
    TaskStatus.RUNNING: frozenset({
        TaskStatus.VALIDATING, TaskStatus.BLOCKED,
        TaskStatus.FAILED, TaskStatus.CANCELLED,
    }),
    TaskStatus.VALIDATING: frozenset({
        TaskStatus.DONE, TaskStatus.FAILED,
        TaskStatus.RUNNING, TaskStatus.CANCELLED,
    }),
    TaskStatus.BLOCKED: frozenset({
        TaskStatus.PLANNED, TaskStatus.CANCELLED,
    }),
    TaskStatus.FAILED: frozenset({
        TaskStatus.PLANNED, TaskStatus.CANCELLED,
    }),
    TaskStatus.DONE: frozenset(),
    TaskStatus.CANCELLED: frozenset(),
}


def validate_transition(current: TaskStatus, target: TaskStatus) -> None:
    """Raise ``InvalidTransitionError`` if (current -> target) is not allowed.

    Self-loops are disallowed; ``DONE`` and ``CANCELLED`` are terminal.
    """
    if current == target:
        raise InvalidTransitionError(
            f"transition {current.value} -> {target.value} not allowed; "
            f"self-loops are disallowed"
        )
    allowed = _VALID_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        allowed_str = sorted(s.value for s in allowed) or ["(none; terminal)"]
        raise InvalidTransitionError(
            f"transition {current.value} -> {target.value} not allowed; "
            f"valid targets: {allowed_str}"
        )


# ── Dataclasses ────────────────────────────────────────────────────────────


@dataclass
class TaskDependency:
    """An edge in the task DAG.

    ``kind="blocks"`` means the successor cannot transition to RUNNING
    until the predecessor reaches DONE. ``kind="informs"`` is advisory
    only and does not block.
    """

    predecessor_task_id: str
    successor_task_id: str
    kind: str = "blocks"

    def to_dict(self) -> dict[str, Any]:
        return {
            "predecessor_task_id": self.predecessor_task_id,
            "successor_task_id": self.successor_task_id,
            "kind": self.kind,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskDependency":
        return cls(
            predecessor_task_id=data["predecessor_task_id"],
            successor_task_id=data["successor_task_id"],
            kind=data.get("kind", "blocks"),
        )


@dataclass
class WorkerAssignment:
    """A worker lane (Claude Code Builder, Codex Reviewer, etc.) bound to a task.

    ``worker`` is a free string so the worker catalog can grow without
    a model change.
    """

    worker: str
    role: str = "primary"
    assigned_at: str = field(default_factory=_utcnow_iso)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker": self.worker,
            "role": self.role,
            "assigned_at": self.assigned_at,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkerAssignment":
        return cls(
            worker=data["worker"],
            role=data.get("role", "primary"),
            assigned_at=data.get("assigned_at") or _utcnow_iso(),
            notes=data.get("notes", ""),
        )


@dataclass
class GateEvidence:
    """A verification-gate outcome recorded against a task or the whole job."""

    gate: GateType
    outcome: GateOutcome
    recorded_at: str = field(default_factory=_utcnow_iso)
    summary: str = ""
    artifacts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate": self.gate.value,
            "outcome": self.outcome.value,
            "recorded_at": self.recorded_at,
            "summary": self.summary,
            "artifacts": list(self.artifacts),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GateEvidence":
        return cls(
            gate=_coerce_enum(GateType, data["gate"]),
            outcome=_coerce_enum(GateOutcome, data["outcome"]),
            recorded_at=data.get("recorded_at") or _utcnow_iso(),
            summary=data.get("summary", ""),
            artifacts=list(data.get("artifacts") or []),
        )


@dataclass
class JobEvent:
    """An append-only entry in the job's audit log."""

    event_type: str
    occurred_at: str = field(default_factory=_utcnow_iso)
    task_id: Optional[str] = None
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    message: str = ""
    event_id: str = field(default_factory=_new_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at,
            "task_id": self.task_id,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobEvent":
        return cls(
            event_type=data["event_type"],
            occurred_at=data.get("occurred_at") or _utcnow_iso(),
            task_id=data.get("task_id"),
            from_status=data.get("from_status"),
            to_status=data.get("to_status"),
            message=data.get("message", ""),
            event_id=data.get("event_id") or _new_id(),
        )


@dataclass
class Task:
    """A unit of work inside a Job."""

    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PLANNED
    task_id: str = field(default_factory=_new_id)
    dependencies: list[TaskDependency] = field(default_factory=list)
    workers: list[WorkerAssignment] = field(default_factory=list)
    gates: list[GateEvidence] = field(default_factory=list)
    created_at: str = field(default_factory=_utcnow_iso)
    updated_at: str = field(default_factory=_utcnow_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "dependencies": [d.to_dict() for d in self.dependencies],
            "workers": [w.to_dict() for w in self.workers],
            "gates": [g.to_dict() for g in self.gates],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        return cls(
            title=data["title"],
            description=data.get("description", ""),
            status=_coerce_enum(TaskStatus, data.get("status", "planned")),
            task_id=data.get("task_id") or _new_id(),
            dependencies=[
                TaskDependency.from_dict(d)
                for d in (data.get("dependencies") or [])
            ],
            workers=[
                WorkerAssignment.from_dict(w)
                for w in (data.get("workers") or [])
            ],
            gates=[
                GateEvidence.from_dict(g) for g in (data.get("gates") or [])
            ],
            created_at=data.get("created_at") or _utcnow_iso(),
            updated_at=data.get("updated_at") or _utcnow_iso(),
        )


@dataclass
class Job:
    """A JARVIS mission decomposed into tasks, with audit log and gates.

    All state changes flow through methods on this class; callers
    should not mutate ``status``, ``events``, or ``gates`` directly.
    """

    title: str
    description: str = ""
    job_id: str = field(default_factory=_new_id)
    schema_version: int = SCHEMA_VERSION
    tasks: list[Task] = field(default_factory=list)
    events: list[JobEvent] = field(default_factory=list)
    gates: list[GateEvidence] = field(default_factory=list)
    created_at: str = field(default_factory=_utcnow_iso)
    updated_at: str = field(default_factory=_utcnow_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    # ── Internals ──

    def _touch(self) -> None:
        self.updated_at = _utcnow_iso()

    def _append_event(self, event: JobEvent) -> JobEvent:
        self.events.append(event)
        self._touch()
        return event

    def _index(self) -> dict[str, Task]:
        return {t.task_id: t for t in self.tasks}

    def _assert_acyclic(self) -> None:
        # Build adjacency over blocking edges only — informs edges don't
        # gate execution so cycles among them are harmless.
        adj: dict[str, list[str]] = {t.task_id: [] for t in self.tasks}
        for task in self.tasks:
            for dep in task.dependencies:
                if dep.kind != "blocks":
                    continue
                # Edge: predecessor -> successor.
                adj.setdefault(dep.predecessor_task_id, []).append(
                    dep.successor_task_id
                )
                adj.setdefault(dep.successor_task_id, adj.get(
                    dep.successor_task_id, []
                ))
        # 3-color DFS to detect any back edge.
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in adj}
        for start in list(adj.keys()):
            if color[start] != WHITE:
                continue
            stack: list[tuple[str, int]] = [(start, 0)]
            color[start] = GRAY
            while stack:
                node, i = stack[-1]
                neighbors = adj.get(node, [])
                if i < len(neighbors):
                    stack[-1] = (node, i + 1)
                    nxt = neighbors[i]
                    if nxt == node:
                        raise CyclicDependencyError(
                            f"self-dependency on task {node!r}"
                        )
                    c = color.get(nxt, WHITE)
                    if c == GRAY:
                        raise CyclicDependencyError(
                            f"cycle detected through task {nxt!r}"
                        )
                    if c == WHITE:
                        color[nxt] = GRAY
                        stack.append((nxt, 0))
                else:
                    color[node] = BLACK
                    stack.pop()

    # ── Lookups ──

    def get_task(self, task_id: str) -> Task:
        for t in self.tasks:
            if t.task_id == task_id:
                return t
        raise UnknownTaskError(f"no task with id {task_id!r}")

    def predecessors_of(self, task_id: str) -> list[Task]:
        task = self.get_task(task_id)
        idx = self._index()
        out: list[Task] = []
        for dep in task.dependencies:
            if dep.kind != "blocks":
                continue
            if dep.successor_task_id != task_id:
                # Stored on this task but pointing elsewhere — skip.
                continue
            pred = idx.get(dep.predecessor_task_id)
            if pred is None:
                raise UnknownTaskError(
                    f"predecessor {dep.predecessor_task_id!r} of "
                    f"{task_id!r} not present"
                )
            out.append(pred)
        return out

    def can_start(self, task_id: str) -> tuple[bool, list[str]]:
        preds = self.predecessors_of(task_id)
        blocking = [p.task_id for p in preds if p.status != TaskStatus.DONE]
        return (not blocking, blocking)

    # ── Mutations ──

    def add_task(self, task: Task) -> JobEvent:
        if any(t.task_id == task.task_id for t in self.tasks):
            raise JobModelError(
                f"task id {task.task_id!r} already present on job"
            )
        self.tasks.append(task)
        return self._append_event(JobEvent(
            event_type="task_added",
            task_id=task.task_id,
            message=task.title,
        ))

    def add_dependency(self, dep: TaskDependency) -> JobEvent:
        # Both endpoints must exist.
        self.get_task(dep.predecessor_task_id)
        successor = self.get_task(dep.successor_task_id)
        # Self-edges fail fast with a clear error.
        if dep.predecessor_task_id == dep.successor_task_id:
            raise CyclicDependencyError(
                f"self-dependency on task {dep.successor_task_id!r}"
            )
        successor.dependencies.append(dep)
        try:
            self._assert_acyclic()
        except CyclicDependencyError:
            # Roll back the speculative append so the job is unchanged.
            successor.dependencies.pop()
            raise
        return self._append_event(JobEvent(
            event_type="dependency_added",
            task_id=dep.successor_task_id,
            message=(
                f"{dep.predecessor_task_id} -> {dep.successor_task_id} "
                f"({dep.kind})"
            ),
        ))

    def assign_worker(
        self, task_id: str, worker: WorkerAssignment,
    ) -> JobEvent:
        task = self.get_task(task_id)
        task.workers.append(worker)
        task.updated_at = _utcnow_iso()
        return self._append_event(JobEvent(
            event_type="worker_assigned",
            task_id=task_id,
            message=f"{worker.worker} ({worker.role})",
        ))

    def record_gate(self, task_id: str, gate: GateEvidence) -> JobEvent:
        task = self.get_task(task_id)
        task.gates.append(gate)
        task.updated_at = _utcnow_iso()
        return self._append_event(JobEvent(
            event_type="gate_recorded",
            task_id=task_id,
            message=f"{gate.gate.value}={gate.outcome.value}",
        ))

    def record_job_gate(self, gate: GateEvidence) -> JobEvent:
        self.gates.append(gate)
        return self._append_event(JobEvent(
            event_type="job_gate_recorded",
            message=f"{gate.gate.value}={gate.outcome.value}",
        ))

    def note(
        self, message: str, task_id: Optional[str] = None,
    ) -> JobEvent:
        if task_id is not None:
            self.get_task(task_id)
        return self._append_event(JobEvent(
            event_type="event_note",
            task_id=task_id,
            message=message,
        ))

    def transition_task(
        self,
        task_id: str,
        target: TaskStatus,
        *,
        reason: str = "",
    ) -> JobEvent:
        task = self.get_task(task_id)
        current = task.status
        validate_transition(current, target)
        if target == TaskStatus.RUNNING:
            ok, blocking = self.can_start(task_id)
            if not ok:
                raise DependencyBlockedError(task_id, blocking)
        task.status = target
        task.updated_at = _utcnow_iso()
        return self._append_event(JobEvent(
            event_type="status_changed",
            task_id=task_id,
            from_status=current.value,
            to_status=target.value,
            message=reason,
        ))

    # ── Serialization ──

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "job_id": self.job_id,
            "title": self.title,
            "description": self.description,
            "tasks": [t.to_dict() for t in self.tasks],
            "events": [e.to_dict() for e in self.events],
            "gates": [g.to_dict() for g in self.gates],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Job":
        return cls(
            title=data["title"],
            description=data.get("description", ""),
            job_id=data.get("job_id") or _new_id(),
            schema_version=int(data.get("schema_version", SCHEMA_VERSION)),
            tasks=[Task.from_dict(t) for t in (data.get("tasks") or [])],
            events=[
                JobEvent.from_dict(e) for e in (data.get("events") or [])
            ],
            gates=[
                GateEvidence.from_dict(g) for g in (data.get("gates") or [])
            ],
            created_at=data.get("created_at") or _utcnow_iso(),
            updated_at=data.get("updated_at") or _utcnow_iso(),
            metadata=dict(data.get("metadata") or {}),
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent)

    @classmethod
    def from_json(cls, s: str) -> "Job":
        return cls.from_dict(json.loads(s))


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

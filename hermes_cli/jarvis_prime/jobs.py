"""Background jobs — in-memory stub registry.

Future wave PRs replace the in-memory dict with a persistent queue (e.g.
``~/.hermes/jarvis/jobs.jsonl``); the Job dataclass and registry helpers
keep the same signatures.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    """Lifecycle states for a background job."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass(frozen=True)
class Job:
    """A queued unit of work for a worker tier."""

    id: str
    kind: str
    status: JobStatus
    payload: Mapping[str, Any] = field(default_factory=dict)


_JOBS: dict[str, Job] = {}


def enqueue(kind: str, payload: Mapping[str, Any] | None = None) -> Job:
    """Add a new pending job to the in-memory registry."""
    job = Job(
        id=f"job-{len(_JOBS):06d}",
        kind=kind,
        status=JobStatus.PENDING,
        payload=dict(payload or {}),
    )
    _JOBS[job.id] = job
    return job


def get_job(job_id: str) -> Job | None:
    """Look up a queued job by id."""
    return _JOBS.get(job_id)

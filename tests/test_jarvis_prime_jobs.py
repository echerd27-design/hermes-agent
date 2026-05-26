"""Tests for ``hermes_cli.jarvis_prime.jobs`` (Wave 06).

Covers:
- ``TaskStatus`` enum shape and terminal states.
- Status transition validator (every legal edge plus a representative
  sample of illegal edges).
- Dependency-blocking semantics (``planned -> running`` requires every
  blocking predecessor to be ``DONE``).
- Cyclic-dependency rejection at edge insert time.
- The append-only ``JobEvent`` log produced by every mutating ``Job``
  method.
- Task-level and job-level ``GateEvidence`` recording.
- JSON round-trip across empty and fully populated jobs.

Hermetic test invariants are enforced by ``tests/conftest.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from hermes_cli.jarvis_prime.jobs import (  # noqa: E402
    SCHEMA_VERSION,
    CyclicDependencyError,
    DependencyBlockedError,
    GateEvidence,
    GateOutcome,
    GateType,
    InvalidTransitionError,
    Job,
    JobEvent,
    Task,
    TaskDependency,
    TaskStatus,
    UnknownTaskError,
    WorkerAssignment,
    validate_transition,
)


def _iso_ish(s: str) -> bool:
    return isinstance(s, str) and len(s) > 0 and s.endswith("Z")


# ── Enum ───────────────────────────────────────────────────────────────────


class TestTaskStatusEnum:
    def test_has_exactly_seven_members(self):
        members = {m.name for m in TaskStatus}
        assert members == {
            "PLANNED", "RUNNING", "VALIDATING", "BLOCKED",
            "FAILED", "DONE", "CANCELLED",
        }

    def test_values_are_expected_lowercase_strings(self):
        assert {m.value for m in TaskStatus} == {
            "planned", "running", "validating", "blocked",
            "failed", "done", "cancelled",
        }

    def test_terminal_states_are_done_and_cancelled(self):
        # Terminal == no outgoing transition is legal.
        for source in TaskStatus:
            for target in TaskStatus:
                if source == target:
                    continue
                if source in (TaskStatus.DONE, TaskStatus.CANCELLED):
                    with pytest.raises(InvalidTransitionError):
                        validate_transition(source, target)


# ── Status transitions ─────────────────────────────────────────────────────


class TestValidateTransition:
    @pytest.mark.parametrize("source,target", [
        (TaskStatus.PLANNED, TaskStatus.RUNNING),
        (TaskStatus.PLANNED, TaskStatus.BLOCKED),
        (TaskStatus.RUNNING, TaskStatus.VALIDATING),
        (TaskStatus.RUNNING, TaskStatus.BLOCKED),
        (TaskStatus.RUNNING, TaskStatus.FAILED),
        (TaskStatus.VALIDATING, TaskStatus.DONE),
        (TaskStatus.VALIDATING, TaskStatus.FAILED),
        (TaskStatus.VALIDATING, TaskStatus.RUNNING),  # soft-miss rerun
        (TaskStatus.BLOCKED, TaskStatus.PLANNED),
        (TaskStatus.FAILED, TaskStatus.PLANNED),      # retry re-queues
    ])
    def test_legal_edges_pass(self, source, target):
        assert validate_transition(source, target) is None

    @pytest.mark.parametrize("source", [
        TaskStatus.PLANNED, TaskStatus.RUNNING, TaskStatus.VALIDATING,
        TaskStatus.BLOCKED, TaskStatus.FAILED,
    ])
    def test_cancel_from_every_nonterminal_state(self, source):
        assert validate_transition(source, TaskStatus.CANCELLED) is None

    def test_self_loop_disallowed(self):
        with pytest.raises(InvalidTransitionError, match="self-loops"):
            validate_transition(TaskStatus.RUNNING, TaskStatus.RUNNING)

    def test_done_to_anything_raises(self):
        with pytest.raises(InvalidTransitionError):
            validate_transition(TaskStatus.DONE, TaskStatus.PLANNED)

    def test_cancelled_to_anything_raises(self):
        with pytest.raises(InvalidTransitionError):
            validate_transition(TaskStatus.CANCELLED, TaskStatus.PLANNED)

    def test_failed_to_running_disallowed_direct(self):
        # Retries must re-queue through PLANNED so deps are re-evaluated.
        with pytest.raises(InvalidTransitionError):
            validate_transition(TaskStatus.FAILED, TaskStatus.RUNNING)

    def test_invalid_transition_message_lists_valid_targets(self):
        with pytest.raises(InvalidTransitionError) as ei:
            validate_transition(TaskStatus.PLANNED, TaskStatus.DONE)
        assert "valid targets" in str(ei.value)
        assert "running" in str(ei.value)


# ── Construction ──────────────────────────────────────────────────────────


class TestJobConstruction:
    def test_job_auto_assigns_id_and_timestamps(self):
        j = Job(title="m")
        assert isinstance(j.job_id, str) and len(j.job_id) >= 16
        assert _iso_ish(j.created_at)
        assert _iso_ish(j.updated_at)
        assert j.schema_version == SCHEMA_VERSION

    def test_task_auto_assigns_id_and_timestamps(self):
        t = Task(title="t")
        assert isinstance(t.task_id, str) and len(t.task_id) >= 16
        assert _iso_ish(t.created_at)
        assert t.status == TaskStatus.PLANNED

    def test_ids_unique_across_constructions(self):
        ids = {Task(title=f"t{i}").task_id for i in range(50)}
        assert len(ids) == 50


# ── Dependency blocking ───────────────────────────────────────────────────


class TestDependencyBlocking:
    def _build(self):
        job = Job(title="job")
        a = Task(title="a")
        b = Task(title="b")
        job.add_task(a)
        job.add_task(b)
        job.add_dependency(TaskDependency(
            predecessor_task_id=a.task_id,
            successor_task_id=b.task_id,
        ))
        return job, a, b

    def test_unmet_blocking_dep_prevents_running(self):
        job, a, b = self._build()
        with pytest.raises(DependencyBlockedError) as ei:
            job.transition_task(b.task_id, TaskStatus.RUNNING)
        assert ei.value.task_id == b.task_id
        assert a.task_id in ei.value.blocking_ids

    def test_unblocks_when_predecessor_reaches_done(self):
        job, a, b = self._build()
        job.transition_task(a.task_id, TaskStatus.RUNNING)
        job.transition_task(a.task_id, TaskStatus.VALIDATING)
        job.transition_task(a.task_id, TaskStatus.DONE)
        # Now b should be startable.
        job.transition_task(b.task_id, TaskStatus.RUNNING)
        assert job.get_task(b.task_id).status == TaskStatus.RUNNING

    def test_informs_dependency_does_not_block(self):
        job = Job(title="job")
        a = Task(title="a")
        b = Task(title="b")
        job.add_task(a)
        job.add_task(b)
        job.add_dependency(TaskDependency(
            predecessor_task_id=a.task_id,
            successor_task_id=b.task_id,
            kind="informs",
        ))
        # `a` is still PLANNED; informs is advisory only.
        job.transition_task(b.task_id, TaskStatus.RUNNING)
        assert job.get_task(b.task_id).status == TaskStatus.RUNNING

    def test_unknown_task_raises(self):
        job = Job(title="job")
        with pytest.raises(UnknownTaskError):
            job.transition_task("nonexistent", TaskStatus.RUNNING)


# ── Cycle detection ───────────────────────────────────────────────────────


class TestCyclicDependencyDetection:
    def test_self_edge_rejected(self):
        job = Job(title="job")
        a = Task(title="a")
        job.add_task(a)
        with pytest.raises(CyclicDependencyError):
            job.add_dependency(TaskDependency(
                predecessor_task_id=a.task_id,
                successor_task_id=a.task_id,
            ))

    def test_two_node_cycle_rejected(self):
        job = Job(title="job")
        a = Task(title="a")
        b = Task(title="b")
        job.add_task(a)
        job.add_task(b)
        job.add_dependency(TaskDependency(
            predecessor_task_id=a.task_id,
            successor_task_id=b.task_id,
        ))
        with pytest.raises(CyclicDependencyError):
            job.add_dependency(TaskDependency(
                predecessor_task_id=b.task_id,
                successor_task_id=a.task_id,
            ))
        # Speculative edge must have been rolled back.
        assert len(job.get_task(a.task_id).dependencies) == 0


# ── Event log ─────────────────────────────────────────────────────────────


class TestJobEventLog:
    def test_add_task_emits_event(self):
        job = Job(title="job")
        ev = job.add_task(Task(title="t"))
        assert isinstance(ev, JobEvent)
        assert ev.event_type == "task_added"
        assert ev.task_id is not None
        assert len(job.events) == 1

    def test_status_change_records_from_and_to(self):
        job = Job(title="job")
        t = Task(title="t")
        job.add_task(t)
        ev = job.transition_task(t.task_id, TaskStatus.RUNNING, reason="go")
        assert ev.event_type == "status_changed"
        assert ev.from_status == "planned"
        assert ev.to_status == "running"
        assert ev.message == "go"

    def test_each_mutation_appends_exactly_one_event(self):
        job = Job(title="job")
        a = Task(title="a")
        b = Task(title="b")
        job.add_task(a)        # 1
        job.add_task(b)        # 2
        job.add_dependency(    # 3
            TaskDependency(
                predecessor_task_id=a.task_id,
                successor_task_id=b.task_id,
            )
        )
        job.assign_worker(     # 4
            a.task_id,
            WorkerAssignment(worker="claude_code_builder"),
        )
        job.record_gate(       # 5
            a.task_id,
            GateEvidence(gate=GateType.BUILD, outcome=GateOutcome.PASS),
        )
        job.record_job_gate(   # 6
            GateEvidence(
                gate=GateType.OWNER_APPROVAL,
                outcome=GateOutcome.OWNER_APPROVED,
            )
        )
        job.note("free-form annotation")  # 7
        assert len(job.events) == 7
        assert [e.event_type for e in job.events] == [
            "task_added",
            "task_added",
            "dependency_added",
            "worker_assigned",
            "gate_recorded",
            "job_gate_recorded",
            "event_note",
        ]


# ── Job-level gates ───────────────────────────────────────────────────────


class TestJobLevelGates:
    def test_record_job_gate_attaches_to_job_not_task(self):
        job = Job(title="job")
        t = Task(title="t")
        job.add_task(t)
        job.record_job_gate(GateEvidence(
            gate=GateType.RELEASE, outcome=GateOutcome.PASS,
        ))
        assert len(job.gates) == 1
        assert len(job.get_task(t.task_id).gates) == 0
        assert job.gates[0].gate == GateType.RELEASE

    def test_record_gate_attaches_to_task(self):
        job = Job(title="job")
        t = Task(title="t")
        job.add_task(t)
        job.record_gate(t.task_id, GateEvidence(
            gate=GateType.TEST, outcome=GateOutcome.PASS,
        ))
        assert len(job.gates) == 0
        assert len(job.get_task(t.task_id).gates) == 1


# ── Serialization ─────────────────────────────────────────────────────────


class TestSerializationRoundTrip:
    def test_empty_job_round_trips(self):
        j = Job(title="empty")
        restored = Job.from_json(j.to_json())
        assert restored.to_dict() == j.to_dict()

    def test_schema_version_present_in_payload(self):
        payload = json.loads(Job(title="m").to_json())
        assert payload["schema_version"] == SCHEMA_VERSION

    def test_enum_values_serialize_as_strings(self):
        job = Job(title="m")
        t = Task(title="t")
        job.add_task(t)
        job.record_gate(t.task_id, GateEvidence(
            gate=GateType.SECURITY, outcome=GateOutcome.FAIL,
        ))
        payload = json.loads(job.to_json())
        assert payload["tasks"][0]["status"] == "planned"
        assert payload["tasks"][0]["gates"][0]["gate"] == "security"
        assert payload["tasks"][0]["gates"][0]["outcome"] == "fail"

    def test_full_job_round_trips_identically(self):
        job = Job(title="full", description="every shape exercised")
        job.metadata["wave"] = "06"
        a = Task(title="alpha")
        b = Task(title="beta")
        job.add_task(a)
        job.add_task(b)
        job.add_dependency(TaskDependency(
            predecessor_task_id=a.task_id,
            successor_task_id=b.task_id,
        ))
        job.assign_worker(a.task_id, WorkerAssignment(
            worker="claude_code_builder", notes="primary",
        ))
        job.record_gate(a.task_id, GateEvidence(
            gate=GateType.BUILD, outcome=GateOutcome.PASS,
            summary="compile ok", artifacts=["jobs.py"],
        ))
        job.record_job_gate(GateEvidence(
            gate=GateType.RELEASE, outcome=GateOutcome.PASS,
        ))
        job.transition_task(a.task_id, TaskStatus.RUNNING)
        job.transition_task(a.task_id, TaskStatus.VALIDATING)
        job.transition_task(a.task_id, TaskStatus.DONE)
        job.note("ready for review")

        restored = Job.from_json(job.to_json())
        assert restored.to_dict() == job.to_dict()
        # Spot-check structural fidelity.
        assert restored.get_task(a.task_id).status == TaskStatus.DONE
        assert restored.metadata["wave"] == "06"
        assert any(
            e.event_type == "status_changed" for e in restored.events
        )

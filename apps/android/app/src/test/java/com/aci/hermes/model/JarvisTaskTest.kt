package com.aci.hermes.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class JarvisTaskTest {

    private fun sampleTask(
        gates: List<JarvisGateStatus> = emptyList(),
        evidence: List<VerificationEvidence> = emptyList(),
    ) = JarvisTask(
        id = "task-1",
        jobId = "job-1",
        mission = "Scaffold low-clearance check",
        assignedRoute = "claude-code-builder",
        status = JarvisTaskStatus.IN_PROGRESS,
        gates = gates,
        evidence = evidence,
        createdAtEpochMs = 1_700_000_000_000L,
        updatedAtEpochMs = 1_700_000_001_000L,
    )

    @Test
    fun defaults_emptyGatesEmptyEvidenceNullResult() {
        val task = sampleTask()
        assertTrue(task.gates.isEmpty())
        assertTrue(task.evidence.isEmpty())
        assertNull(task.result)
        assertNull(task.nextAction)
    }

    @Test
    fun copy_attachesGatesAndEvidence() {
        val original = sampleTask()
        val gate = JarvisGateStatus(JarvisGate.PLANNING, JarvisGateResult.PASSED)
        val evidence = VerificationEvidence(
            id = "ev-1",
            taskId = original.id,
            gate = JarvisGate.PLANNING,
            type = VerificationEvidenceType.MANUAL_CHECK,
            summary = "Mission scope confirmed.",
            verified = true,
            collectedAtEpochMs = 1_700_000_000_500L,
        )
        val copy = original.copy(gates = listOf(gate), evidence = listOf(evidence))
        assertEquals(1, copy.gates.size)
        assertEquals(1, copy.evidence.size)
        assertEquals(JarvisGate.PLANNING, copy.gates.first().gate)
    }

    @Test
    fun statusEnum_coversFullLifecycle() {
        val expected = setOf(
            JarvisTaskStatus.DRAFT,
            JarvisTaskStatus.ASSIGNED,
            JarvisTaskStatus.IN_PROGRESS,
            JarvisTaskStatus.AWAITING_VERIFICATION,
            JarvisTaskStatus.BLOCKED_ON_GATE,
            JarvisTaskStatus.AWAITING_OWNER_APPROVAL,
            JarvisTaskStatus.COMPLETED,
            JarvisTaskStatus.FAILED,
            JarvisTaskStatus.CANCELLED,
        )
        assertEquals(expected, JarvisTaskStatus.values().toSet())
    }
}

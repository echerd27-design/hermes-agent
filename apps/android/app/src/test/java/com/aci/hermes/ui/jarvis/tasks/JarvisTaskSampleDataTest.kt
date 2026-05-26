package com.aci.hermes.ui.jarvis.tasks

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class JarvisTaskSampleDataTest {

    @Test
    fun sampleData_hasFourEntries() {
        assertEquals(4, JarvisTaskSampleData.samples.size)
    }

    @Test
    fun sampleData_idsAreUnique() {
        val ids = JarvisTaskSampleData.samples.map { it.id }
        assertEquals(ids.size, ids.toSet().size)
    }

    @Test
    fun sampleData_titlesAreNonBlank() {
        for (task in JarvisTaskSampleData.samples) {
            assertTrue("title blank for ${task.id}", task.title.isNotBlank())
        }
    }

    @Test
    fun sampleData_blockedReasonImpliesBlockedSignal() {
        for (task in JarvisTaskSampleData.samples) {
            if (task.blockedReason != null) {
                val phaseSaysBlocked = task.phase == TaskPhase.BLOCKED
                val anyStageBlocked =
                    task.workerLane.stages.any { it.state is WorkerLaneStageState.Blocked }
                assertTrue(
                    "task ${task.id} has blockedReason but no blocked signal",
                    phaseSaysBlocked || anyStageBlocked
                )
                assertTrue(task.isBlocked)
            } else {
                assertFalse(task.isBlocked)
            }
        }
    }

    @Test
    fun sampleData_unblockGuidanceRequiresBlockedReason() {
        for (task in JarvisTaskSampleData.samples) {
            if (task.unblockGuidance != null) {
                assertNotNull(
                    "task ${task.id} has unblock guidance but no blocked reason",
                    task.blockedReason
                )
            }
        }
    }

    @Test
    fun sampleData_publishedTaskHasAllStagesDone() {
        val published = JarvisTaskSampleData.samples.first { it.id == "task-003" }
        assertEquals(TaskPhase.PUBLISHED, published.phase)
        assertTrue(
            published.workerLane.stages.all { it.state == WorkerLaneStageState.Done }
        )
    }

    @Test
    fun sampleData_planningTaskHasOnlyPlannerActive() {
        val planning = JarvisTaskSampleData.samples.first { it.id == "task-004" }
        assertEquals(TaskPhase.PLANNING, planning.phase)
        assertEquals(WorkerLabel.PLANNER, planning.currentWorker)
        assertNull(planning.proofLink)
        assertFalse(planning.rollbackAvailable)
        val plannerStage = planning.workerLane.stages.first { it.label == WorkerLabel.PLANNER }
        assertEquals(WorkerLaneStageState.Active, plannerStage.state)
        val others = planning.workerLane.stages.filter { it.label != WorkerLabel.PLANNER }
        assertTrue(others.all { it.state == WorkerLaneStageState.Pending })
    }

    @Test
    fun previewProvider_enumeratesAllSamples() {
        val provider = JarvisTaskCardPreviewProvider()
        val values = provider.values.toList()
        assertEquals(JarvisTaskSampleData.samples.size, values.size)
        assertEquals(JarvisTaskSampleData.samples, values)
    }
}

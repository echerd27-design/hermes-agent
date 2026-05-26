package com.aci.hermes.ui.jarvis.tasks

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class WorkerLaneUiStateTest {

    @Test
    fun workerLane_allPendingHasSevenStagesInPipelineOrder() {
        val state = WorkerLaneUiState.allPending()
        assertEquals(7, state.stages.size)
        assertEquals(WorkerLabel.pipeline, state.stages.map { it.label })
        assertTrue(state.stages.all { it.state == WorkerLaneStageState.Pending })
    }

    @Test
    fun workerLane_rejectsWrongLength() {
        val short = WorkerLabel.pipeline.dropLast(1).map {
            WorkerLaneStage(it, WorkerLaneStageState.Pending)
        }
        assertThrows(IllegalArgumentException::class.java) {
            WorkerLaneUiState(short)
        }
    }

    @Test
    fun workerLane_rejectsOutOfOrderStages() {
        val swapped = WorkerLabel.pipeline.toMutableList().apply {
            val a = this[0]
            this[0] = this[1]
            this[1] = a
        }.map { WorkerLaneStage(it, WorkerLaneStageState.Pending) }
        assertThrows(IllegalArgumentException::class.java) {
            WorkerLaneUiState(swapped)
        }
    }

    @Test
    fun workerLane_acceptsCanonicalOrder() {
        val canonical = WorkerLabel.pipeline.map {
            WorkerLaneStage(it, WorkerLaneStageState.Done)
        }
        val state = WorkerLaneUiState(canonical)
        assertEquals(7, state.stages.size)
    }

    @Test
    fun workerLane_acceptsBlockedStateWithReason() {
        val stages = WorkerLabel.pipeline.mapIndexed { index, label ->
            val s = if (index == 5) {
                WorkerLaneStageState.Blocked("Owner gate not granted")
            } else {
                WorkerLaneStageState.Pending
            }
            WorkerLaneStage(label, s)
        }
        val state = WorkerLaneUiState(stages)
        val blocked = state.stages[5].state as WorkerLaneStageState.Blocked
        assertEquals("Owner gate not granted", blocked.reason)
    }
}

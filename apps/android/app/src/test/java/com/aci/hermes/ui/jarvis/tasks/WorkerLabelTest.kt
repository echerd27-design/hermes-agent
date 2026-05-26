package com.aci.hermes.ui.jarvis.tasks

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class WorkerLabelTest {

    @Test
    fun workerLabel_pipelineIsSevenInProductOrder() {
        val expected = listOf(
            WorkerLabel.PLANNER,
            WorkerLabel.NAVIGATOR,
            WorkerLabel.EDITOR,
            WorkerLabel.EXECUTOR,
            WorkerLabel.REVIEWER,
            WorkerLabel.VERIFIER,
            WorkerLabel.PUBLISHER
        )
        assertEquals(expected, WorkerLabel.pipeline)
    }

    @Test
    fun workerLabel_orderMatchesPipelineIndex() {
        WorkerLabel.pipeline.forEachIndexed { index, label ->
            assertEquals("order mismatch for $label", index, label.order)
        }
    }

    @Test
    fun workerLabel_displayLabelsAreDistinctAndNonBlank() {
        val labels = WorkerLabel.values().map { it.displayLabel }
        assertEquals(labels.size, labels.toSet().size)
        for (label in labels) {
            assertTrue("label blank", label.isNotBlank())
        }
    }

    @Test
    fun workerLabel_displayLabelsAreProductized() {
        val allowlist = setOf(
            "Planner", "Navigator", "Editor", "Executor",
            "Reviewer", "Verifier", "Publisher"
        )
        for (label in WorkerLabel.values()) {
            assertTrue(
                "unexpected worker label: ${label.displayLabel}",
                label.displayLabel in allowlist
            )
        }
    }
}

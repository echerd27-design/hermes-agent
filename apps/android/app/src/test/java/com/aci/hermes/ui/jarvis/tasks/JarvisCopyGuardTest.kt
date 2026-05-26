package com.aci.hermes.ui.jarvis.tasks

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class JarvisCopyGuardTest {

    private val forbiddenNames = listOf(
        "claude", "codex", "openhuman", "hyperagent",
        "autogen", "langgraph", "crewai", "paperclip"
    )

    private fun stringsForTask(task: TaskCardUiState): List<String> {
        val stageReasons = task.workerLane.stages.mapNotNull { stage ->
            (stage.state as? WorkerLaneStageState.Blocked)?.reason
        }
        return listOfNotNull(
            task.id,
            task.title,
            task.blockedReason,
            task.unblockGuidance,
            task.proofLink
        ) + stageReasons
    }

    @Test
    fun forbiddenNames_neverAppearInSampleData() {
        for (task in JarvisTaskSampleData.samples) {
            for (text in stringsForTask(task)) {
                val lower = text.lowercase()
                for (forbidden in forbiddenNames) {
                    assertFalse(
                        "task ${task.id} text contains forbidden name '$forbidden': '$text'",
                        lower.contains(forbidden)
                    )
                }
            }
        }
    }

    @Test
    fun jarvisProductNameIsPresentInSampleData() {
        val allText = JarvisTaskSampleData.samples
            .flatMap { stringsForTask(it) }
            .joinToString(" ")
            .lowercase()
        assertTrue(
            "expected 'jarvis prime' or 'jarvis' to appear in sample data",
            allText.contains("jarvis prime") || allText.contains("jarvis")
        )
    }

    @Test
    fun workerLabelsAreProductized() {
        val allowlist = setOf(
            "Planner", "Navigator", "Editor", "Executor",
            "Reviewer", "Verifier", "Publisher"
        )
        for (label in WorkerLabel.values()) {
            assertTrue(
                "worker label '${label.displayLabel}' is not productized",
                label.displayLabel in allowlist
            )
        }
    }
}

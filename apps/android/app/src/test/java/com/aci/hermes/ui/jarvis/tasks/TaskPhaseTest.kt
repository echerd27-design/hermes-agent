package com.aci.hermes.ui.jarvis.tasks

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class TaskPhaseTest {

    @Test
    fun taskPhase_hasExpectedSevenValues() {
        assertEquals(7, TaskPhase.values().size)
    }

    @Test
    fun taskPhase_displayLabelsAreNonBlankAndHumanReadable() {
        for (phase in TaskPhase.values()) {
            assertTrue("label blank for $phase", phase.displayLabel.isNotBlank())
            assertNotEquals(
                "displayLabel should not equal enum name for $phase",
                phase.name,
                phase.displayLabel
            )
        }
    }

    @Test
    fun taskPhase_blockedExists() {
        val blocked = TaskPhase.values().firstOrNull { it == TaskPhase.BLOCKED }
        assertEquals(TaskPhase.BLOCKED, blocked)
        assertEquals("Blocked", TaskPhase.BLOCKED.displayLabel)
    }
}

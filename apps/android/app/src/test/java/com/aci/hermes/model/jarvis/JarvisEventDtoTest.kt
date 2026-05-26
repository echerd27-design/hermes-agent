package com.aci.hermes.model.jarvis

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Test

class JarvisEventDtoTest {

    private fun sampleEvent(
        eventType: String = "task.updated",
        taskId: String? = null,
    ) = JarvisEventDto(
        eventType = eventType,
        timestampEpochMs = 1_700_000_003_000L,
        message = "Task updated.",
        payloadSummary = "phase=BUILD risk=NORMAL",
        taskId = taskId,
    )

    @Test
    fun defaults_taskIdIsNull() {
        val event = sampleEvent()
        assertNull(event.taskId)
    }

    @Test
    fun copy_populatesTaskId() {
        val event = sampleEvent()
        val withTask = event.copy(taskId = "task-99")
        assertEquals("task-99", withTask.taskId)
        assertNull(event.taskId)
    }

    @Test
    fun equality_basedOnAllFields() {
        val a = sampleEvent()
        val b = sampleEvent()
        assertEquals(a, b)
        assertEquals(a.hashCode(), b.hashCode())

        val c = sampleEvent(eventType = "task.created")
        assertNotEquals(a, c)
    }
}

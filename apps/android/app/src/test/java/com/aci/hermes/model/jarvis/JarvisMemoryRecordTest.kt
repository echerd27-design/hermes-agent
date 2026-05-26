package com.aci.hermes.model.jarvis

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class JarvisMemoryRecordTest {

    private fun sampleRecord(
        id: String = "mem-1",
        confidence: Double = 0.75,
        editable: Boolean = true,
        removable: Boolean = true,
    ) = JarvisMemoryRecord(
        id = id,
        title = "Prefers concise summaries",
        summary = "User asked for shorter status updates twice this week.",
        source = "conversation",
        confidence = confidence,
        editable = editable,
        removable = removable,
    )

    @Test
    fun defaults_editableAndRemovableAreTrue() {
        val record = JarvisMemoryRecord(
            id = "mem-default",
            title = "Note",
            summary = "Something.",
            source = "observation",
            confidence = 0.5,
        )
        assertTrue(record.editable)
        assertTrue(record.removable)
    }

    @Test
    fun confidence_acceptsBoundaryValues() {
        val low = sampleRecord(confidence = 0.0)
        val high = sampleRecord(confidence = 1.0)
        assertEquals(0.0, low.confidence, 0.0)
        assertEquals(1.0, high.confidence, 0.0)
    }

    @Test
    fun copy_canFlipEditability() {
        val record = sampleRecord(editable = true, removable = true)
        val locked = record.copy(editable = false, removable = false)
        assertEquals(false, locked.editable)
        assertEquals(false, locked.removable)
        assertEquals(true, record.editable)
        assertEquals(true, record.removable)
    }

    @Test
    fun equality_basedOnAllFields() {
        val a = sampleRecord()
        val b = sampleRecord()
        assertEquals(a, b)
        assertEquals(a.hashCode(), b.hashCode())

        val c = sampleRecord(id = "mem-2")
        assertNotEquals(a, c)
    }
}

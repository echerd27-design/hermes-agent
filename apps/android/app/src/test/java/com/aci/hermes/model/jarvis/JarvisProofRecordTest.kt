package com.aci.hermes.model.jarvis

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class JarvisProofRecordTest {

    private fun sampleRecord(
        id: String = "proof-1",
        filesChanged: List<String> = emptyList(),
        testsRun: List<String> = emptyList(),
    ) = JarvisProofRecord(
        id = id,
        taskId = "task-7",
        action = "edit",
        evidenceSummary = "Updated rendering rules and added test.",
        timestampEpochMs = 1_700_000_002_000L,
        filesChanged = filesChanged,
        testsRun = testsRun,
    )

    @Test
    fun defaults_collectionsAreEmpty() {
        val record = sampleRecord()
        assertTrue(record.filesChanged.isEmpty())
        assertTrue(record.testsRun.isEmpty())
    }

    @Test
    fun copy_preservesListOrder() {
        val record = sampleRecord(
            filesChanged = listOf("a.kt", "b.kt", "c.kt"),
            testsRun = listOf("TestA", "TestB"),
        )
        val copy = record.copy(evidenceSummary = "Same files, new summary.")
        assertEquals(listOf("a.kt", "b.kt", "c.kt"), copy.filesChanged)
        assertEquals(listOf("TestA", "TestB"), copy.testsRun)
    }

    @Test
    fun equality_basedOnAllFields() {
        val a = sampleRecord()
        val b = sampleRecord()
        assertEquals(a, b)
        assertEquals(a.hashCode(), b.hashCode())

        val c = sampleRecord(id = "proof-2")
        assertNotEquals(a, c)
    }
}

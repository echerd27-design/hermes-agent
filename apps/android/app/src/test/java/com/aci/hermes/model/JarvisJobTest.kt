package com.aci.hermes.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class JarvisJobTest {

    private fun sampleJob(
        id: String = "job-1",
        tasks: List<JarvisTask> = emptyList(),
        ownerApproval: OwnerApprovalRequest? = null,
    ) = JarvisJob(
        id = id,
        title = "Wire low-clearance warning",
        description = "Add truck-safe reroute hint.",
        mode = JarvisJobMode.BUILDER,
        tasks = tasks,
        createdAtEpochMs = 1_700_000_000_000L,
        updatedAtEpochMs = 1_700_000_001_000L,
        ownerApproval = ownerApproval,
    )

    @Test
    fun defaults_emptyTaskListAndNullOwnerApproval() {
        val job = sampleJob()
        assertTrue(job.tasks.isEmpty())
        assertNull(job.ownerApproval)
    }

    @Test
    fun copy_preservesUneditedFields() {
        val original = sampleJob()
        val copy = original.copy(title = "Renamed job")
        assertEquals("Renamed job", copy.title)
        assertEquals(original.id, copy.id)
        assertEquals(original.mode, copy.mode)
        assertEquals(original.createdAtEpochMs, copy.createdAtEpochMs)
    }

    @Test
    fun equality_basedOnAllFields() {
        val a = sampleJob()
        val b = sampleJob()
        assertEquals(a, b)
        assertEquals(a.hashCode(), b.hashCode())

        val c = sampleJob(id = "job-2")
        assertNotEquals(a, c)
    }

    @Test
    fun allModes_areDistinct() {
        assertEquals(JarvisJobMode.values().toSet().size, JarvisJobMode.values().size)
    }
}

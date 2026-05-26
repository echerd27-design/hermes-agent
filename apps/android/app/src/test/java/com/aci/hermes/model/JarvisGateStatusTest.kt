package com.aci.hermes.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Test

class JarvisGateStatusTest {

    @Test
    fun allEightGates_arePresent() {
        val expected = setOf(
            JarvisGate.PLANNING,
            JarvisGate.BUILD,
            JarvisGate.REVIEW,
            JarvisGate.TEST,
            JarvisGate.SECURITY,
            JarvisGate.RELEASE,
            JarvisGate.OWNER_APPROVAL,
            JarvisGate.ROLLBACK,
        )
        assertEquals(expected, JarvisGate.values().toSet())
    }

    @Test
    fun allFiveResults_arePresent() {
        val expected = setOf(
            JarvisGateResult.PENDING,
            JarvisGateResult.PASSED,
            JarvisGateResult.FAILED,
            JarvisGateResult.REQUIRES_OWNER_APPROVAL,
            JarvisGateResult.SKIPPED,
        )
        assertEquals(expected, JarvisGateResult.values().toSet())
    }

    @Test
    fun defaults_notesAndCheckedAtAreNull() {
        val status = JarvisGateStatus(
            gate = JarvisGate.PLANNING,
            result = JarvisGateResult.PENDING,
        )
        assertNull(status.notes)
        assertNull(status.checkedAtEpochMs)
    }

    @Test
    fun equality_differsByResult() {
        val a = JarvisGateStatus(JarvisGate.SECURITY, JarvisGateResult.PASSED)
        val b = JarvisGateStatus(JarvisGate.SECURITY, JarvisGateResult.FAILED)
        assertNotEquals(a, b)
    }
}

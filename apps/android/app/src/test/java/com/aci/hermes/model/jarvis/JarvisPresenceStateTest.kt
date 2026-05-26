package com.aci.hermes.model.jarvis

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class JarvisPresenceStateTest {

    @Test
    fun values_containsAllTwelveStates() {
        val expected = setOf(
            JarvisPresenceState.IDLE,
            JarvisPresenceState.LISTENING,
            JarvisPresenceState.THINKING,
            JarvisPresenceState.SPEAKING,
            JarvisPresenceState.WORKING,
            JarvisPresenceState.WAITING_FOR_APPROVAL,
            JarvisPresenceState.SERIOUS_ACTION_PENDING,
            JarvisPresenceState.CRITICAL_ACTION_PENDING,
            JarvisPresenceState.BLOCKED,
            JarvisPresenceState.WARNING,
            JarvisPresenceState.COMPLETE,
            JarvisPresenceState.OFFLINE,
        )
        assertEquals(12, JarvisPresenceState.values().size)
        assertEquals(expected, JarvisPresenceState.values().toSet())
    }

    @Test
    fun valueOf_roundTripsKnownName() {
        assertEquals(JarvisPresenceState.IDLE, JarvisPresenceState.valueOf("IDLE"))
        assertEquals(
            JarvisPresenceState.WAITING_FOR_APPROVAL,
            JarvisPresenceState.valueOf("WAITING_FOR_APPROVAL"),
        )
    }

    @Test(expected = IllegalArgumentException::class)
    fun valueOf_unknownName_throws() {
        JarvisPresenceState.valueOf("NOT_A_STATE")
    }

    @Test
    fun entries_areDistinct() {
        assertTrue(JarvisPresenceState.values().toSet().size == JarvisPresenceState.values().size)
    }
}

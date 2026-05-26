package com.aci.hermes.ui.jarvis.presence

import org.junit.Assert.assertEquals
import org.junit.Test

class PresenceStateTest {

    @Test
    fun has_exactly_twelve_states() {
        assertEquals(12, PresenceState.values().size)
    }

    @Test
    fun canonical_order_matches_spec() {
        val expected = listOf(
            PresenceState.IDLE,
            PresenceState.LISTENING,
            PresenceState.THINKING,
            PresenceState.SPEAKING,
            PresenceState.WORKING,
            PresenceState.WAITING_FOR_APPROVAL,
            PresenceState.SERIOUS_ACTION_PENDING,
            PresenceState.CRITICAL_ACTION_PENDING,
            PresenceState.BLOCKED,
            PresenceState.WARNING,
            PresenceState.COMPLETE,
            PresenceState.OFFLINE,
        )
        assertEquals(expected, PresenceState.values().toList())
    }

    @Test
    fun no_duplicate_entries() {
        val all = PresenceState.values().toList()
        assertEquals(all.size, all.toSet().size)
    }
}

package com.aci.hermes.ui.jarvis.presence

import com.aci.hermes.ui.jarvis.design.JarvisColors
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PresenceUiTest {

    @Test
    fun every_state_has_a_non_blank_label() {
        for (state in PresenceState.values()) {
            assertFalse(
                "label for $state must be non-blank",
                PresenceUi.label(state).isBlank(),
            )
        }
    }

    @Test
    fun every_state_has_a_non_blank_content_description() {
        for (state in PresenceState.values()) {
            assertFalse(
                "contentDescription for $state must be non-blank",
                PresenceUi.contentDescription(state).isBlank(),
            )
        }
    }

    @Test
    fun every_state_resolves_to_a_known_token_color() {
        val tokens = setOf(
            JarvisColors.BaseNavy,
            JarvisColors.BaseBlack,
            JarvisColors.Gold,
            JarvisColors.Cyan,
            JarvisColors.Red,
            JarvisColors.Green,
            JarvisColors.MutedGray,
            JarvisColors.Warning,
        )
        for (state in PresenceState.values()) {
            assertTrue(
                "color for $state must be one of the JarvisColors tokens",
                PresenceUi.colorHex(state) in tokens,
            )
        }
    }

    @Test
    fun listening_thinking_speaking_working_all_use_cyan() {
        assertEquals(JarvisColors.Cyan, PresenceUi.colorHex(PresenceState.LISTENING))
        assertEquals(JarvisColors.Cyan, PresenceUi.colorHex(PresenceState.THINKING))
        assertEquals(JarvisColors.Cyan, PresenceUi.colorHex(PresenceState.SPEAKING))
        assertEquals(JarvisColors.Cyan, PresenceUi.colorHex(PresenceState.WORKING))
    }

    @Test
    fun approval_states_use_gold() {
        assertEquals(JarvisColors.Gold, PresenceUi.colorHex(PresenceState.WAITING_FOR_APPROVAL))
        assertEquals(JarvisColors.Gold, PresenceUi.colorHex(PresenceState.SERIOUS_ACTION_PENDING))
    }

    @Test
    fun critical_action_uses_red() {
        assertEquals(
            JarvisColors.Red,
            PresenceUi.colorHex(PresenceState.CRITICAL_ACTION_PENDING),
        )
    }

    @Test
    fun warning_uses_warning_color() {
        assertEquals(JarvisColors.Warning, PresenceUi.colorHex(PresenceState.WARNING))
    }

    @Test
    fun complete_uses_green() {
        assertEquals(JarvisColors.Green, PresenceUi.colorHex(PresenceState.COMPLETE))
    }

    @Test
    fun offline_and_blocked_use_muted_gray() {
        assertEquals(JarvisColors.MutedGray, PresenceUi.colorHex(PresenceState.OFFLINE))
        assertEquals(JarvisColors.MutedGray, PresenceUi.colorHex(PresenceState.BLOCKED))
    }

    @Test
    fun idle_uses_base_navy() {
        assertEquals(JarvisColors.BaseNavy, PresenceUi.colorHex(PresenceState.IDLE))
    }

    @Test
    fun content_descriptions_mention_jarvis_for_a11y_consistency() {
        for (state in PresenceState.values()) {
            assertTrue(
                "contentDescription for $state must mention 'Jarvis'",
                PresenceUi.contentDescription(state).contains("Jarvis"),
            )
        }
    }
}

package com.aci.hermes.ui.jarvis.emergency

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class EmergencyStopStateTest {

    @Test
    fun emergencyStopUiState_hasExactlyThreeStates() {
        val values = EmergencyStopUiState.values()
        assertEquals(3, values.size)
        assertTrue(values.contains(EmergencyStopUiState.Active))
        assertTrue(values.contains(EmergencyStopUiState.Confirming))
        assertTrue(values.contains(EmergencyStopUiState.Stopped))
    }

    @Test
    fun emergencyStopUiState_valueOf_roundTripsEveryConstant() {
        for (value in EmergencyStopUiState.values()) {
            assertEquals(value, EmergencyStopUiState.valueOf(value.name))
        }
    }

    @Test
    fun copy_title_matchesProductCopyExactly() {
        assertEquals("Stop Jarvis Prime", EmergencyStopCopy.TITLE)
    }

    @Test
    fun copy_description_matchesProductCopyExactly() {
        assertEquals(
            "Stops active tasks and blocks new risky actions until you resume.",
            EmergencyStopCopy.DESCRIPTION,
        )
    }

    @Test
    fun copy_dialogTitle_isStopJarvisPrimeQuestion() {
        assertEquals("Stop Jarvis Prime?", EmergencyStopCopy.CONFIRM_DIALOG_TITLE)
    }

    @Test
    fun copy_confirmAndCancelLabels_areDistinctAndNonEmpty() {
        assertTrue(EmergencyStopCopy.CONFIRM_LABEL.isNotBlank())
        assertTrue(EmergencyStopCopy.CANCEL_LABEL.isNotBlank())
        assertTrue(EmergencyStopCopy.CONFIRM_LABEL != EmergencyStopCopy.CANCEL_LABEL)
    }

    @Test
    fun copy_stoppedBadge_isNonEmpty() {
        assertNotNull(EmergencyStopCopy.STOPPED_BADGE)
        assertTrue(EmergencyStopCopy.STOPPED_BADGE.isNotBlank())
    }
}

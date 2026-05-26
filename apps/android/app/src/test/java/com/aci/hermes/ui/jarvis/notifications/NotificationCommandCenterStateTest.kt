package com.aci.hermes.ui.jarvis.notifications

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNotSame
import org.junit.Assert.assertTrue
import org.junit.Test

class NotificationCommandCenterStateTest {

    @Test
    fun default_returnsAllCategoriesDisabled() {
        val state = NotificationCommandCenterState.default()
        for (category in NotificationCategory.values()) {
            assertFalse(
                "category $category should default to disabled",
                state.isEnabled(category),
            )
        }
    }

    @Test
    fun default_coversEveryCategory() {
        val state = NotificationCommandCenterState.default()
        assertEquals(
            NotificationCategory.values().size,
            state.enabledByCategory.size,
        )
    }

    @Test
    fun withCategory_returnsNewInstance_doesNotMutateOriginal() {
        val original = NotificationCommandCenterState.default()
        val updated = original.withCategory(NotificationCategory.TASK_COMPLETED, true)

        assertNotSame(original, updated)
        assertFalse(original.isEnabled(NotificationCategory.TASK_COMPLETED))
        assertTrue(updated.isEnabled(NotificationCategory.TASK_COMPLETED))
    }

    @Test
    fun withCategory_otherCategoriesUnchanged() {
        val state = NotificationCommandCenterState.default()
            .withCategory(NotificationCategory.CRITICAL_WARNING, true)
        for (category in NotificationCategory.values()) {
            val expected = category == NotificationCategory.CRITICAL_WARNING
            assertEquals(
                "isEnabled mismatch for $category",
                expected,
                state.isEnabled(category),
            )
        }
    }

    @Test
    fun withCategory_toggleRoundTripsToDefault() {
        val toggled = NotificationCommandCenterState.default()
            .withCategory(NotificationCategory.GATEWAY_OFFLINE, true)
            .withCategory(NotificationCategory.GATEWAY_OFFLINE, false)
        assertEquals(NotificationCommandCenterState.default(), toggled)
    }

    @Test
    fun isEnabled_returnsFalseForCategoryNotInMap() {
        val state = NotificationCommandCenterState(enabledByCategory = emptyMap())
        for (category in NotificationCategory.values()) {
            assertFalse(state.isEnabled(category))
        }
    }

    @Test
    fun equality_isValueBased() {
        val a = NotificationCommandCenterState.default()
            .withCategory(NotificationCategory.TASK_BLOCKED, true)
        val b = NotificationCommandCenterState.default()
            .withCategory(NotificationCategory.TASK_BLOCKED, true)
        assertEquals(a, b)
        assertEquals(a.hashCode(), b.hashCode())

        val c = NotificationCommandCenterState.default()
            .withCategory(NotificationCategory.APPROVAL_NEEDED, true)
        assertNotEquals(a, c)
    }
}

package com.aci.hermes.ui.jarvis.notifications

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class NotificationCategoryTest {

    @Test
    fun categories_haveExactlyFiveRequiredValues() {
        val values = NotificationCategory.values()
        assertEquals(5, values.size)
        assertTrue(values.contains(NotificationCategory.TASK_COMPLETED))
        assertTrue(values.contains(NotificationCategory.TASK_BLOCKED))
        assertTrue(values.contains(NotificationCategory.APPROVAL_NEEDED))
        assertTrue(values.contains(NotificationCategory.CRITICAL_WARNING))
        assertTrue(values.contains(NotificationCategory.GATEWAY_OFFLINE))
    }

    @Test
    fun categories_areDeclaredInPromptOrder() {
        val expected = listOf(
            NotificationCategory.TASK_COMPLETED,
            NotificationCategory.TASK_BLOCKED,
            NotificationCategory.APPROVAL_NEEDED,
            NotificationCategory.CRITICAL_WARNING,
            NotificationCategory.GATEWAY_OFFLINE,
        )
        assertEquals(expected, NotificationCategory.values().toList())
    }

    @Test
    fun categories_haveStableSnakeCaseIds() {
        assertEquals("task_completed", NotificationCategory.TASK_COMPLETED.id)
        assertEquals("task_blocked", NotificationCategory.TASK_BLOCKED.id)
        assertEquals("approval_needed", NotificationCategory.APPROVAL_NEEDED.id)
        assertEquals("critical_warning", NotificationCategory.CRITICAL_WARNING.id)
        assertEquals("gateway_offline", NotificationCategory.GATEWAY_OFFLINE.id)
    }

    @Test
    fun categories_haveUniqueIds() {
        val ids = NotificationCategory.values().map { it.id }
        assertEquals(ids.size, ids.toSet().size)
    }

    @Test
    fun categories_haveNonEmptyDisplayNameAndDescription() {
        for (category in NotificationCategory.values()) {
            assertTrue("displayName empty for $category", category.displayName.isNotBlank())
            assertTrue("description empty for $category", category.description.isNotBlank())
        }
    }
}

package com.aci.hermes.ui.jarvis.notifications

enum class NotificationCategory(
    val id: String,
    val displayName: String,
    val description: String,
) {
    TASK_COMPLETED(
        id = "task_completed",
        displayName = "Task completed",
        description = "Tell me when Jarvis finishes a task you queued.",
    ),
    TASK_BLOCKED(
        id = "task_blocked",
        displayName = "Task blocked",
        description = "Tell me when Jarvis stops on a task that needs my input.",
    ),
    APPROVAL_NEEDED(
        id = "approval_needed",
        displayName = "Approval needed",
        description = "Tell me when Jarvis is waiting on owner approval before continuing.",
    ),
    CRITICAL_WARNING(
        id = "critical_warning",
        displayName = "Critical warning",
        description = "Tell me about safety, security, or rollback warnings I should not miss.",
    ),
    GATEWAY_OFFLINE(
        id = "gateway_offline",
        displayName = "Gateway offline",
        description = "Tell me when the Hermes gateway is unreachable from this device.",
    ),
}

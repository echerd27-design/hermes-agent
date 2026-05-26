package com.aci.hermes.ui.jarvis.notifications

data class NotificationCommandCenterState(
    val enabledByCategory: Map<NotificationCategory, Boolean>,
) {
    fun isEnabled(category: NotificationCategory): Boolean =
        enabledByCategory[category] ?: false

    fun withCategory(category: NotificationCategory, enabled: Boolean): NotificationCommandCenterState =
        copy(enabledByCategory = enabledByCategory + (category to enabled))

    companion object {
        fun default(): NotificationCommandCenterState =
            NotificationCommandCenterState(
                enabledByCategory = NotificationCategory.values().associateWith { false },
            )
    }
}

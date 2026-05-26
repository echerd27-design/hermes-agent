package com.aci.hermes.model.jarvis

enum class JarvisPresenceState {
    IDLE,
    LISTENING,
    THINKING,
    SPEAKING,
    WORKING,
    WAITING_FOR_APPROVAL,
    SERIOUS_ACTION_PENDING,
    CRITICAL_ACTION_PENDING,
    BLOCKED,
    WARNING,
    COMPLETE,
    OFFLINE,
}

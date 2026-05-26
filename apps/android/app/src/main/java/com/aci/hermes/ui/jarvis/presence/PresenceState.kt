package com.aci.hermes.ui.jarvis.presence

/**
 * Canonical Jarvis Prime presence states.
 *
 * Ordered to match the sequence the operating-layer spec uses, so any
 * UI list/stepper composes against a stable order without re-sorting.
 */
enum class PresenceState {
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

package com.aci.hermes.ui.jarvis.presence

import com.aci.hermes.ui.jarvis.design.JarvisColors

/**
 * Pure-Kotlin mapping from PresenceState to display surface: color token,
 * user-visible label, and accessibility sentence. No Compose imports —
 * the orb composable consumes this object so the data layer can be unit
 * tested without an Android runtime.
 */
object PresenceUi {

    fun colorHex(state: PresenceState): Long = when (state) {
        PresenceState.IDLE -> JarvisColors.BaseNavy
        PresenceState.LISTENING -> JarvisColors.Cyan
        PresenceState.THINKING -> JarvisColors.Cyan
        PresenceState.SPEAKING -> JarvisColors.Cyan
        PresenceState.WORKING -> JarvisColors.Cyan
        PresenceState.WAITING_FOR_APPROVAL -> JarvisColors.Gold
        PresenceState.SERIOUS_ACTION_PENDING -> JarvisColors.Gold
        PresenceState.CRITICAL_ACTION_PENDING -> JarvisColors.Red
        PresenceState.BLOCKED -> JarvisColors.MutedGray
        PresenceState.WARNING -> JarvisColors.Warning
        PresenceState.COMPLETE -> JarvisColors.Green
        PresenceState.OFFLINE -> JarvisColors.MutedGray
    }

    fun label(state: PresenceState): String = when (state) {
        PresenceState.IDLE -> "Idle"
        PresenceState.LISTENING -> "Listening"
        PresenceState.THINKING -> "Thinking"
        PresenceState.SPEAKING -> "Speaking"
        PresenceState.WORKING -> "Working"
        PresenceState.WAITING_FOR_APPROVAL -> "Waiting for approval"
        PresenceState.SERIOUS_ACTION_PENDING -> "Serious action pending"
        PresenceState.CRITICAL_ACTION_PENDING -> "Critical action pending"
        PresenceState.BLOCKED -> "Blocked"
        PresenceState.WARNING -> "Warning"
        PresenceState.COMPLETE -> "Complete"
        PresenceState.OFFLINE -> "Offline"
    }

    fun contentDescription(state: PresenceState): String = when (state) {
        PresenceState.IDLE -> "Jarvis is idle."
        PresenceState.LISTENING -> "Jarvis is listening."
        PresenceState.THINKING -> "Jarvis is thinking."
        PresenceState.SPEAKING -> "Jarvis is speaking."
        PresenceState.WORKING -> "Jarvis is working."
        PresenceState.WAITING_FOR_APPROVAL ->
            "Jarvis is waiting for your approval before proceeding."
        PresenceState.SERIOUS_ACTION_PENDING ->
            "Jarvis has a serious action pending your approval."
        PresenceState.CRITICAL_ACTION_PENDING ->
            "Jarvis has a critical action pending your approval."
        PresenceState.BLOCKED -> "Jarvis is blocked and cannot proceed."
        PresenceState.WARNING -> "Jarvis has a warning that needs attention."
        PresenceState.COMPLETE -> "Jarvis has completed the task."
        PresenceState.OFFLINE -> "Jarvis is offline."
    }
}

package com.aci.hermes.ui.jarvis.voice

object VoiceEducationContent {
    const val TITLE: String = "Voice input is optional"

    val BODY_PARAGRAPHS: List<String> = listOf(
        "Tap the microphone any time you want to speak instead of type. " +
            "Jarvis Prime only listens while you hold the button or while the capture screen is open.",
        "We do not listen in the background. We do not read your SMS or call log. " +
            "We do not start the microphone automatically.",
        "Microphone access is fully optional. The app keeps working if you decline, " +
            "and you can change your mind later in system settings.",
    )

    const val CONTINUE_LABEL: String = "Allow microphone"
    const val DECLINE_LABEL: String = "Not now"
    const val DENIED_HINT: String =
        "Microphone access was declined. You can keep using the app and re-enable it from Android settings any time."
}

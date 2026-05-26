package com.aci.hermes.ui.jarvis.voice

enum class VoiceStage {
    EDUCATION,
    REQUESTING_PERMISSION,
    READY,
    CAPTURING,
    REVIEWING,
    DENIED,
}

data class VoiceCaptureState(
    val stage: VoiceStage = VoiceStage.EDUCATION,
    val transcript: String = "",
    val error: String? = null,
)

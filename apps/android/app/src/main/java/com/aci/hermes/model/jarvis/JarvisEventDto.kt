package com.aci.hermes.model.jarvis

data class JarvisEventDto(
    val eventType: String,
    val timestampEpochMs: Long,
    val message: String,
    val payloadSummary: String,
    val taskId: String? = null,
)

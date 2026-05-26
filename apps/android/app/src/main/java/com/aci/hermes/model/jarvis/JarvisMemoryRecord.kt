package com.aci.hermes.model.jarvis

data class JarvisMemoryRecord(
    val id: String,
    val title: String,
    val summary: String,
    val source: String,
    val confidence: Double,
    val editable: Boolean = true,
    val removable: Boolean = true,
)

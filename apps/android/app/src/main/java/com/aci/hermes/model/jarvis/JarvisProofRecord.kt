package com.aci.hermes.model.jarvis

data class JarvisProofRecord(
    val id: String,
    val taskId: String,
    val action: String,
    val evidenceSummary: String,
    val timestampEpochMs: Long,
    val filesChanged: List<String> = emptyList(),
    val testsRun: List<String> = emptyList(),
)

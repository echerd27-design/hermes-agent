package com.aci.hermes.model

data class JarvisTask(
    val id: String,
    val jobId: String,
    val mission: String,
    val assignedRoute: String,
    val status: JarvisTaskStatus,
    val gates: List<JarvisGateStatus> = emptyList(),
    val evidence: List<VerificationEvidence> = emptyList(),
    val result: String? = null,
    val nextAction: String? = null,
    val createdAtEpochMs: Long,
    val updatedAtEpochMs: Long,
)

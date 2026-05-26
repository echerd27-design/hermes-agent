package com.aci.hermes.model.jarvis

data class JarvisTaskCard(
    val id: String,
    val title: String,
    val summary: String,
    val phase: String,
    val riskTier: JarvisRiskTier,
    val workerLabel: String,
    val createdAtEpochMs: Long,
    val updatedAtEpochMs: Long,
    val blockedReason: String? = null,
    val proofId: String? = null,
    val rollbackAvailable: Boolean = false,
)

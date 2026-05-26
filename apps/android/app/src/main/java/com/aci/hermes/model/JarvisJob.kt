package com.aci.hermes.model

data class JarvisJob(
    val id: String,
    val title: String,
    val description: String,
    val mode: JarvisJobMode,
    val tasks: List<JarvisTask> = emptyList(),
    val createdAtEpochMs: Long,
    val updatedAtEpochMs: Long,
    val ownerApproval: OwnerApprovalRequest? = null,
)

enum class JarvisJobMode {
    COMPANION,
    STRATEGY,
    CRITIC,
    OPERATOR,
    BUILDER,
    MOBILE_VOICE,
}

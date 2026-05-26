package com.aci.hermes.model

data class OwnerApprovalRequest(
    val id: String,
    val taskId: String,
    val reason: OwnerApprovalReason,
    val riskSummary: String,
    val recommendation: String,
    val status: OwnerApprovalStatus = OwnerApprovalStatus.PENDING,
    val requestedAtEpochMs: Long,
    val resolvedAtEpochMs: Long? = null,
    val resolutionNote: String? = null,
)

enum class OwnerApprovalReason {
    MERGE,
    FORCE_PUSH,
    DEPLOY,
    PUBLISH,
    DELETE_RECOVERED_SOURCE,
    MODIFY_SECRETS,
    CHANGE_DEFAULT_AGENTS,
    REGISTRY_MUTATION,
    SPEND_MONEY,
    EXTERNAL_SERVICE_CHANGE,
    DNS_CHANGE,
    APP_STORE_SUBMISSION,
}

enum class OwnerApprovalStatus {
    PENDING,
    APPROVED,
    REJECTED,
    EXPIRED,
}

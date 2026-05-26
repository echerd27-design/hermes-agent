package com.aci.hermes.model.jarvis

data class JarvisApprovalCard(
    val id: String,
    val title: String,
    val action: String,
    val riskTier: JarvisRiskTier,
    val impactSummary: String,
    val rollbackSummary: String,
    val requiresSecondConfirm: Boolean = false,
    val requiresExactPhrase: Boolean = false,
    val status: JarvisApprovalStatus = JarvisApprovalStatus.PENDING,
)

enum class JarvisApprovalStatus {
    PENDING,
    APPROVED,
    REJECTED,
    EXPIRED,
}

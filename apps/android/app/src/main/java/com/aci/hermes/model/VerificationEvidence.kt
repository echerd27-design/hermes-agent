package com.aci.hermes.model

data class VerificationEvidence(
    val id: String,
    val taskId: String,
    val gate: JarvisGate,
    val type: VerificationEvidenceType,
    val summary: String,
    val detailRef: String? = null,
    val verified: Boolean,
    val collectedAtEpochMs: Long,
)

enum class VerificationEvidenceType {
    TEST_RESULT,
    DIFF_REVIEW,
    LINT_RESULT,
    SECURITY_SCAN,
    BUILD_LOG,
    MANUAL_CHECK,
    LINK_CHECK,
    SCHEMA_VALIDATION,
}

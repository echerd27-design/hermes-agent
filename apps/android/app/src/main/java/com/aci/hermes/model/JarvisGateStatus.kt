package com.aci.hermes.model

data class JarvisGateStatus(
    val gate: JarvisGate,
    val result: JarvisGateResult,
    val notes: String? = null,
    val checkedAtEpochMs: Long? = null,
)

enum class JarvisGate {
    PLANNING,
    BUILD,
    REVIEW,
    TEST,
    SECURITY,
    RELEASE,
    OWNER_APPROVAL,
    ROLLBACK,
}

enum class JarvisGateResult {
    PENDING,
    PASSED,
    FAILED,
    REQUIRES_OWNER_APPROVAL,
    SKIPPED,
}

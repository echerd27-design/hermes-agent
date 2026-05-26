package com.aci.hermes.model

enum class JarvisTaskStatus {
    DRAFT,
    ASSIGNED,
    IN_PROGRESS,
    AWAITING_VERIFICATION,
    BLOCKED_ON_GATE,
    AWAITING_OWNER_APPROVAL,
    COMPLETED,
    FAILED,
    CANCELLED,
}

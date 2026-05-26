package com.aci.hermes.ui.jarvis.tasks

enum class TaskPhase(val displayLabel: String) {
    INTAKE("Intake"),
    PLANNING("Planning"),
    IN_PROGRESS("In progress"),
    REVIEW("Review"),
    VERIFYING("Verifying"),
    PUBLISHED("Published"),
    BLOCKED("Blocked")
}

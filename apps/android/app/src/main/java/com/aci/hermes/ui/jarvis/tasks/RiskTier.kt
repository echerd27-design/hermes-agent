package com.aci.hermes.ui.jarvis.tasks

enum class RiskTier(val displayLabel: String, val severity: Int) {
    LOW("Low risk", 0),
    MODERATE("Moderate risk", 1),
    HIGH("High risk", 2),
    CRITICAL("Critical risk", 3)
}

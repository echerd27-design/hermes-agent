package com.aci.hermes.ui.jarvis.tasks

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class RiskTierTest {

    @Test
    fun riskTier_hasFourTiers() {
        assertEquals(4, RiskTier.values().size)
    }

    @Test
    fun riskTier_severityAscendsByOrdinal() {
        val byOrdinal = RiskTier.values().toList()
        val severities = byOrdinal.map { it.severity }
        assertEquals(listOf(0, 1, 2, 3), severities)
    }

    @Test
    fun riskTier_severityIsUnique() {
        val severities = RiskTier.values().map { it.severity }
        assertEquals(severities.size, severities.toSet().size)
    }

    @Test
    fun riskTier_labelsEndWithRiskWord() {
        for (tier in RiskTier.values()) {
            assertTrue(
                "expected label to end with 'risk' for $tier, was '${tier.displayLabel}'",
                tier.displayLabel.endsWith("risk")
            )
        }
    }
}

package com.aci.hermes.model.jarvis

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class JarvisRiskTierTest {

    @Test
    fun values_containsAllThreeTiers() {
        assertEquals(3, JarvisRiskTier.values().size)
        assertEquals(
            setOf(JarvisRiskTier.NORMAL, JarvisRiskTier.SERIOUS, JarvisRiskTier.CRITICAL),
            JarvisRiskTier.values().toSet(),
        )
    }

    @Test
    fun ordinal_isNormalThenSeriousThenCritical() {
        assertTrue(JarvisRiskTier.NORMAL.ordinal < JarvisRiskTier.SERIOUS.ordinal)
        assertTrue(JarvisRiskTier.SERIOUS.ordinal < JarvisRiskTier.CRITICAL.ordinal)
    }

    @Test
    fun valueOf_roundTrips() {
        assertEquals(JarvisRiskTier.SERIOUS, JarvisRiskTier.valueOf("SERIOUS"))
        assertEquals(JarvisRiskTier.CRITICAL, JarvisRiskTier.valueOf("CRITICAL"))
    }
}

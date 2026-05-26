package com.aci.hermes.model.jarvis

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Test

class JarvisTaskCardTest {

    private fun sampleCard(
        id: String = "task-1",
        riskTier: JarvisRiskTier = JarvisRiskTier.NORMAL,
        blockedReason: String? = null,
        proofId: String? = null,
        rollbackAvailable: Boolean = false,
    ) = JarvisTaskCard(
        id = id,
        title = "Wire low-clearance warning",
        summary = "Add truck-safe reroute hint to navigation card.",
        phase = "BUILD",
        riskTier = riskTier,
        workerLabel = "operator-01",
        createdAtEpochMs = 1_700_000_000_000L,
        updatedAtEpochMs = 1_700_000_001_000L,
        blockedReason = blockedReason,
        proofId = proofId,
        rollbackAvailable = rollbackAvailable,
    )

    @Test
    fun defaults_blockedReasonAndProofIdAreNullAndRollbackUnavailable() {
        val card = sampleCard()
        assertNull(card.blockedReason)
        assertNull(card.proofId)
        assertFalse(card.rollbackAvailable)
    }

    @Test
    fun copy_preservesUneditedFields() {
        val original = sampleCard()
        val copy = original.copy(title = "Renamed card")
        assertEquals("Renamed card", copy.title)
        assertEquals(original.id, copy.id)
        assertEquals(original.phase, copy.phase)
        assertEquals(original.riskTier, copy.riskTier)
        assertEquals(original.createdAtEpochMs, copy.createdAtEpochMs)
    }

    @Test
    fun equality_basedOnAllFields() {
        val a = sampleCard()
        val b = sampleCard()
        assertEquals(a, b)
        assertEquals(a.hashCode(), b.hashCode())

        val c = sampleCard(id = "task-2")
        assertNotEquals(a, c)
    }

    @Test
    fun riskTier_roundTripsThroughCopy() {
        val card = sampleCard(riskTier = JarvisRiskTier.NORMAL)
        val escalated = card.copy(riskTier = JarvisRiskTier.CRITICAL)
        assertEquals(JarvisRiskTier.CRITICAL, escalated.riskTier)
        assertEquals(JarvisRiskTier.NORMAL, card.riskTier)
    }

    @Test
    fun blockedReason_andProofId_persistWhenSet() {
        val card = sampleCard(blockedReason = "awaiting gate", proofId = "proof-42")
        assertEquals("awaiting gate", card.blockedReason)
        assertEquals("proof-42", card.proofId)
    }
}

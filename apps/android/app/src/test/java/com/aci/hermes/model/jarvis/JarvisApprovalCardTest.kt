package com.aci.hermes.model.jarvis

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Test

class JarvisApprovalCardTest {

    private fun sampleCard(
        status: JarvisApprovalStatus = JarvisApprovalStatus.PENDING,
        riskTier: JarvisRiskTier = JarvisRiskTier.SERIOUS,
        requiresSecondConfirm: Boolean = false,
        requiresExactPhrase: Boolean = false,
    ) = JarvisApprovalCard(
        id = "approval-1",
        title = "Deploy gateway change",
        action = "deploy",
        riskTier = riskTier,
        impactSummary = "Restarts gateway service for ~20 seconds.",
        rollbackSummary = "Revert commit and redeploy prior tag.",
        requiresSecondConfirm = requiresSecondConfirm,
        requiresExactPhrase = requiresExactPhrase,
        status = status,
    )

    @Test
    fun defaultStatus_isPending() {
        val card = JarvisApprovalCard(
            id = "approval-2",
            title = "Open question",
            action = "merge",
            riskTier = JarvisRiskTier.NORMAL,
            impactSummary = "Merges PR.",
            rollbackSummary = "Revert merge commit.",
        )
        assertEquals(JarvisApprovalStatus.PENDING, card.status)
        assertFalse(card.requiresSecondConfirm)
        assertFalse(card.requiresExactPhrase)
    }

    @Test
    fun copy_canTransitionStatusToApproved() {
        val pending = sampleCard()
        val approved = pending.copy(status = JarvisApprovalStatus.APPROVED)
        assertEquals(JarvisApprovalStatus.APPROVED, approved.status)
        assertEquals(JarvisApprovalStatus.PENDING, pending.status)
        assertNotEquals(pending, approved)
    }

    @Test
    fun statusEnum_hasFourEntries() {
        assertEquals(4, JarvisApprovalStatus.values().size)
        assertEquals(
            setOf(
                JarvisApprovalStatus.PENDING,
                JarvisApprovalStatus.APPROVED,
                JarvisApprovalStatus.REJECTED,
                JarvisApprovalStatus.EXPIRED,
            ),
            JarvisApprovalStatus.values().toSet(),
        )
    }

    @Test
    fun confirmFlags_persistWhenSet() {
        val card = sampleCard(requiresSecondConfirm = true, requiresExactPhrase = true)
        assertEquals(true, card.requiresSecondConfirm)
        assertEquals(true, card.requiresExactPhrase)
    }

    @Test
    fun equality_basedOnAllFields() {
        val a = sampleCard()
        val b = sampleCard()
        assertEquals(a, b)
        assertEquals(a.hashCode(), b.hashCode())
    }
}

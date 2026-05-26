package com.aci.hermes.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class OwnerApprovalRequestTest {

    private fun sampleRequest(
        status: OwnerApprovalStatus = OwnerApprovalStatus.PENDING,
        resolvedAtEpochMs: Long? = null,
        resolutionNote: String? = null,
    ) = OwnerApprovalRequest(
        id = "approval-1",
        taskId = "task-1",
        reason = OwnerApprovalReason.MERGE,
        riskSummary = "Merging to main affects release line.",
        recommendation = "Request explicit owner authorization before merge.",
        status = status,
        requestedAtEpochMs = 1_700_000_000_000L,
        resolvedAtEpochMs = resolvedAtEpochMs,
        resolutionNote = resolutionNote,
    )

    @Test
    fun defaultStatus_isPending_andUnresolvedFieldsAreNull() {
        val request = sampleRequest()
        assertEquals(OwnerApprovalStatus.PENDING, request.status)
        assertNull(request.resolvedAtEpochMs)
        assertNull(request.resolutionNote)
    }

    @Test
    fun approvedCopy_recordsResolution() {
        val request = sampleRequest().copy(
            status = OwnerApprovalStatus.APPROVED,
            resolvedAtEpochMs = 1_700_000_500_000L,
            resolutionNote = "Yes, with authorization.",
        )
        assertEquals(OwnerApprovalStatus.APPROVED, request.status)
        assertEquals("Yes, with authorization.", request.resolutionNote)
    }

    @Test
    fun reasonsEnum_coversDocumentedOwnerGates() {
        val expected = setOf(
            OwnerApprovalReason.MERGE,
            OwnerApprovalReason.FORCE_PUSH,
            OwnerApprovalReason.DEPLOY,
            OwnerApprovalReason.PUBLISH,
            OwnerApprovalReason.DELETE_RECOVERED_SOURCE,
            OwnerApprovalReason.MODIFY_SECRETS,
            OwnerApprovalReason.CHANGE_DEFAULT_AGENTS,
            OwnerApprovalReason.REGISTRY_MUTATION,
            OwnerApprovalReason.SPEND_MONEY,
            OwnerApprovalReason.EXTERNAL_SERVICE_CHANGE,
            OwnerApprovalReason.DNS_CHANGE,
            OwnerApprovalReason.APP_STORE_SUBMISSION,
        )
        assertEquals(expected, OwnerApprovalReason.values().toSet())
    }

    @Test
    fun statusEnum_includesExpired() {
        assertTrue(OwnerApprovalStatus.values().contains(OwnerApprovalStatus.EXPIRED))
    }
}

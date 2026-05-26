package com.aci.hermes.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class VerificationEvidenceTest {

    private fun sampleEvidence(
        verified: Boolean = false,
        detailRef: String? = null,
    ) = VerificationEvidence(
        id = "ev-1",
        taskId = "task-1",
        gate = JarvisGate.TEST,
        type = VerificationEvidenceType.TEST_RESULT,
        summary = "Unit suite passed.",
        detailRef = detailRef,
        verified = verified,
        collectedAtEpochMs = 1_700_000_000_000L,
    )

    @Test
    fun defaults_detailRefIsNull_verifiedIsFalse() {
        val evidence = sampleEvidence()
        assertNull(evidence.detailRef)
        assertFalse(evidence.verified)
    }

    @Test
    fun verifiedCopy_setsVerifiedAndDetailRef() {
        val original = sampleEvidence()
        val verified = original.copy(verified = true, detailRef = "build/reports/tests/test/index.html")
        assertTrue(verified.verified)
        assertEquals("build/reports/tests/test/index.html", verified.detailRef)
    }

    @Test
    fun typesEnum_coversExpectedEvidenceCategories() {
        val expected = setOf(
            VerificationEvidenceType.TEST_RESULT,
            VerificationEvidenceType.DIFF_REVIEW,
            VerificationEvidenceType.LINT_RESULT,
            VerificationEvidenceType.SECURITY_SCAN,
            VerificationEvidenceType.BUILD_LOG,
            VerificationEvidenceType.MANUAL_CHECK,
            VerificationEvidenceType.LINK_CHECK,
            VerificationEvidenceType.SCHEMA_VALIDATION,
        )
        assertEquals(expected, VerificationEvidenceType.values().toSet())
    }
}

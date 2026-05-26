/*
 * Jarvis Prime — ProofRecord.summary() tests (W10 spec-only).
 *
 * Pure JVM unit test. No Android framework imports. Safe to run as a plain
 * JUnit suite in the consuming Android repo
 * (A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent).
 *
 * Does NOT run in echerd27-design/hermes-agent (no Gradle / JUnit here).
 */
package com.aci.hermes.ui.jarvis.proof

import org.junit.Test
import kotlin.test.assertEquals

class ProofRecordSummaryTest {

    private fun record(
        tests: Int,
        files: Int,
        approvals: Int,
    ): ProofRecord = ProofRecord(
        id = "p-1",
        action = "Refactored cache layer",
        timestamp = "2026-05-26T14:00:00Z",
        tests = List(tests) { TestEvidence(suite = "suite-$it", passed = 1, failed = 0) },
        files = List(files) { ChangedFile(path = "src/file$it.kt", added = 1, removed = 0) },
        approvals = List(approvals) {
            ApprovalEvent(actor = "actor-$it", decision = "approved", timestamp = "2026-05-26T14:00:00Z")
        },
        hasRollback = false,
    )

    @Test
    fun pluralizes_when_counts_are_not_one() {
        assertEquals("3 tests, 2 files, 0 approvals", record(3, 2, 0).summary())
    }

    @Test
    fun singularizes_when_counts_are_one() {
        assertEquals("1 test, 1 file, 1 approval", record(1, 1, 1).summary())
    }

    @Test
    fun handles_all_zero() {
        assertEquals("0 tests, 0 files, 0 approvals", record(0, 0, 0).summary())
    }
}

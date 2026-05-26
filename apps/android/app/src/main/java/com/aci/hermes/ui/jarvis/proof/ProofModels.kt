/*
 * Jarvis Prime — Proof History models (W10 spec-only delivery).
 *
 * Spec-only: ships from echerd27-design/hermes-agent (Python Hermes runtime)
 * and does NOT compile here — no Gradle, no Android SDK, no app module.
 * Target consumer: A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent W10 wave.
 *
 * TODO on integration: extract user-visible strings to res/values/strings.xml.
 */
package com.aci.hermes.ui.jarvis.proof

/** A single action Jarvis Prime performed and the proof it carries. */
data class ProofRecord(
    val id: String,
    val action: String,
    val timestamp: String,
    val tests: List<TestEvidence>,
    val files: List<ChangedFile>,
    val approvals: List<ApprovalEvent>,
    val hasRollback: Boolean,
)

/** Test suite result snapshot tied to a proof record. */
data class TestEvidence(
    val suite: String,
    val passed: Int,
    val failed: Int,
) {
    val hasFailures: Boolean get() = failed > 0
}

/** A file changed by the action, with line deltas. */
data class ChangedFile(
    val path: String,
    val added: Int,
    val removed: Int,
)

/** A human or agent approval recorded for the action. */
data class ApprovalEvent(
    val actor: String,
    val decision: String,
    val timestamp: String,
)

/** UI state for the Proof History screen. */
sealed class ProofHistoryUiState {
    object Loading : ProofHistoryUiState()
    object Empty : ProofHistoryUiState()
    data class Loaded(val records: List<ProofRecord>) : ProofHistoryUiState()
    data class Error(val message: String) : ProofHistoryUiState()

    companion object {
        fun fromRecords(records: List<ProofRecord>): ProofHistoryUiState =
            if (records.isEmpty()) Empty else Loaded(records)
    }
}

/**
 * Intent-only callback surface. No rollback action runs in this wave —
 * the host wires real behavior later.
 */
interface ProofHistoryCallbacks {
    fun onRollback(proofId: String)
    fun onOpenFile(path: String)
}

/** Short summary used for accessibility and tests. */
fun ProofRecord.summary(): String {
    val testCount = tests.size
    val fileCount = files.size
    val approvalCount = approvals.size
    return buildString {
        append(testCount).append(' ').append(if (testCount == 1) "test" else "tests")
        append(", ")
        append(fileCount).append(' ').append(if (fileCount == 1) "file" else "files")
        append(", ")
        append(approvalCount).append(' ').append(if (approvalCount == 1) "approval" else "approvals")
    }
}

// Chat-local sealed message vocabulary.
//
// A future reconciliation wave should collapse these chat-local types with the
// shared model package introduced by PR #18 ("Wave 10: JARVIS job-state Kotlin
// models" at apps/android/app/src/main/java/com/aci/hermes/model/). This wave
// intentionally does NOT depend on com.aci.hermes.model.* because PR #18 is
// still an open draft and importing from an unmerged branch would couple W09
// to its rebase schedule.
package com.aci.hermes.ui.jarvis.chat

sealed interface ChatMessage {
    val id: String
    val timestampMs: Long
}

data class UserMessage(
    override val id: String,
    val body: String,
    override val timestampMs: Long,
) : ChatMessage

data class JarvisMessage(
    override val id: String,
    val body: String,
    val expandedBody: String? = null,
    override val timestampMs: Long,
) : ChatMessage

data class TaskUpdate(
    override val id: String,
    val taskId: String,
    val label: String,
    val progressPercent: Int? = null,
    override val timestampMs: Long,
) : ChatMessage

data class ApprovalRequest(
    override val id: String,
    val approvalId: String,
    val prompt: String,
    val options: List<ApprovalOption>,
    override val timestampMs: Long,
) : ChatMessage

data class ApprovalOption(
    val label: String,
    val value: String,
)

enum class ProofKind {
    LINK,
    IMAGE,
    COMMAND_OUTPUT,
    FILE_DIFF,
}

data class ProofUpdate(
    override val id: String,
    val kind: ProofKind,
    val summary: String,
    override val timestampMs: Long,
) : ChatMessage

data class StatusEvent(
    override val id: String,
    val status: JarvisStatus,
    val detail: String? = null,
    override val timestampMs: Long,
) : ChatMessage

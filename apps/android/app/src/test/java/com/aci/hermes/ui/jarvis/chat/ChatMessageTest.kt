package com.aci.hermes.ui.jarvis.chat

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ChatMessageTest {

    private fun describe(message: ChatMessage): String = when (message) {
        is UserMessage -> "user"
        is JarvisMessage -> "jarvis"
        is TaskUpdate -> "task"
        is ApprovalRequest -> "approval"
        is ProofUpdate -> "proof"
        is StatusEvent -> "status"
    }

    @Test
    fun sealedInterfaceIsExhaustiveOverAllSixSubtypes() {
        val one = UserMessage(id = "u", body = "x", timestampMs = 0L)
        val two = JarvisMessage(id = "j", body = "x", timestampMs = 0L)
        val three = TaskUpdate(id = "t", taskId = "t-1", label = "x", timestampMs = 0L)
        val four = ApprovalRequest(id = "a", approvalId = "appr", prompt = "x", options = emptyList(), timestampMs = 0L)
        val five = ProofUpdate(id = "p", kind = ProofKind.LINK, summary = "x", timestampMs = 0L)
        val six = StatusEvent(id = "s", status = JarvisStatus.IDLE, timestampMs = 0L)
        val all = listOf(one, two, three, four, five, six)
        val labels = all.map(::describe)
        assertEquals(listOf("user", "jarvis", "task", "approval", "proof", "status"), labels)
    }

    @Test
    fun jarvisMessageExpandedBodyIsOptional() {
        val short = JarvisMessage(id = "j", body = "hi", timestampMs = 0L)
        val withExpand = JarvisMessage(id = "j", body = "hi", expandedBody = "longer", timestampMs = 0L)
        assertNull(short.expandedBody)
        assertNotNull(withExpand.expandedBody)
    }

    @Test
    fun proofKindCoversFourCases() {
        val kinds = ProofKind.values().toSet()
        assertEquals(setOf(ProofKind.LINK, ProofKind.IMAGE, ProofKind.COMMAND_OUTPUT, ProofKind.FILE_DIFF), kinds)
    }

    @Test
    fun jarvisStatusCoversFiveStatesIncludingIdle() {
        val expected = setOf(
            JarvisStatus.IDLE,
            JarvisStatus.LISTENING,
            JarvisStatus.THINKING,
            JarvisStatus.WORKING,
            JarvisStatus.WAITING_FOR_APPROVAL,
        )
        assertEquals(expected, JarvisStatus.values().toSet())
    }

    @Test
    fun approvalRequestCarriesOptionsList() {
        val req = ApprovalRequest(
            id = "a",
            approvalId = "appr-1",
            prompt = "deploy?",
            options = listOf(
                ApprovalOption("Approve", "approve"),
                ApprovalOption("Hold", "hold"),
            ),
            timestampMs = 0L,
        )
        assertEquals(2, req.options.size)
        assertTrue(req.options.any { it.value == "approve" })
    }
}

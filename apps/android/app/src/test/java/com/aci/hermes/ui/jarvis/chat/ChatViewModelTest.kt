package com.aci.hermes.ui.jarvis.chat

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ChatViewModelTest {

    private fun viewModel(clockSeed: Long = 1_000L): ChatViewModel {
        var counter = 0L
        var time = clockSeed
        return ChatViewModel(
            idProvider = {
                counter += 1
                "id-$counter"
            },
            clock = {
                time += 1
                time
            },
        )
    }

    @Test
    fun initialStateIsIdleAndEmpty() {
        val vm = viewModel()
        val state = vm.uiState.value
        assertTrue("messages should start empty", state.messages.isEmpty())
        assertEquals(JarvisStatus.IDLE, state.status)
        assertTrue("input should be enabled by default", state.isInputEnabled)
        assertNull("no pending approval at start", state.pendingApprovalId)
    }

    @Test
    fun sendUserMessageAppendsAndLeavesStatusUnchanged() {
        val vm = viewModel()
        vm.sendUserMessage("hello")
        val state = vm.uiState.value
        assertEquals(1, state.messages.size)
        val msg = state.messages.single()
        assertTrue("first message should be a UserMessage", msg is UserMessage)
        assertEquals("hello", (msg as UserMessage).body)
        assertEquals(JarvisStatus.IDLE, state.status)
    }

    @Test
    fun sendUserMessageIgnoresBlank() {
        val vm = viewModel()
        vm.sendUserMessage("")
        vm.sendUserMessage("   ")
        assertTrue(vm.uiState.value.messages.isEmpty())
    }

    @Test
    fun updateStatusEmitsNewStateAndStatusEvent() {
        val vm = viewModel()
        vm.updateStatus(JarvisStatus.LISTENING, detail = "warming up")
        val state = vm.uiState.value
        assertEquals(JarvisStatus.LISTENING, state.status)
        assertEquals(1, state.messages.size)
        val event = state.messages.single() as StatusEvent
        assertEquals(JarvisStatus.LISTENING, event.status)
        assertEquals("warming up", event.detail)
    }

    @Test
    fun appendIncomingHandlesEachSubtype() {
        val vm = viewModel()
        val now = 0L
        vm.appendIncoming(JarvisMessage(id = "j", body = "hi", timestampMs = now))
        vm.appendIncoming(TaskUpdate(id = "t", taskId = "t-1", label = "x", timestampMs = now))
        vm.appendIncoming(ProofUpdate(id = "p", kind = ProofKind.LINK, summary = "ok", timestampMs = now))
        vm.appendIncoming(StatusEvent(id = "s", status = JarvisStatus.WORKING, timestampMs = now))
        val messages = vm.uiState.value.messages
        assertEquals(4, messages.size)
        assertTrue(messages[0] is JarvisMessage)
        assertTrue(messages[1] is TaskUpdate)
        assertTrue(messages[2] is ProofUpdate)
        assertTrue(messages[3] is StatusEvent)
    }

    @Test
    fun appendingApprovalSetsPendingAndStatus() {
        val vm = viewModel()
        val approval = ApprovalRequest(
            id = "a-msg",
            approvalId = "appr-9",
            prompt = "go?",
            options = listOf(ApprovalOption("yes", "y"), ApprovalOption("no", "n")),
            timestampMs = 0L,
        )
        vm.appendIncoming(approval)
        val state = vm.uiState.value
        assertEquals("appr-9", state.pendingApprovalId)
        assertEquals(JarvisStatus.WAITING_FOR_APPROVAL, state.status)
    }

    @Test
    fun respondToApprovalClearsPendingAndTransitionsToWorking() {
        val vm = viewModel()
        val approval = ApprovalRequest(
            id = "a-msg",
            approvalId = "appr-9",
            prompt = "go?",
            options = listOf(ApprovalOption("yes", "y"), ApprovalOption("no", "n")),
            timestampMs = 0L,
        )
        vm.appendIncoming(approval)
        vm.respondToApproval(approvalId = "appr-9", optionValue = "y")
        val state = vm.uiState.value
        assertNull(state.pendingApprovalId)
        assertEquals(JarvisStatus.WORKING, state.status)
        val tail = state.messages.last()
        assertTrue("a UserMessage acknowledgement should be appended", tail is UserMessage)
        assertEquals("Approval response: y", (tail as UserMessage).body)
    }

    @Test
    fun respondToApprovalIgnoresUnknownId() {
        val vm = viewModel()
        vm.appendIncoming(
            ApprovalRequest(
                id = "a",
                approvalId = "appr-1",
                prompt = "go?",
                options = listOf(ApprovalOption("y", "y")),
                timestampMs = 0L,
            ),
        )
        val before = vm.uiState.value
        vm.respondToApproval(approvalId = "appr-other", optionValue = "y")
        val after = vm.uiState.value
        assertEquals(before, after)
    }

    @Test
    fun clearPendingApprovalNullsField() {
        val vm = viewModel()
        vm.appendIncoming(
            ApprovalRequest(
                id = "a",
                approvalId = "appr-1",
                prompt = "go?",
                options = emptyList(),
                timestampMs = 0L,
            ),
        )
        vm.clearPendingApproval()
        assertNull(vm.uiState.value.pendingApprovalId)
    }

    @Test
    fun statusTransitionMatrixIsAccepted() {
        val vm = viewModel()
        val sequence = listOf(
            JarvisStatus.LISTENING,
            JarvisStatus.THINKING,
            JarvisStatus.WORKING,
            JarvisStatus.WAITING_FOR_APPROVAL,
            JarvisStatus.IDLE,
        )
        sequence.forEach { vm.updateStatus(it) }
        assertEquals(JarvisStatus.IDLE, vm.uiState.value.status)
        val statusEventsInOrder = vm.uiState.value.messages
            .filterIsInstance<StatusEvent>()
            .map { it.status }
        assertEquals(sequence, statusEventsInOrder)
    }

    @Test
    fun jarvisMessageShortAndExpandedBothSurfaceWhenProvided() {
        val msg = JarvisMessage(id = "j", body = "short", expandedBody = "long expanded", timestampMs = 0L)
        assertEquals("short", msg.body)
        assertNotNull(msg.expandedBody)
    }

    @Test
    fun jarvisMessageDefaultsToShortOnly() {
        val msg = JarvisMessage(id = "j", body = "short", timestampMs = 0L)
        assertNull("default expandedBody should be null so no Expand button is shown", msg.expandedBody)
    }
}

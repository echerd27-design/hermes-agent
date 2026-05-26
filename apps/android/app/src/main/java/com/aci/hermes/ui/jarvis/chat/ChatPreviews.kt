package com.aci.hermes.ui.jarvis.chat

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp

@Preview(name = "Idle empty", showBackground = true)
@Composable
fun ChatScreenIdleEmptyPreview() {
    MaterialTheme {
        Surface(modifier = Modifier.fillMaxSize()) {
            ChatScreen(
                state = ChatUiState(),
                onSend = {},
                onExpand = {},
                onApprovalSelect = { _, _ -> },
                onVoiceTap = {},
            )
        }
    }
}

@Preview(name = "Conversation", showBackground = true)
@Composable
fun ChatScreenConversationPreview() {
    MaterialTheme {
        Surface(modifier = Modifier.fillMaxSize()) {
            ChatScreen(
                state = sampleConversation(),
                onSend = {},
                onExpand = {},
                onApprovalSelect = { _, _ -> },
                onVoiceTap = {},
            )
        }
    }
}

@Preview(name = "Waiting for approval", showBackground = true)
@Composable
fun ChatScreenApprovalPreview() {
    MaterialTheme {
        Surface(modifier = Modifier.fillMaxSize()) {
            ChatScreen(
                state = sampleApproval(),
                onSend = {},
                onExpand = {},
                onApprovalSelect = { _, _ -> },
                onVoiceTap = {},
            )
        }
    }
}

@Preview(name = "Status pills", showBackground = true)
@Composable
fun StatusPillsPreview() {
    MaterialTheme {
        Surface {
            Column(
                verticalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.padding(16.dp),
            ) {
                JarvisStatus.values().forEach { StatusPill(status = it) }
            }
        }
    }
}

private fun sampleConversation(): ChatUiState = ChatUiState(
    messages = listOf(
        UserMessage(id = "u1", body = "Plan tomorrow's work.", timestampMs = 0L),
        JarvisMessage(
            id = "j1",
            body = "Three blocks: deep work AM, ops review PM, family dinner.",
            expandedBody = "Three blocks:\n1. 09:00-12:00 deep work — finish W09 chat surface.\n2. 14:00-16:00 ops review with the AOS council.\n3. 18:30 family dinner. No screens.",
            timestampMs = 1L,
        ),
        TaskUpdate(
            id = "t1",
            taskId = "task-42",
            label = "Drafting PR description",
            progressPercent = 60,
            timestampMs = 2L,
        ),
        ProofUpdate(id = "p1", kind = ProofKind.LINK, summary = "Draft PR #19 opened", timestampMs = 3L),
    ),
    status = JarvisStatus.WORKING,
)

private fun sampleApproval(): ChatUiState = ChatUiState(
    messages = listOf(
        JarvisMessage(id = "j2", body = "Ready to push. Approve?", timestampMs = 0L),
        ApprovalRequest(
            id = "a1",
            approvalId = "appr-1",
            prompt = "Push branch aci/jarvis-prime-09-chat-voice-ui and open draft PR?",
            options = listOf(
                ApprovalOption(label = "Approve", value = "approve"),
                ApprovalOption(label = "Hold", value = "hold"),
            ),
            timestampMs = 1L,
        ),
    ),
    status = JarvisStatus.WAITING_FOR_APPROVAL,
    pendingApprovalId = "appr-1",
)

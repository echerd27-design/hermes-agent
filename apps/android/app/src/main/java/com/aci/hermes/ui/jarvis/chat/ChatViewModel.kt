package com.aci.hermes.ui.jarvis.chat

import androidx.lifecycle.ViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

open class ChatViewModel(
    private val idProvider: () -> String = { java.util.UUID.randomUUID().toString() },
    private val clock: () -> Long = { System.currentTimeMillis() },
) : ViewModel() {

    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    fun sendUserMessage(body: String) {
        if (body.isBlank()) return
        val message = UserMessage(id = idProvider(), body = body, timestampMs = clock())
        _uiState.update { it.copy(messages = it.messages + message) }
    }

    fun updateStatus(status: JarvisStatus, detail: String? = null) {
        _uiState.update { current ->
            val pending = if (status == JarvisStatus.WAITING_FOR_APPROVAL) {
                current.pendingApprovalId
            } else if (current.pendingApprovalId != null && status == JarvisStatus.IDLE) {
                current.pendingApprovalId
            } else {
                current.pendingApprovalId
            }
            val statusEvent = StatusEvent(
                id = idProvider(),
                status = status,
                detail = detail,
                timestampMs = clock(),
            )
            current.copy(
                status = status,
                pendingApprovalId = pending,
                messages = current.messages + statusEvent,
            )
        }
    }

    fun appendIncoming(message: ChatMessage) {
        _uiState.update { current ->
            val newPending = if (message is ApprovalRequest) message.approvalId else current.pendingApprovalId
            val newStatus = if (message is ApprovalRequest) JarvisStatus.WAITING_FOR_APPROVAL else current.status
            current.copy(
                messages = current.messages + message,
                pendingApprovalId = newPending,
                status = newStatus,
            )
        }
    }

    fun respondToApproval(approvalId: String, optionValue: String) {
        _uiState.update { current ->
            if (current.pendingApprovalId != approvalId) return@update current
            val ack = UserMessage(
                id = idProvider(),
                body = "Approval response: $optionValue",
                timestampMs = clock(),
            )
            current.copy(
                messages = current.messages + ack,
                pendingApprovalId = null,
                status = JarvisStatus.WORKING,
            )
        }
    }

    fun clearPendingApproval() {
        _uiState.update { it.copy(pendingApprovalId = null) }
    }
}

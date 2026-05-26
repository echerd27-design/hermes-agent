package com.aci.hermes.ui.jarvis.chat

data class ChatUiState(
    val messages: List<ChatMessage> = emptyList(),
    val status: JarvisStatus = JarvisStatus.IDLE,
    val isInputEnabled: Boolean = true,
    val pendingApprovalId: String? = null,
)

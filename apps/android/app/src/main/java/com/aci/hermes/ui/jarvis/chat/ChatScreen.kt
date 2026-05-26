package com.aci.hermes.ui.jarvis.chat

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.Button
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.aci.hermes.ui.jarvis.voice.VoiceTapButton

@Composable
fun ChatScreen(
    state: ChatUiState,
    onSend: (String) -> Unit,
    onExpand: (messageId: String) -> Unit,
    onApprovalSelect: (approvalId: String, optionValue: String) -> Unit,
    onVoiceTap: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val expandedIds = remember { mutableStateOf(setOf<String>()) }
    val listState = rememberLazyListState()

    LaunchedEffect(state.messages.size) {
        if (state.messages.isNotEmpty()) {
            listState.animateScrollToItem(state.messages.lastIndex)
        }
    }

    Column(modifier = modifier.fillMaxSize().imePadding()) {
        Surface(
            tonalElevation = 2.dp,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(12.dp),
                horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                StatusPill(status = state.status)
            }
        }
        HorizontalDivider()
        Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
            if (state.messages.isEmpty()) {
                Text(
                    text = "Say hello to Jarvis.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.align(Alignment.Center),
                )
            } else {
                LazyColumn(
                    state = listState,
                    contentPadding = PaddingValues(vertical = 8.dp),
                    modifier = Modifier.fillMaxSize(),
                ) {
                    items(items = state.messages, key = { it.id }) { message ->
                        val isExpanded = message.id in expandedIds.value
                        ChatMessageRow(
                            message = message,
                            expanded = isExpanded,
                            onExpand = { id ->
                                expandedIds.value =
                                    if (id in expandedIds.value) expandedIds.value - id
                                    else expandedIds.value + id
                                onExpand(id)
                            },
                            onApprovalSelect = onApprovalSelect,
                        )
                    }
                }
            }
        }
        HorizontalDivider()
        ChatInputRow(
            enabled = state.isInputEnabled,
            onSend = onSend,
            onVoiceTap = onVoiceTap,
        )
    }
}

@Composable
private fun ChatInputRow(
    enabled: Boolean,
    onSend: (String) -> Unit,
    onVoiceTap: () -> Unit,
) {
    var draft by remember { mutableStateOf("") }
    Row(
        modifier = Modifier.fillMaxWidth().padding(8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        OutlinedTextField(
            value = draft,
            onValueChange = { draft = it },
            placeholder = { Text("Message Jarvis") },
            enabled = enabled,
            modifier = Modifier.weight(1f),
            singleLine = false,
        )
        VoiceTapButton(onTap = onVoiceTap, enabled = enabled)
        Button(
            enabled = enabled && draft.isNotBlank(),
            onClick = {
                onSend(draft)
                draft = ""
            },
        ) {
            Text("Send")
        }
    }
}

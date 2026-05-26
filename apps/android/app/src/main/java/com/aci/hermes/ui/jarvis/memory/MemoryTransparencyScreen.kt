/*
 * Jarvis Prime — Memory Transparency screen (W10 spec-only delivery).
 *
 * Spec-only: ships from echerd27-design/hermes-agent, does NOT compile here
 * (no Gradle, no Android SDK). Target: A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent.
 *
 * Header copy:  "What Jarvis Prime remembers"
 * Subhead copy: "You can edit or remove memories"
 *
 * No NavController, no ViewModel, no backend. The screen renders state and
 * forwards intent through MemoryTransparencyCallbacks.
 *
 * TODO on integration: extract user-visible strings to res/values/strings.xml.
 */
package com.aci.hermes.ui.jarvis.memory

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun MemoryTransparencyScreen(
    state: MemoryTransparencyUiState,
    callbacks: MemoryTransparencyCallbacks,
    modifier: Modifier = Modifier,
) {
    Scaffold(modifier = modifier.fillMaxSize()) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                text = "What Jarvis Prime remembers",
                style = MaterialTheme.typography.titleLarge,
            )
            Text(
                text = "You can edit or remove memories",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            MemoryTransparencyBody(state = state, callbacks = callbacks)
        }
    }
}

@Composable
private fun MemoryTransparencyBody(
    state: MemoryTransparencyUiState,
    callbacks: MemoryTransparencyCallbacks,
) {
    when (state) {
        is MemoryTransparencyUiState.Loading -> {
            Column(
                modifier = Modifier.fillMaxSize(),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) {
                CircularProgressIndicator()
            }
        }
        is MemoryTransparencyUiState.Empty -> EmptyMemoryState()
        is MemoryTransparencyUiState.Loaded -> {
            LazyColumn(
                contentPadding = PaddingValues(vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                items(items = state.records, key = { it.id }) { record ->
                    MemoryRecordCard(record = record, callbacks = callbacks)
                }
            }
        }
        is MemoryTransparencyUiState.Error -> {
            Text(
                text = state.message,
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}

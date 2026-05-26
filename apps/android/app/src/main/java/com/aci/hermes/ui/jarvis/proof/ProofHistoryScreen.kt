/*
 * Jarvis Prime — Proof History screen (W10 spec-only delivery).
 *
 * Spec-only; does NOT compile in echerd27-design/hermes-agent.
 * Target: A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent W10 wave.
 *
 * Header copy:  "Proof History"
 * Subhead copy: "What Jarvis did / How it was verified"
 *
 * No NavController, no ViewModel, no backend. Intent flows through
 * ProofHistoryCallbacks.
 */
package com.aci.hermes.ui.jarvis.proof

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
fun ProofHistoryScreen(
    state: ProofHistoryUiState,
    callbacks: ProofHistoryCallbacks,
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
                text = "Proof History",
                style = MaterialTheme.typography.titleLarge,
            )
            Text(
                text = "What Jarvis did / How it was verified",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            ProofHistoryBody(state = state, callbacks = callbacks)
        }
    }
}

@Composable
private fun ProofHistoryBody(
    state: ProofHistoryUiState,
    callbacks: ProofHistoryCallbacks,
) {
    when (state) {
        is ProofHistoryUiState.Loading -> {
            Column(
                modifier = Modifier.fillMaxSize(),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) {
                CircularProgressIndicator()
            }
        }
        is ProofHistoryUiState.Empty -> EmptyProofState()
        is ProofHistoryUiState.Loaded -> {
            LazyColumn(
                contentPadding = PaddingValues(vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                items(items = state.records, key = { it.id }) { record ->
                    ProofRecordCard(record = record, callbacks = callbacks)
                }
            }
        }
        is ProofHistoryUiState.Error -> {
            Text(
                text = state.message,
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}

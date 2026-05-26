package com.aci.hermes.ui.jarvis.emergency

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun EmergencyStopPanel(
    state: EmergencyStopUiState,
    onEmergencyStopConfirmed: () -> Unit,
    modifier: Modifier = Modifier,
) {
    var confirming by rememberSaveable { mutableStateOf(state == EmergencyStopUiState.Confirming) }

    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                text = EmergencyStopCopy.TITLE,
                style = MaterialTheme.typography.titleMedium,
            )
            Text(
                text = EmergencyStopCopy.DESCRIPTION,
                style = MaterialTheme.typography.bodyMedium,
            )
            EmergencyStopButton(
                state = state,
                onRequestStop = { confirming = true },
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }

    if (confirming && state != EmergencyStopUiState.Stopped) {
        EmergencyStopConfirmDialog(
            onConfirm = {
                confirming = false
                onEmergencyStopConfirmed()
            },
            onDismiss = { confirming = false },
        )
    }
}

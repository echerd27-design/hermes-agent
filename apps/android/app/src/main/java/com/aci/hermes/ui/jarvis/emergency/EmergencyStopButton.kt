package com.aci.hermes.ui.jarvis.emergency

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun EmergencyStopButton(
    state: EmergencyStopUiState,
    onRequestStop: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val isStopped = state == EmergencyStopUiState.Stopped
    Button(
        onClick = onRequestStop,
        enabled = !isStopped,
        modifier = modifier,
        colors = ButtonDefaults.buttonColors(
            containerColor = MaterialTheme.colorScheme.errorContainer,
            contentColor = MaterialTheme.colorScheme.onErrorContainer,
        ),
    ) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                text = if (isStopped) EmergencyStopCopy.STOPPED_BADGE else EmergencyStopCopy.TITLE,
                style = MaterialTheme.typography.labelLarge,
                modifier = Modifier.padding(vertical = 4.dp),
            )
        }
    }
}

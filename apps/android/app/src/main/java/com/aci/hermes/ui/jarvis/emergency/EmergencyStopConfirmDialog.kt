package com.aci.hermes.ui.jarvis.emergency

import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable

@Composable
fun EmergencyStopConfirmDialog(
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                text = EmergencyStopCopy.CONFIRM_DIALOG_TITLE,
                style = MaterialTheme.typography.headlineSmall,
            )
        },
        text = {
            Text(
                text = EmergencyStopCopy.DESCRIPTION,
                style = MaterialTheme.typography.bodyMedium,
            )
        },
        confirmButton = {
            TextButton(onClick = onConfirm) {
                Text(text = EmergencyStopCopy.CONFIRM_LABEL)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text(text = EmergencyStopCopy.CANCEL_LABEL)
            }
        },
    )
}

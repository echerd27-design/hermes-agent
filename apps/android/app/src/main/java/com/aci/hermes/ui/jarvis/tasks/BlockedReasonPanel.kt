package com.aci.hermes.ui.jarvis.tasks

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Block
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp

@Composable
fun BlockedReasonPanel(
    reason: String,
    unblockGuidance: String?,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.medium,
        color = MaterialTheme.colorScheme.errorContainer,
        contentColor = MaterialTheme.colorScheme.onErrorContainer,
        tonalElevation = 2.dp
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.Top
        ) {
            Icon(
                imageVector = Icons.Filled.Block,
                contentDescription = "Blocked"
            )
            Spacer(modifier = Modifier.width(12.dp))
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    text = "Blocked",
                    style = MaterialTheme.typography.labelLarge
                )
                Text(
                    text = reason,
                    style = MaterialTheme.typography.bodyMedium
                )
                if (unblockGuidance != null) {
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Unblock: $unblockGuidance",
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        }
    }
}

@Preview
@Composable
private fun BlockedReasonPanelPreview() {
    BlockedReasonPanel(
        reason = "Owner gate has not been granted for the publish step.",
        unblockGuidance = "Reply 'Yes, with authorization.' in the Jarvis Prime thread to release the gate."
    )
}

@Preview
@Composable
private fun BlockedReasonPanelWithoutGuidancePreview() {
    BlockedReasonPanel(
        reason = "Waiting on owner review.",
        unblockGuidance = null
    )
}

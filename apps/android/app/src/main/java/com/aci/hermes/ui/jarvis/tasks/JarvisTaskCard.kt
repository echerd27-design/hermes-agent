package com.aci.hermes.ui.jarvis.tasks

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Undo
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.tooling.preview.PreviewParameter
import androidx.compose.ui.unit.dp

@Composable
fun JarvisTaskCard(
    state: TaskCardUiState,
    modifier: Modifier = Modifier,
    onProofClick: (() -> Unit)? = null,
    onRollbackClick: (() -> Unit)? = null
) {
    ElevatedCard(modifier = modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = state.title,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f)
                )
                Spacer(modifier = Modifier.width(8.dp))
                RiskTierBadge(riskTier = state.riskTier)
            }

            Row(verticalAlignment = Alignment.CenterVertically) {
                TaskPhaseBadge(phase = state.phase)
                Spacer(modifier = Modifier.width(8.dp))
                val workerLabel = state.currentWorker?.displayLabel ?: "—"
                Text(
                    text = "Worker: $workerLabel",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            JarvisWorkerLane(state = state.workerLane)

            if (state.isBlocked) {
                BlockedReasonPanel(
                    reason = state.blockedReason ?: "",
                    unblockGuidance = state.unblockGuidance
                )
            }

            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                if (state.proofLink != null) {
                    TextButton(onClick = { onProofClick?.invoke() }) {
                        Text(text = "View proof")
                    }
                }
                if (state.rollbackAvailable) {
                    AssistChip(
                        onClick = { onRollbackClick?.invoke() },
                        label = { Text("Rollback available") },
                        leadingIcon = {
                            Icon(
                                imageVector = Icons.Filled.Undo,
                                contentDescription = null,
                                modifier = Modifier.padding(end = 4.dp)
                            )
                        },
                        colors = AssistChipDefaults.assistChipColors()
                    )
                }
            }
        }
    }
}

@Preview
@Composable
private fun JarvisTaskCardPreview(
    @PreviewParameter(JarvisTaskCardPreviewProvider::class) state: TaskCardUiState
) {
    JarvisTaskCard(state = state)
}

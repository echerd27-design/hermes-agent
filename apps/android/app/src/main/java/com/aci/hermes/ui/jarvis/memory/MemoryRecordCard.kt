/*
 * Jarvis Prime — Memory record card (W10 spec-only delivery).
 *
 * Spec-only; does NOT compile in echerd27-design/hermes-agent.
 * Target: A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent W10 wave.
 *
 * Edit/Delete are callback-only. No deletion happens in this wave.
 *
 * TODO on integration: extract user-visible strings to res/values/strings.xml.
 */
package com.aci.hermes.ui.jarvis.memory

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun MemoryRecordCard(
    record: MemoryRecord,
    callbacks: MemoryTransparencyCallbacks,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        elevation = CardDefaults.elevatedCardElevation(defaultElevation = 2.dp),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                text = record.fact,
                style = MaterialTheme.typography.titleMedium,
            )

            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                MemoryConfidenceBadge(confidence = record.confidence)
                Spacer(modifier = Modifier.width(4.dp))
                SourceProofReference(
                    source = record.source,
                    onViewProof = { proofId -> callbacks.onViewProof(proofId) },
                )
            }

            Text(
                text = "Why Jarvis remembers this: ${record.reason}",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End,
            ) {
                TextButton(onClick = { callbacks.onEdit(record.id) }) {
                    Text(text = "Edit")
                }
                TextButton(onClick = { callbacks.onDelete(record.id) }) {
                    Text(text = "Remove")
                }
            }
        }
    }
}

/*
 * Jarvis Prime — Proof record card (W10 spec-only delivery).
 *
 * Spec-only; does NOT compile in echerd27-design/hermes-agent.
 * Target: A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent W10 wave.
 */
package com.aci.hermes.ui.jarvis.proof

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun ProofRecordCard(
    record: ProofRecord,
    callbacks: ProofHistoryCallbacks,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        elevation = CardDefaults.elevatedCardElevation(defaultElevation = 2.dp),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                text = record.action,
                style = MaterialTheme.typography.titleMedium,
            )
            Text(
                text = record.timestamp,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            TestEvidenceSection(tests = record.tests)
            ChangedFilesSection(files = record.files, onOpenFile = callbacks::onOpenFile)
            ApprovalHistorySection(approvals = record.approvals)

            if (record.hasRollback) {
                RollbackLinkPlaceholder()
            }
        }
    }
}

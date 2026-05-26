package com.aci.hermes.ui.jarvis.tasks

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp

@Composable
fun TaskPhaseBadge(
    phase: TaskPhase,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier.semantics { contentDescription = "Phase: ${phase.displayLabel}" },
        shape = MaterialTheme.shapes.small,
        color = MaterialTheme.colorScheme.secondaryContainer,
        contentColor = MaterialTheme.colorScheme.onSecondaryContainer
    ) {
        Text(
            text = phase.displayLabel,
            style = MaterialTheme.typography.labelSmall,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
        )
    }
}

@Preview
@Composable
private fun TaskPhaseBadgePreview() {
    TaskPhaseBadge(phase = TaskPhase.IN_PROGRESS)
}

@Preview
@Composable
private fun TaskPhaseBadgeBlockedPreview() {
    TaskPhaseBadge(phase = TaskPhase.BLOCKED)
}

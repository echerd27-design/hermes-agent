/*
 * Jarvis Prime — Memory confidence badge (W10 spec-only delivery).
 *
 * Spec-only; does NOT compile in echerd27-design/hermes-agent.
 * Target: A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent W10 wave.
 *
 * Tier colors come from MaterialTheme.colorScheme — never hard-coded hex.
 */
package com.aci.hermes.ui.jarvis.memory

import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

@Composable
fun MemoryConfidenceBadge(
    confidence: MemoryConfidence,
    modifier: Modifier = Modifier,
) {
    val container: Color = when (confidence) {
        MemoryConfidence.HIGH -> MaterialTheme.colorScheme.primary
        MemoryConfidence.MEDIUM -> MaterialTheme.colorScheme.tertiary
        MemoryConfidence.LOW -> MaterialTheme.colorScheme.error
    }
    val content: Color = when (confidence) {
        MemoryConfidence.HIGH -> MaterialTheme.colorScheme.onPrimary
        MemoryConfidence.MEDIUM -> MaterialTheme.colorScheme.onTertiary
        MemoryConfidence.LOW -> MaterialTheme.colorScheme.onError
    }

    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(percent = 50),
        color = container,
        contentColor = content,
    ) {
        Text(
            text = confidence.label(),
            style = MaterialTheme.typography.labelSmall,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
        )
    }
}

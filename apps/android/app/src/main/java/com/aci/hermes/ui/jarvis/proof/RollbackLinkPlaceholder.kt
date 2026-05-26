/*
 * Jarvis Prime — Rollback link placeholder (W10 spec-only delivery).
 *
 * Spec-only; does NOT compile in echerd27-design/hermes-agent.
 * Target: A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent W10 wave.
 *
 * Placeholder only — no onClick wired in this wave. The host attaches a real
 * rollback handler when the proof backend ships.
 */
package com.aci.hermes.ui.jarvis.proof

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier

@Composable
fun RollbackLinkPlaceholder(modifier: Modifier = Modifier) {
    Text(
        text = "Rollback available",
        style = MaterialTheme.typography.labelMedium,
        color = MaterialTheme.colorScheme.primary,
        modifier = modifier,
    )
}

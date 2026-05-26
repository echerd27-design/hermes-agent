package com.aci.hermes.ui.jarvis.voice

import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp

// Voice tap button.
//
// The button does NOT call any Android permission API directly. Tapping it
// simply invokes `onTap`, which a future navigation wave will route to the
// voice capture screen. This keeps every mic-permission request strictly
// downstream of explicit user intent (mission rule: no auto-mic-prompt,
// no always-listening).
@Composable
fun VoiceTapButton(
    onTap: () -> Unit,
    enabled: Boolean = true,
    modifier: Modifier = Modifier,
) {
    FilledTonalIconButton(
        onClick = onTap,
        enabled = enabled,
        modifier = modifier
            .size(48.dp)
            .semantics { contentDescription = "Voice input" },
    ) {
        Icon(imageVector = Icons.Filled.Mic, contentDescription = null)
    }
}

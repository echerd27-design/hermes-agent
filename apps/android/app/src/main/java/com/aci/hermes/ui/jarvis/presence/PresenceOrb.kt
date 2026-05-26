package com.aci.hermes.ui.jarvis.presence

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aci.hermes.ui.jarvis.design.JarvisColors
import com.aci.hermes.ui.jarvis.design.JarvisSpacing
import com.aci.hermes.ui.jarvis.design.JarvisType

/**
 * Jarvis Prime presence orb.
 *
 * Solid circle filled with the state's semantic color, labeled below.
 * Professional and quiet by design — no animation, no glow, no
 * cartoon affordances. A future wave can layer motion on top via a
 * `PresenceOrbAnimated` variant without changing this contract.
 */
@Composable
fun PresenceOrb(
    state: PresenceState,
    modifier: Modifier = Modifier,
    diameter: Int = 56,
) {
    val color = Color(PresenceUi.colorHex(state))
    val description = PresenceUi.contentDescription(state)
    val labelText = PresenceUi.label(state)

    Column(
        modifier = modifier.semantics { contentDescription = description },
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(JarvisSpacing.sm.dp),
    ) {
        Box(
            modifier = Modifier
                .size(diameter.dp)
                .clip(CircleShape)
                .background(color),
        )
        Text(
            text = labelText,
            color = Color(JarvisColors.MutedGray),
            fontSize = JarvisType.caption.sp,
            style = MaterialTheme.typography.labelMedium,
        )
    }
}

@Preview(showBackground = true, backgroundColor = JarvisColors.BaseNavy)
@Composable
private fun PreviewPresenceOrbIdle() {
    PresenceOrb(state = PresenceState.IDLE)
}

@Preview(showBackground = true, backgroundColor = JarvisColors.BaseNavy)
@Composable
private fun PreviewPresenceOrbCritical() {
    PresenceOrb(state = PresenceState.CRITICAL_ACTION_PENDING)
}

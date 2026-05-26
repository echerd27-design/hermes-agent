package com.aci.hermes.ui.jarvis.chat

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

@Composable
fun StatusPill(
    status: JarvisStatus,
    detail: String? = null,
    modifier: Modifier = Modifier,
) {
    val label = when (status) {
        JarvisStatus.IDLE -> "Ready"
        JarvisStatus.LISTENING -> "Listening"
        JarvisStatus.THINKING -> "Thinking"
        JarvisStatus.WORKING -> "Working"
        JarvisStatus.WAITING_FOR_APPROVAL -> "Waiting for approval"
    }
    val indicatorColor = when (status) {
        JarvisStatus.IDLE -> MaterialTheme.colorScheme.outline
        JarvisStatus.LISTENING -> MaterialTheme.colorScheme.tertiary
        JarvisStatus.THINKING -> MaterialTheme.colorScheme.secondary
        JarvisStatus.WORKING -> MaterialTheme.colorScheme.primary
        JarvisStatus.WAITING_FOR_APPROVAL -> MaterialTheme.colorScheme.error
    }
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(50),
        color = MaterialTheme.colorScheme.surfaceVariant,
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
        ) {
            StatusIndicator(status = status, color = indicatorColor)
            Text(
                text = if (detail.isNullOrBlank()) label else "$label — $detail",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun StatusIndicator(status: JarvisStatus, color: Color) {
    val transition = rememberInfiniteTransition(label = "status-indicator")
    val pulse by transition.animateFloatAsState(
        initialValue = 0.4f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 700, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "status-pulse",
    )
    val alpha = when (status) {
        JarvisStatus.LISTENING, JarvisStatus.THINKING, JarvisStatus.WORKING -> pulse
        else -> 1f
    }
    androidx.compose.foundation.layout.Box(
        modifier = Modifier
            .size(10.dp)
            .alpha(alpha)
            .clip(RoundedCornerShape(50))
            .background(color),
    )
}

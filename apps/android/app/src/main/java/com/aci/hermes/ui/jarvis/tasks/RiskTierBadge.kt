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
fun RiskTierBadge(
    riskTier: RiskTier,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier.semantics { contentDescription = riskTier.displayLabel },
        shape = MaterialTheme.shapes.small,
        color = riskTierContainer(riskTier),
        contentColor = riskTierOnContainer(riskTier)
    ) {
        Text(
            text = riskTier.displayLabel,
            style = MaterialTheme.typography.labelSmall,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
        )
    }
}

@Preview
@Composable
private fun RiskTierBadgeLowPreview() {
    RiskTierBadge(riskTier = RiskTier.LOW)
}

@Preview
@Composable
private fun RiskTierBadgeHighPreview() {
    RiskTierBadge(riskTier = RiskTier.HIGH)
}

@Preview
@Composable
private fun RiskTierBadgeCriticalPreview() {
    RiskTierBadge(riskTier = RiskTier.CRITICAL)
}

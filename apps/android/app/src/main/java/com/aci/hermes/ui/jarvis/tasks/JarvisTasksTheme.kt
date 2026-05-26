package com.aci.hermes.ui.jarvis.tasks

import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

@Composable
fun riskTierContainer(riskTier: RiskTier): Color = when (riskTier) {
    RiskTier.LOW -> MaterialTheme.colorScheme.secondaryContainer
    RiskTier.MODERATE -> MaterialTheme.colorScheme.tertiaryContainer
    RiskTier.HIGH -> MaterialTheme.colorScheme.errorContainer
    RiskTier.CRITICAL -> MaterialTheme.colorScheme.error
}

@Composable
fun riskTierOnContainer(riskTier: RiskTier): Color = when (riskTier) {
    RiskTier.LOW -> MaterialTheme.colorScheme.onSecondaryContainer
    RiskTier.MODERATE -> MaterialTheme.colorScheme.onTertiaryContainer
    RiskTier.HIGH -> MaterialTheme.colorScheme.onErrorContainer
    RiskTier.CRITICAL -> MaterialTheme.colorScheme.onError
}

@Composable
fun stageContainer(state: WorkerLaneStageState): Color = when (state) {
    WorkerLaneStageState.Active -> MaterialTheme.colorScheme.primary
    WorkerLaneStageState.Done -> MaterialTheme.colorScheme.tertiary
    is WorkerLaneStageState.Blocked -> MaterialTheme.colorScheme.error
    WorkerLaneStageState.Skipped -> MaterialTheme.colorScheme.outlineVariant
    WorkerLaneStageState.Pending -> MaterialTheme.colorScheme.surfaceVariant
}

@Composable
fun stageOnContainer(state: WorkerLaneStageState): Color = when (state) {
    WorkerLaneStageState.Active -> MaterialTheme.colorScheme.onPrimary
    WorkerLaneStageState.Done -> MaterialTheme.colorScheme.onTertiary
    is WorkerLaneStageState.Blocked -> MaterialTheme.colorScheme.onError
    WorkerLaneStageState.Skipped -> MaterialTheme.colorScheme.onSurfaceVariant
    WorkerLaneStageState.Pending -> MaterialTheme.colorScheme.onSurfaceVariant
}

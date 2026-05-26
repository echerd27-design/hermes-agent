package com.aci.hermes.ui.jarvis.tasks

data class TaskCardUiState(
    val id: String,
    val title: String,
    val phase: TaskPhase,
    val riskTier: RiskTier,
    val currentWorker: WorkerLabel?,
    val workerLane: WorkerLaneUiState,
    val blockedReason: String?,
    val unblockGuidance: String?,
    val proofLink: String?,
    val rollbackAvailable: Boolean
) {
    val isBlocked: Boolean
        get() = blockedReason != null
}

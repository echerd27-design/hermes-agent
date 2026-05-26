package com.aci.hermes.ui.jarvis.tasks

import androidx.compose.ui.tooling.preview.PreviewParameterProvider

object JarvisTaskSampleData {
    val samples: List<TaskCardUiState> = listOf(
        TaskCardUiState(
            id = "task-001",
            title = "Refactor Jarvis Prime memory ledger writer",
            phase = TaskPhase.IN_PROGRESS,
            riskTier = RiskTier.MODERATE,
            currentWorker = WorkerLabel.EDITOR,
            workerLane = WorkerLaneUiState(
                listOf(
                    WorkerLaneStage(WorkerLabel.PLANNER, WorkerLaneStageState.Done),
                    WorkerLaneStage(WorkerLabel.NAVIGATOR, WorkerLaneStageState.Done),
                    WorkerLaneStage(WorkerLabel.EDITOR, WorkerLaneStageState.Active),
                    WorkerLaneStage(WorkerLabel.EXECUTOR, WorkerLaneStageState.Pending),
                    WorkerLaneStage(WorkerLabel.REVIEWER, WorkerLaneStageState.Pending),
                    WorkerLaneStage(WorkerLabel.VERIFIER, WorkerLaneStageState.Pending),
                    WorkerLaneStage(WorkerLabel.PUBLISHER, WorkerLaneStageState.Pending)
                )
            ),
            blockedReason = null,
            unblockGuidance = null,
            proofLink = "jarvis://proof/task-001",
            rollbackAvailable = false
        ),
        TaskCardUiState(
            id = "task-002",
            title = "Publish Wave 05 release notes to Jarvis Prime channel",
            phase = TaskPhase.BLOCKED,
            riskTier = RiskTier.HIGH,
            currentWorker = WorkerLabel.VERIFIER,
            workerLane = WorkerLaneUiState(
                listOf(
                    WorkerLaneStage(WorkerLabel.PLANNER, WorkerLaneStageState.Done),
                    WorkerLaneStage(WorkerLabel.NAVIGATOR, WorkerLaneStageState.Done),
                    WorkerLaneStage(WorkerLabel.EDITOR, WorkerLaneStageState.Done),
                    WorkerLaneStage(WorkerLabel.EXECUTOR, WorkerLaneStageState.Done),
                    WorkerLaneStage(WorkerLabel.REVIEWER, WorkerLaneStageState.Done),
                    WorkerLaneStage(
                        WorkerLabel.VERIFIER,
                        WorkerLaneStageState.Blocked("Owner gate not granted")
                    ),
                    WorkerLaneStage(WorkerLabel.PUBLISHER, WorkerLaneStageState.Pending)
                )
            ),
            blockedReason = "Owner gate has not been granted for the publish step.",
            unblockGuidance = "Reply 'Yes, with authorization.' in the Jarvis Prime thread to release the gate.",
            proofLink = "jarvis://proof/task-002",
            rollbackAvailable = true
        ),
        TaskCardUiState(
            id = "task-003",
            title = "Promote Jarvis Prime mobile layout to beta",
            phase = TaskPhase.PUBLISHED,
            riskTier = RiskTier.LOW,
            currentWorker = WorkerLabel.PUBLISHER,
            workerLane = WorkerLaneUiState(
                WorkerLabel.pipeline.map { WorkerLaneStage(it, WorkerLaneStageState.Done) }
            ),
            blockedReason = null,
            unblockGuidance = null,
            proofLink = "jarvis://proof/task-003",
            rollbackAvailable = true
        ),
        TaskCardUiState(
            id = "task-004",
            title = "Draft Jarvis Prime compliance review for v0.15 cut",
            phase = TaskPhase.PLANNING,
            riskTier = RiskTier.CRITICAL,
            currentWorker = WorkerLabel.PLANNER,
            workerLane = WorkerLaneUiState(
                listOf(
                    WorkerLaneStage(WorkerLabel.PLANNER, WorkerLaneStageState.Active),
                    WorkerLaneStage(WorkerLabel.NAVIGATOR, WorkerLaneStageState.Pending),
                    WorkerLaneStage(WorkerLabel.EDITOR, WorkerLaneStageState.Pending),
                    WorkerLaneStage(WorkerLabel.EXECUTOR, WorkerLaneStageState.Pending),
                    WorkerLaneStage(WorkerLabel.REVIEWER, WorkerLaneStageState.Pending),
                    WorkerLaneStage(WorkerLabel.VERIFIER, WorkerLaneStageState.Pending),
                    WorkerLaneStage(WorkerLabel.PUBLISHER, WorkerLaneStageState.Pending)
                )
            ),
            blockedReason = null,
            unblockGuidance = null,
            proofLink = null,
            rollbackAvailable = false
        )
    )
}

class JarvisTaskCardPreviewProvider : PreviewParameterProvider<TaskCardUiState> {
    override val values: Sequence<TaskCardUiState> = JarvisTaskSampleData.samples.asSequence()
}

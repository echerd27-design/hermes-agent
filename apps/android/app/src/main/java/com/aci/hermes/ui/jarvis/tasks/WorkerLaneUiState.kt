package com.aci.hermes.ui.jarvis.tasks

data class WorkerLaneStage(
    val label: WorkerLabel,
    val state: WorkerLaneStageState
)

data class WorkerLaneUiState(val stages: List<WorkerLaneStage>) {
    init {
        require(stages.size == WorkerLabel.values().size) {
            "WorkerLaneUiState must contain exactly ${WorkerLabel.values().size} stages"
        }
        require(stages.map { it.label } == WorkerLabel.pipeline) {
            "WorkerLaneUiState stages must follow WorkerLabel.pipeline order"
        }
    }

    companion object {
        fun allPending(): WorkerLaneUiState =
            WorkerLaneUiState(WorkerLabel.pipeline.map { WorkerLaneStage(it, WorkerLaneStageState.Pending) })
    }
}

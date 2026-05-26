package com.aci.hermes.ui.jarvis.tasks

sealed class WorkerLaneStageState {
    object Pending : WorkerLaneStageState()
    object Active : WorkerLaneStageState()
    object Done : WorkerLaneStageState()
    data class Blocked(val reason: String) : WorkerLaneStageState()
    object Skipped : WorkerLaneStageState()
}

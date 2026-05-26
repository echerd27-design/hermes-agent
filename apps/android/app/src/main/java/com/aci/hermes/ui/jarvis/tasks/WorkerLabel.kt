package com.aci.hermes.ui.jarvis.tasks

enum class WorkerLabel(val displayLabel: String, val order: Int) {
    PLANNER("Planner", 0),
    NAVIGATOR("Navigator", 1),
    EDITOR("Editor", 2),
    EXECUTOR("Executor", 3),
    REVIEWER("Reviewer", 4),
    VERIFIER("Verifier", 5),
    PUBLISHER("Publisher", 6);

    companion object {
        val pipeline: List<WorkerLabel> = values().sortedBy { it.order }
    }
}

package com.aci.hermes.ui.jarvis.tasks

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp

@Composable
fun JarvisWorkerLane(
    state: WorkerLaneUiState,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .semantics { contentDescription = "Jarvis Prime worker lane" },
        verticalAlignment = Alignment.Top
    ) {
        state.stages.forEachIndexed { index, stage ->
            WorkerLaneStageItem(
                index = index,
                stage = stage,
                modifier = Modifier.weight(1f)
            )
            if (index < state.stages.lastIndex) {
                WorkerLaneConnector(
                    leftState = stage.state,
                    rightState = state.stages[index + 1].state
                )
            }
        }
    }
}

@Composable
private fun WorkerLaneStageItem(
    index: Int,
    stage: WorkerLaneStage,
    modifier: Modifier = Modifier
) {
    val stageStateLabel = stageStateLabel(stage.state)
    Column(
        modifier = modifier.semantics {
            stateDescription = stageStateLabel
            contentDescription = "${stage.label.displayLabel}: $stageStateLabel"
        },
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Top
    ) {
        Surface(
            shape = CircleShape,
            color = stageContainer(stage.state),
            contentColor = stageOnContainer(stage.state),
            modifier = Modifier.size(28.dp)
        ) {
            Box(contentAlignment = Alignment.Center) {
                Text(
                    text = (index + 1).toString(),
                    style = MaterialTheme.typography.labelMedium
                )
            }
        }
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = stage.label.displayLabel,
            style = MaterialTheme.typography.bodySmall,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(horizontal = 2.dp)
        )
    }
}

@Composable
private fun WorkerLaneConnector(
    leftState: WorkerLaneStageState,
    rightState: WorkerLaneStageState
) {
    val color = when {
        leftState is WorkerLaneStageState.Done && rightState !is WorkerLaneStageState.Pending ->
            MaterialTheme.colorScheme.tertiary
        else -> MaterialTheme.colorScheme.outlineVariant
    }
    Column(
        verticalArrangement = Arrangement.Top,
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier.padding(top = 13.dp)
    ) {
        HorizontalDivider(
            thickness = 2.dp,
            color = color,
            modifier = Modifier.size(width = 16.dp, height = 2.dp)
        )
    }
}

private fun stageStateLabel(state: WorkerLaneStageState): String = when (state) {
    WorkerLaneStageState.Pending -> "Pending"
    WorkerLaneStageState.Active -> "Active"
    WorkerLaneStageState.Done -> "Done"
    is WorkerLaneStageState.Blocked -> "Blocked"
    WorkerLaneStageState.Skipped -> "Skipped"
}

@Preview
@Composable
private fun JarvisWorkerLaneAllPendingPreview() {
    JarvisWorkerLane(state = WorkerLaneUiState.allPending())
}

@Preview
@Composable
private fun JarvisWorkerLaneMixedPreview() {
    JarvisWorkerLane(
        state = WorkerLaneUiState(
            listOf(
                WorkerLaneStage(WorkerLabel.PLANNER, WorkerLaneStageState.Done),
                WorkerLaneStage(WorkerLabel.NAVIGATOR, WorkerLaneStageState.Done),
                WorkerLaneStage(WorkerLabel.EDITOR, WorkerLaneStageState.Active),
                WorkerLaneStage(WorkerLabel.EXECUTOR, WorkerLaneStageState.Pending),
                WorkerLaneStage(WorkerLabel.REVIEWER, WorkerLaneStageState.Pending),
                WorkerLaneStage(WorkerLabel.VERIFIER, WorkerLaneStageState.Pending),
                WorkerLaneStage(WorkerLabel.PUBLISHER, WorkerLaneStageState.Pending)
            )
        )
    )
}

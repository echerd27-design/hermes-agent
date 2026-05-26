package com.aci.hermes.ui.jarvis.voice

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp

@Composable
fun VoiceCaptureScreen(
    state: VoiceCaptureState,
    onEducationContinue: () -> Unit,
    onEducationDecline: () -> Unit,
    onStartCapture: () -> Unit,
    onCaptureTranscript: (String) -> Unit,
    onSubmitTranscript: (String) -> Unit,
    onCancel: () -> Unit,
    onRetryEducation: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(modifier = modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier.fillMaxSize().padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            when (state.stage) {
                VoiceStage.EDUCATION,
                VoiceStage.REQUESTING_PERMISSION -> EducationBody(
                    requesting = state.stage == VoiceStage.REQUESTING_PERMISSION,
                    onContinue = onEducationContinue,
                    onDecline = onEducationDecline,
                )

                VoiceStage.READY -> ReadyBody(onStartCapture = onStartCapture, onCancel = onCancel)
                VoiceStage.CAPTURING -> CapturingBody(onCaptureTranscript = onCaptureTranscript, onCancel = onCancel)
                VoiceStage.REVIEWING -> ReviewingBody(
                    transcript = state.transcript,
                    onSubmit = { onSubmitTranscript(state.transcript) },
                    onCancel = onCancel,
                )

                VoiceStage.DENIED -> DeniedBody(onRetryEducation = onRetryEducation, onCancel = onCancel)
            }
            state.error?.takeIf { it.isNotBlank() }?.let { msg ->
                Text(
                    text = msg,
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
    }
}

@Composable
private fun EducationBody(requesting: Boolean, onContinue: () -> Unit, onDecline: () -> Unit) {
    Text(
        text = VoiceEducationContent.TITLE,
        style = MaterialTheme.typography.headlineSmall,
        fontWeight = FontWeight.SemiBold,
    )
    VoiceEducationContent.BODY_PARAGRAPHS.forEach { paragraph ->
        Text(text = paragraph, style = MaterialTheme.typography.bodyMedium)
    }
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp, Alignment.End),
    ) {
        TextButton(onClick = onDecline, enabled = !requesting) {
            Text(VoiceEducationContent.DECLINE_LABEL)
        }
        Button(onClick = onContinue, enabled = !requesting) {
            Text(if (requesting) "Requesting…" else VoiceEducationContent.CONTINUE_LABEL)
        }
    }
}

@Composable
private fun ReadyBody(onStartCapture: () -> Unit, onCancel: () -> Unit) {
    Text(
        text = "Mic ready. Tap to speak.",
        style = MaterialTheme.typography.titleMedium,
    )
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp, Alignment.End),
    ) {
        TextButton(onClick = onCancel) { Text("Cancel") }
        Button(onClick = onStartCapture) { Text("Start") }
    }
}

@Composable
private fun CapturingBody(onCaptureTranscript: (String) -> Unit, onCancel: () -> Unit) {
    // Backend wiring will replace this stub with a real audio + STT pipeline.
    // For W09 the operator types the transcript so the state machine can be
    // exercised end-to-end in previews and tests without an emulator mic.
    var draft by remember { mutableStateOf("") }
    Text(
        text = "Listening…",
        style = MaterialTheme.typography.titleMedium,
    )
    Text(
        text = "Voice backend is wired in a later wave. For now, type what you would have said.",
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    OutlinedTextField(
        value = draft,
        onValueChange = { draft = it },
        modifier = Modifier.fillMaxWidth(),
        placeholder = { Text("Spoken text") },
    )
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp, Alignment.End),
    ) {
        TextButton(onClick = onCancel) { Text("Cancel") }
        Button(onClick = { onCaptureTranscript(draft) }, enabled = draft.isNotBlank()) {
            Text("Stop")
        }
    }
}

@Composable
private fun ReviewingBody(transcript: String, onSubmit: () -> Unit, onCancel: () -> Unit) {
    Text(
        text = "Review",
        style = MaterialTheme.typography.titleMedium,
    )
    Text(text = transcript, style = MaterialTheme.typography.bodyMedium)
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp, Alignment.End),
    ) {
        TextButton(onClick = onCancel) { Text("Discard") }
        Button(onClick = onSubmit) { Text("Send to Jarvis") }
    }
}

@Composable
private fun DeniedBody(onRetryEducation: () -> Unit, onCancel: () -> Unit) {
    Text(
        text = "Microphone disabled",
        style = MaterialTheme.typography.titleMedium,
    )
    Text(text = VoiceEducationContent.DENIED_HINT, style = MaterialTheme.typography.bodyMedium)
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp, Alignment.End),
    ) {
        OutlinedButton(onClick = onRetryEducation) { Text("Read again") }
        TextButton(onClick = onCancel) { Text("Close") }
    }
}

@Preview(name = "Education", showBackground = true)
@Composable
fun VoiceCaptureEducationPreview() {
    MaterialTheme {
        VoiceCaptureScreen(
            state = VoiceCaptureState(),
            onEducationContinue = {},
            onEducationDecline = {},
            onStartCapture = {},
            onCaptureTranscript = {},
            onSubmitTranscript = {},
            onCancel = {},
            onRetryEducation = {},
        )
    }
}

@Preview(name = "Reviewing", showBackground = true)
@Composable
fun VoiceCaptureReviewingPreview() {
    MaterialTheme {
        VoiceCaptureScreen(
            state = VoiceCaptureState(stage = VoiceStage.REVIEWING, transcript = "Plan tomorrow's deep-work block."),
            onEducationContinue = {},
            onEducationDecline = {},
            onStartCapture = {},
            onCaptureTranscript = {},
            onSubmitTranscript = {},
            onCancel = {},
            onRetryEducation = {},
        )
    }
}

@Preview(name = "Denied", showBackground = true)
@Composable
fun VoiceCaptureDeniedPreview() {
    MaterialTheme {
        VoiceCaptureScreen(
            state = VoiceCaptureState(stage = VoiceStage.DENIED),
            onEducationContinue = {},
            onEducationDecline = {},
            onStartCapture = {},
            onCaptureTranscript = {},
            onSubmitTranscript = {},
            onCancel = {},
            onRetryEducation = {},
        )
    }
}

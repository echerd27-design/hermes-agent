package com.aci.hermes.ui.jarvis.voice

import androidx.lifecycle.ViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

open class VoiceCaptureViewModel(
    private val permission: MicPermissionState = StubMicPermissionState(),
) : ViewModel() {

    private val _uiState = MutableStateFlow(VoiceCaptureState())
    val uiState: StateFlow<VoiceCaptureState> = _uiState.asStateFlow()

    fun onEducationContinue() {
        if (_uiState.value.stage != VoiceStage.EDUCATION) return
        _uiState.update { it.copy(stage = VoiceStage.REQUESTING_PERMISSION, error = null) }
        permission.requestPermission()
        _uiState.update {
            it.copy(stage = if (permission.isGranted) VoiceStage.READY else VoiceStage.DENIED)
        }
    }

    fun onStartCapture() {
        val current = _uiState.value
        if (current.stage != VoiceStage.READY) return
        if (!permission.isGranted) {
            _uiState.update { it.copy(stage = VoiceStage.DENIED, error = "Microphone permission not granted.") }
            return
        }
        _uiState.update { it.copy(stage = VoiceStage.CAPTURING, transcript = "", error = null) }
    }

    fun onCaptureTranscript(text: String) {
        if (_uiState.value.stage != VoiceStage.CAPTURING) return
        _uiState.update { it.copy(stage = VoiceStage.REVIEWING, transcript = text) }
    }

    fun onSubmit(): String {
        val current = _uiState.value
        if (current.stage != VoiceStage.REVIEWING) return ""
        val out = current.transcript
        _uiState.update { VoiceCaptureState() }
        return out
    }

    fun onCancel() {
        _uiState.update { VoiceCaptureState() }
    }

    fun onRetryEducation() {
        _uiState.update { VoiceCaptureState() }
    }
}

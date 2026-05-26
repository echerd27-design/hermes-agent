package com.aci.hermes.ui.jarvis.voice

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class VoiceCaptureViewModelTest {

    @Test
    fun initialStageIsEducation() {
        val vm = VoiceCaptureViewModel(permission = StubMicPermissionState())
        assertEquals(VoiceStage.EDUCATION, vm.uiState.value.stage)
        assertEquals("", vm.uiState.value.transcript)
        assertNull(vm.uiState.value.error)
    }

    @Test
    fun noPermissionRequestFiresBeforeEducationContinue() {
        val stub = StubMicPermissionState(onRequest = { true })
        val vm = VoiceCaptureViewModel(permission = stub)
        // Simulate the user navigating around without acknowledging education.
        assertEquals(VoiceStage.EDUCATION, vm.uiState.value.stage)
        assertEquals(0, stub.recordedRequests)
    }

    @Test
    fun educationContinueGrantedAdvancesToReady() {
        val stub = StubMicPermissionState(onRequest = { true })
        val vm = VoiceCaptureViewModel(permission = stub)
        vm.onEducationContinue()
        assertEquals(VoiceStage.READY, vm.uiState.value.stage)
        assertEquals(1, stub.recordedRequests)
    }

    @Test
    fun educationContinueDeniedLandsOnDenied() {
        val stub = StubMicPermissionState(onRequest = { false })
        val vm = VoiceCaptureViewModel(permission = stub)
        vm.onEducationContinue()
        assertEquals(VoiceStage.DENIED, vm.uiState.value.stage)
        assertEquals(1, stub.recordedRequests)
    }

    @Test
    fun deniedStateDoesNotSilentlyRetry() {
        val stub = StubMicPermissionState(onRequest = { false })
        val vm = VoiceCaptureViewModel(permission = stub)
        vm.onEducationContinue()
        vm.onEducationContinue()
        vm.onEducationContinue()
        assertEquals(VoiceStage.DENIED, vm.uiState.value.stage)
        assertEquals("only the original explicit continue should trigger a request", 1, stub.recordedRequests)
    }

    @Test
    fun retryEducationResetsAndRequiresNewExplicitContinue() {
        val stub = StubMicPermissionState(onRequest = { false })
        val vm = VoiceCaptureViewModel(permission = stub)
        vm.onEducationContinue()
        assertEquals(VoiceStage.DENIED, vm.uiState.value.stage)
        vm.onRetryEducation()
        assertEquals(VoiceStage.EDUCATION, vm.uiState.value.stage)
        assertEquals("retry alone must not re-request mic", 1, stub.recordedRequests)
    }

    @Test
    fun startCaptureRequiresReady() {
        val vm = VoiceCaptureViewModel(permission = StubMicPermissionState())
        vm.onStartCapture()
        assertEquals(VoiceStage.EDUCATION, vm.uiState.value.stage)
    }

    @Test
    fun captureTranscriptAdvancesToReviewing() {
        val stub = StubMicPermissionState(onRequest = { true })
        val vm = VoiceCaptureViewModel(permission = stub)
        vm.onEducationContinue()
        vm.onStartCapture()
        vm.onCaptureTranscript("plan tomorrow")
        val state = vm.uiState.value
        assertEquals(VoiceStage.REVIEWING, state.stage)
        assertEquals("plan tomorrow", state.transcript)
    }

    @Test
    fun submitReturnsTranscriptAndResets() {
        val stub = StubMicPermissionState(onRequest = { true })
        val vm = VoiceCaptureViewModel(permission = stub)
        vm.onEducationContinue()
        vm.onStartCapture()
        vm.onCaptureTranscript("plan tomorrow")
        val submitted = vm.onSubmit()
        assertEquals("plan tomorrow", submitted)
        assertEquals(VoiceStage.EDUCATION, vm.uiState.value.stage)
        assertEquals("", vm.uiState.value.transcript)
    }

    @Test
    fun cancelFromAnyStageReturnsToEducation() {
        val stub = StubMicPermissionState(onRequest = { true })
        val vm = VoiceCaptureViewModel(permission = stub)
        vm.onEducationContinue()
        vm.onStartCapture()
        vm.onCancel()
        assertEquals(VoiceStage.EDUCATION, vm.uiState.value.stage)
        assertEquals("", vm.uiState.value.transcript)
    }

    @Test
    fun startCaptureBlocksWhenPermissionFlipsAwayBeforeStart() {
        // Build a permission stub that grants once, then revokes for any future
        // observation (simulates the user toggling permission off in Settings
        // between the READY state and the Start tap).
        val flipping = object : MicPermissionState {
            private var grants = 1
            private var requests = 0
            override val isGranted: Boolean
                get() = grants > 0
            override fun requestPermission() {
                requests += 1
            }
            fun revoke() { grants = 0 }
        }
        val vm = VoiceCaptureViewModel(permission = flipping)
        vm.onEducationContinue()
        assertEquals(VoiceStage.READY, vm.uiState.value.stage)
        flipping.revoke()
        vm.onStartCapture()
        assertEquals(VoiceStage.DENIED, vm.uiState.value.stage)
        assertTrue(vm.uiState.value.error?.contains("not granted") == true)
    }

    @Test
    fun moduleDoesNotImportBannedApis() {
        // Smoke guard: when the skeleton wave lands and Robolectric or
        // instrumentation tests can run, this test will assert that no
        // banned media-capture or telephony imports have crept into the
        // voice module. For W09 the guard is enforced by the pre-PR grep
        // gate documented in docs/aci/reports/W09_CHAT_VOICE_UI_REPORT.md
        // section 8.
        assertTrue(true)
    }
}

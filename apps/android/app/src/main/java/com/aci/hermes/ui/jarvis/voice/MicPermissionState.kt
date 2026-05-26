// Tap-to-speak permission abstraction.
//
// A future wave will provide an implementation backed by Accompanist
// Permissions or AndroidX `ActivityResultContracts.RequestPermission`.
// The W09 wave intentionally keeps this an interface so the chat/voice
// composables and ViewModel can be exercised in previews and unit tests
// without touching the real Android permission API or modifying the
// AndroidManifest (the Manifest itself is on this wave's FORBIDDEN list;
// the required `<uses-permission android:name="android.permission.RECORD_AUDIO" />`
// follow-up is documented in docs/aci/reports/W09_CHAT_VOICE_UI_REPORT.md).
package com.aci.hermes.ui.jarvis.voice

interface MicPermissionState {
    val isGranted: Boolean
    fun requestPermission()
}

class StubMicPermissionState(
    initiallyGranted: Boolean = false,
    private val onRequest: () -> Boolean = { false },
) : MicPermissionState {

    private var grantedState: Boolean = initiallyGranted
    private var requestCount: Int = 0

    override val isGranted: Boolean
        get() = grantedState

    val recordedRequests: Int
        get() = requestCount

    override fun requestPermission() {
        requestCount += 1
        grantedState = onRequest()
    }
}

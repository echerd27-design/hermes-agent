/*
 * Jarvis Prime — Memory Transparency models (W10 spec-only delivery).
 *
 * Spec-only: this file is shipped from the Python Hermes runtime repo
 * (echerd27-design/hermes-agent) and does NOT compile here — there is no
 * Gradle, no Android SDK, and no app module. Intended consumer is the
 * Android module in A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent for the
 * W10 Memory + Proof UI wave.
 *
 * TODO on integration: extract user-visible strings to res/values/strings.xml
 * inside the consuming module.
 */
package com.aci.hermes.ui.jarvis.memory

/** A single fact Jarvis Prime believes about the user. */
data class MemoryRecord(
    val id: String,
    val fact: String,
    val confidence: MemoryConfidence,
    val source: MemorySource,
    val reason: String,
)

/** Confidence tier surfaced on each memory card. */
enum class MemoryConfidence {
    HIGH,
    MEDIUM,
    LOW;

    fun label(): String = when (this) {
        HIGH -> "High"
        MEDIUM -> "Medium"
        LOW -> "Low"
    }
}

/**
 * Pointer back to the evidence/proof that produced this memory.
 * `proofId` is a placeholder — the UI calls back into the host with this id
 * and the host resolves navigation to the proof record.
 */
data class MemorySource(
    val label: String,
    val proofId: String?,
)

/** UI state for the Memory Transparency screen. */
sealed class MemoryTransparencyUiState {
    object Loading : MemoryTransparencyUiState()
    object Empty : MemoryTransparencyUiState()
    data class Loaded(val records: List<MemoryRecord>) : MemoryTransparencyUiState()
    data class Error(val message: String) : MemoryTransparencyUiState()

    companion object {
        /** Convenience: empty list -> Empty, non-empty -> Loaded. */
        fun fromRecords(records: List<MemoryRecord>): MemoryTransparencyUiState =
            if (records.isEmpty()) Empty else Loaded(records)
    }
}

/**
 * Callback surface used by the screen.
 *
 * The W10 wave deliberately exposes intent only — implementations live
 * in the host. No actual deletion or backend mutation happens in this wave.
 */
interface MemoryTransparencyCallbacks {
    fun onEdit(memoryId: String)
    fun onDelete(memoryId: String)
    fun onViewProof(proofId: String)
}

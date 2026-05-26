/*
 * Jarvis Prime — MemoryTransparencyUiState.fromRecords tests (W10 spec-only).
 *
 * Pure JVM unit test. No Android framework imports. Safe to run as a plain
 * JUnit suite in the consuming Android repo
 * (A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent).
 *
 * Does NOT run in echerd27-design/hermes-agent (no Gradle / JUnit here).
 */
package com.aci.hermes.ui.jarvis.memory

import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class MemoryTransparencyUiStateTest {

    @Test
    fun fromRecords_emptyList_returnsEmpty() {
        val state = MemoryTransparencyUiState.fromRecords(emptyList())
        assertTrue(state is MemoryTransparencyUiState.Empty)
    }

    @Test
    fun fromRecords_nonEmpty_returnsLoadedWithRecords() {
        val records = listOf(
            MemoryRecord(
                id = "m-1",
                fact = "User prefers terse responses.",
                confidence = MemoryConfidence.HIGH,
                source = MemorySource(label = "Conversation 2026-05-01", proofId = "p-42"),
                reason = "User said so directly.",
            ),
        )
        val state = MemoryTransparencyUiState.fromRecords(records)
        assertTrue(state is MemoryTransparencyUiState.Loaded)
        assertEquals(records, state.records)
    }
}

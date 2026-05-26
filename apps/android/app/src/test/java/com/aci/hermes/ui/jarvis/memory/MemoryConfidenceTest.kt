/*
 * Jarvis Prime — MemoryConfidence label tests (W10 spec-only delivery).
 *
 * Pure JVM unit test. No Android framework imports — safe to run as a plain
 * JUnit suite once a Gradle test source set wraps this file in the consuming
 * Android repo (A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent).
 *
 * Does NOT run in echerd27-design/hermes-agent: no Gradle, no JUnit on the
 * classpath here.
 */
package com.aci.hermes.ui.jarvis.memory

import org.junit.Test
import kotlin.test.assertEquals

class MemoryConfidenceTest {
    @Test
    fun high_label_is_High() {
        assertEquals("High", MemoryConfidence.HIGH.label())
    }

    @Test
    fun medium_label_is_Medium() {
        assertEquals("Medium", MemoryConfidence.MEDIUM.label())
    }

    @Test
    fun low_label_is_Low() {
        assertEquals("Low", MemoryConfidence.LOW.label())
    }
}

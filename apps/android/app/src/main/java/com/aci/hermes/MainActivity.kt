/*
 * Jarvis Prime — MainActivity (W10 scaffold).
 *
 * Sprint-header override: MainActivity was on the FORBIDDEN list; the user
 * explicitly opted to scaffold it so the W10 memory + proof surfaces are
 * reachable in a debug build. This implementation deliberately stays minimal:
 *
 * - No NavController, no nav-graph library, no DI.
 * - No backend, no ViewModel, no coroutine work.
 * - Two callback stubs that just log; nothing is actually deleted, edited,
 *   rolled back, or fetched.
 * - Memory + proof state is static sample data baked into the Activity so
 *   the UI renders in `assembleDebug` without any backing service.
 */
package com.aci.hermes

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.aci.hermes.ui.jarvis.memory.MemoryConfidence
import com.aci.hermes.ui.jarvis.memory.MemoryRecord
import com.aci.hermes.ui.jarvis.memory.MemorySource
import com.aci.hermes.ui.jarvis.memory.MemoryTransparencyCallbacks
import com.aci.hermes.ui.jarvis.memory.MemoryTransparencyScreen
import com.aci.hermes.ui.jarvis.memory.MemoryTransparencyUiState
import com.aci.hermes.ui.jarvis.proof.ApprovalEvent
import com.aci.hermes.ui.jarvis.proof.ChangedFile
import com.aci.hermes.ui.jarvis.proof.ProofHistoryCallbacks
import com.aci.hermes.ui.jarvis.proof.ProofHistoryScreen
import com.aci.hermes.ui.jarvis.proof.ProofHistoryUiState
import com.aci.hermes.ui.jarvis.proof.ProofRecord
import com.aci.hermes.ui.jarvis.proof.TestEvidence
import com.aci.hermes.ui.theme.JarvisPrimeTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            JarvisPrimeTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    JarvisPrimeRoot()
                }
            }
        }
    }
}

private enum class Surface { Picker, Memory, Proof }

@Composable
private fun JarvisPrimeRoot() {
    var current by remember { mutableStateOf(Surface.Picker) }

    when (current) {
        Surface.Picker -> SurfacePicker(
            onMemory = { current = Surface.Memory },
            onProof = { current = Surface.Proof },
        )
        Surface.Memory -> MemoryTransparencyScreen(
            state = MemoryTransparencyUiState.fromRecords(SampleData.memories),
            callbacks = NoOpMemoryCallbacks,
        )
        Surface.Proof -> ProofHistoryScreen(
            state = ProofHistoryUiState.fromRecords(SampleData.proofs),
            callbacks = NoOpProofCallbacks,
        )
    }
}

@Composable
private fun SurfacePicker(onMemory: () -> Unit, onProof: () -> Unit) {
    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                text = "Jarvis Prime — W10 preview",
                style = MaterialTheme.typography.titleLarge,
            )
            Text(
                text = "Pick a surface to render. No backend; sample data only.",
                style = MaterialTheme.typography.bodyMedium,
            )
            Button(onClick = onMemory) { Text("Memory transparency") }
            Button(onClick = onProof) { Text("Proof history") }
        }
    }
}

private object NoOpMemoryCallbacks : MemoryTransparencyCallbacks {
    override fun onEdit(memoryId: String) { /* W10 wave: callback only */ }
    override fun onDelete(memoryId: String) { /* W10 wave: no real deletion */ }
    override fun onViewProof(proofId: String) { /* W10 wave: no nav */ }
}

private object NoOpProofCallbacks : ProofHistoryCallbacks {
    override fun onRollback(proofId: String) { /* W10 wave: no rollback */ }
    override fun onOpenFile(path: String) { /* W10 wave: no editor */ }
}

private object SampleData {
    val memories: List<MemoryRecord> = listOf(
        MemoryRecord(
            id = "m-1",
            fact = "User prefers terse responses.",
            confidence = MemoryConfidence.HIGH,
            source = MemorySource(label = "Conversation on 2026-05-01", proofId = "p-1"),
            reason = "User said so directly twice in the past week.",
        ),
        MemoryRecord(
            id = "m-2",
            fact = "User is building Jarvis Prime in spare hours.",
            confidence = MemoryConfidence.MEDIUM,
            source = MemorySource(label = "Inferred from session times", proofId = null),
            reason = "Sessions cluster between 9 PM and 1 AM local time.",
        ),
        MemoryRecord(
            id = "m-3",
            fact = "User dislikes verbose explanations of what just happened.",
            confidence = MemoryConfidence.LOW,
            source = MemorySource(label = "Single feedback note", proofId = "p-2"),
            reason = "Mentioned once during a code review.",
        ),
    )

    val proofs: List<ProofRecord> = listOf(
        ProofRecord(
            id = "p-1",
            action = "Refactored memory store backing layer",
            timestamp = "2026-05-26 14:02",
            tests = listOf(
                TestEvidence(suite = "memoryStoreTest", passed = 12, failed = 0),
                TestEvidence(suite = "memoryStoreIntegrationTest", passed = 4, failed = 0),
            ),
            files = listOf(
                ChangedFile(path = "memory/Store.kt", added = 42, removed = 18),
                ChangedFile(path = "memory/StoreTest.kt", added = 16, removed = 0),
            ),
            approvals = listOf(
                ApprovalEvent(actor = "echerd27", decision = "approved", timestamp = "2026-05-26 14:05"),
            ),
            hasRollback = true,
        ),
        ProofRecord(
            id = "p-2",
            action = "Tuned confidence scoring threshold",
            timestamp = "2026-05-25 21:30",
            tests = listOf(
                TestEvidence(suite = "confidenceTest", passed = 7, failed = 1),
            ),
            files = listOf(
                ChangedFile(path = "memory/Confidence.kt", added = 3, removed = 1),
            ),
            approvals = emptyList(),
            hasRollback = false,
        ),
    )
}

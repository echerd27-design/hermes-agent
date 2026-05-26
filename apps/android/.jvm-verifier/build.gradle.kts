/*
 * Jarvis Prime — W10 JVM verifier.
 *
 * Compiles only the pure-Kotlin pieces of the W10 delivery (the data classes,
 * sealed states, callback interfaces, and small helpers) plus the three
 * JUnit suites. Skips every Composable file — those need the Android SDK and
 * Compose runtime, which aren't available in this remote environment.
 *
 * Run from this directory:
 *     gradle test
 *
 * Or against this build from the repo root:
 *     gradle -p apps/android/.jvm-verifier test
 *
 * If all three tests pass, the W10 model layer and helpers are validated.
 */
plugins {
    kotlin("jvm") version "2.0.21"
}

repositories {
    mavenCentral()
}

dependencies {
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlin:kotlin-test:2.0.21")
}

sourceSets {
    main {
        java.setSrcDirs(listOf("../app/src/main/java"))
        // Only the pure-Kotlin model files compile here — every other .kt file
        // pulls in androidx.compose.* and would need the Android SDK.
        java.include(
            "com/aci/hermes/ui/jarvis/memory/MemoryModels.kt",
            "com/aci/hermes/ui/jarvis/proof/ProofModels.kt",
        )
    }
    test {
        java.setSrcDirs(listOf("../app/src/test/java"))
    }
}

tasks.test {
    useJUnit()
    testLogging {
        events("passed", "failed", "skipped")
    }
}

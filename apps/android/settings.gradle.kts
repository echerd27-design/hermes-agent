/*
 * Jarvis Prime — Android module settings (W10 scaffold).
 *
 * Sprint-header override: this file (and the rest of the Android scaffold)
 * was added to make the W10 memory + proof UI buildable. The original sprint
 * header forbids Gradle files; the user explicitly overrode that rule so
 * the module is no longer a paper spec.
 *
 * The .jvm-verifier sibling build is intentionally NOT included here — it
 * is a standalone Kotlin/JVM build that validates pure-Kotlin pieces
 * without dragging in the Android Gradle Plugin.
 */
pluginManagement {
    repositories {
        gradlePluginPortal()
        google()
        mavenCentral()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "jarvis-prime-android"
include(":app")

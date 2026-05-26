/*
 * Standalone settings file so this verifier build does NOT inherit anything
 * from apps/android/settings.gradle.kts. We don't want the Android Gradle
 * Plugin loaded here — the verifier proves the pure-Kotlin pieces compile
 * and the JUnit tests pass without needing an Android SDK.
 */
rootProject.name = "w10-jvm-verifier"

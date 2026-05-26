/*
 * Jarvis Prime — Android root build (W10 scaffold).
 *
 * Plugin versions are declared without apply so each subproject opts in.
 * AGP 8.5 + Kotlin 2.0 + Compose Compiler plugin (Kotlin 2.0+ requirement).
 */
plugins {
    id("com.android.application") version "8.5.2" apply false
    id("org.jetbrains.kotlin.android") version "2.0.21" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.0.21" apply false
}

package com.aci.hermes.ui.jarvis.design

/**
 * Jarvis Prime semantic color tokens.
 *
 * Stored as 0xAARRGGBB Long values so this file stays free of any
 * androidx.compose import. Downstream Compose call sites wrap as
 * Color(JarvisColors.Gold). Keeps the token surface compile-clean
 * ahead of the Android Gradle skeleton wave.
 */
object JarvisColors {
    const val BaseNavy: Long = 0xFF0A0F1F
    const val BaseBlack: Long = 0xFF050810
    const val Gold: Long = 0xFFD4A640
    const val Cyan: Long = 0xFF38D6FF
    const val Red: Long = 0xFFE5484D
    const val Green: Long = 0xFF30A46C
    const val MutedGray: Long = 0xFF8A8F9B
    const val Warning: Long = 0xFFE6A23C
}

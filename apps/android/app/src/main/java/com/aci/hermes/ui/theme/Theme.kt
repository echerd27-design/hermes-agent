/*
 * Jarvis Prime — Material 3 theme (W10 scaffold).
 * Dynamic color on S+; falls back to the static palette in Color.kt below.
 */
package com.aci.hermes.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext

@Composable
fun JarvisPrimeTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit,
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> darkColorScheme(
            primary = JarvisPrimary,
            onPrimary = JarvisOnPrimary,
            tertiary = JarvisTertiary,
            onTertiary = JarvisOnTertiary,
            error = JarvisError,
            onError = JarvisOnError,
        )
        else -> lightColorScheme(
            primary = JarvisPrimary,
            onPrimary = JarvisOnPrimary,
            tertiary = JarvisTertiary,
            onTertiary = JarvisOnTertiary,
            error = JarvisError,
            onError = JarvisOnError,
        )
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = JarvisTypography,
        content = content,
    )
}

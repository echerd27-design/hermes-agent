package com.aci.hermes.ui.jarvis.notifications

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun NotificationCommandCenterScreen(
    state: NotificationCommandCenterState,
    onStateChange: (NotificationCommandCenterState) -> Unit,
    modifier: Modifier = Modifier,
) {
    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(vertical = 16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        item {
            Text(
                text = NotificationCenterCopy.SCREEN_TITLE,
                style = MaterialTheme.typography.headlineSmall,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        }
        item {
            NotificationEducationCard(
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        }
        item {
            Text(
                text = NotificationCenterCopy.PLACEHOLDER_NOTE,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        }
        items(
            items = NotificationCategory.values().toList(),
            key = { it.id },
        ) { category ->
            NotificationCategoryToggle(
                category = category,
                enabled = state.isEnabled(category),
                onEnabledChange = { next ->
                    onStateChange(state.withCategory(category, next))
                },
            )
            HorizontalDivider()
        }
    }
}

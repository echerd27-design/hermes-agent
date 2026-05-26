package com.aci.hermes.ui.jarvis.notifications

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun NotificationEducationCard(modifier: Modifier = Modifier) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.secondaryContainer,
            contentColor = MaterialTheme.colorScheme.onSecondaryContainer,
        ),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                text = NotificationCenterCopy.EDUCATION_HEADLINE,
                style = MaterialTheme.typography.titleMedium,
            )
            Text(
                text = NotificationCenterCopy.EDUCATION_BODY,
                style = MaterialTheme.typography.bodyMedium,
            )
            Text(
                text = NotificationCenterCopy.EDUCATION_FOOTNOTE,
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}

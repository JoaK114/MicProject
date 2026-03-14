package com.micproject.app

import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import com.micproject.app.network.ConnectionState

/**
 * Shared observable state between the Service and the UI.
 * Lightweight singleton — no heavy frameworks needed.
 */
object AppState {
    val connectionState = mutableStateOf(ConnectionState.DISCONNECTED)
    val isStreaming = mutableStateOf(false)
    val isMuted = mutableStateOf(false)
    val volume = mutableFloatStateOf(1.0f)
    val serverIP = mutableStateOf("Buscando...")
    val connectionMode = mutableStateOf("wifi") // "wifi", "usb", or "direct"
    val directIP = mutableStateOf("") // manual IP for direct connection
    val detectedServerIP = mutableStateOf("") // auto-detected PC IP from broadcast
    val connectionError = mutableStateOf("") // non-empty = show error alert
    val languageSelected = mutableStateOf(false) // tracks if language was picked this session
}

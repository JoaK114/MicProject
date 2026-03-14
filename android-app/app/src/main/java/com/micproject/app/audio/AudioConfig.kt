package com.micproject.app.audio

/**
 * Audio capture configuration constants.
 * Optimized for low latency and low bandwidth.
 */
object AudioConfig {
    const val SAMPLE_RATE = 48000          // Hz - standard for Opus
    const val CHANNELS = 1                  // Mono
    const val FRAME_DURATION_MS = 20        // 20ms frames (Opus standard)
    const val FRAME_SIZE = SAMPLE_RATE * FRAME_DURATION_MS / 1000  // 960 samples
    const val OPUS_BITRATE = 32000          // 32kbps - good quality for voice
    const val BUFFER_SIZE_FACTOR = 2        // AudioRecord buffer multiplier

    // Packet format: [2 bytes length][N bytes opus data]
    const val HEADER_SIZE = 2
}

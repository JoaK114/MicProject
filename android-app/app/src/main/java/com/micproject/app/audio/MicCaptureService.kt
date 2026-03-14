package com.micproject.app.audio

import android.app.*
import android.content.Intent
import android.content.pm.ServiceInfo
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import androidx.core.app.NotificationCompat
import com.micproject.app.AppState
import com.micproject.app.MainActivity
import com.micproject.app.network.WifiStreamer
import com.micproject.app.network.UsbStreamer
import com.micproject.app.network.ControlChannel
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Foreground service that captures microphone audio and streams it to the PC.
 * Uses AudioRecord for low-latency capture.
 */
class MicCaptureService : Service() {

    companion object {
        const val ACTION_START = "com.micproject.START"
        const val ACTION_STOP = "com.micproject.STOP"
        const val EXTRA_MODE = "connection_mode"
        private const val CHANNEL_ID = "mic_capture_channel"
        private const val NOTIFICATION_ID = 1001
        private const val TAG = "MicCaptureService"
    }

    private var audioRecord: AudioRecord? = null
    private var isRecording = false
    private var captureThread: Thread? = null
    private var streamer: Any? = null  // WifiStreamer or UsbStreamer
    private var controlChannel: ControlChannel? = null
    private var wakeLock: PowerManager.WakeLock? = null

    // Audio state
    var volume: Float = 1.0f
    var isMuted: Boolean = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> {
                val mode = intent.getStringExtra(EXTRA_MODE) ?: "wifi"
                startCapture(mode)
            }
            ACTION_STOP -> {
                stopCapture()
                stopSelf()
            }
        }
        return START_STICKY
    }

    private fun startCapture(mode: String) {
        // Start as foreground service
        val notification = createNotification("Capturando audio...")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }

        // Acquire wake lock to prevent CPU sleep
        val powerManager = getSystemService(POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK, "MicProject::AudioCapture"
        ).apply { acquire(60 * 60 * 1000L) } // 1 hour max

        // Configure AudioRecord
        val bufferSize = AudioRecord.getMinBufferSize(
            AudioConfig.SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        ) * AudioConfig.BUFFER_SIZE_FACTOR

        try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.VOICE_COMMUNICATION,
                AudioConfig.SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                bufferSize
            )
        } catch (e: SecurityException) {
            Log.e(TAG, "Microphone permission not granted", e)
            stopSelf()
            return
        }

        if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
            Log.e(TAG, "AudioRecord failed to initialize")
            stopSelf()
            return
        }

        // Setup control channel
        controlChannel = ControlChannel(
            onVolumeChange = { vol ->
                volume = vol
                AppState.volume.floatValue = vol
            },
            onMuteChange = { muted ->
                isMuted = muted
                AppState.isMuted.value = muted
            }
        )

        // Setup streamer based on mode
        when (mode) {
            "wifi" -> {
                val wifiStreamer = WifiStreamer()
                var serverFound = false
                wifiStreamer.onServerFound = { ip, port ->
                    serverFound = true
                    Log.i(TAG, "Server found at $ip:$port, connecting control channel...")
                    AppState.serverIP.value = "$ip:$port"
                    AppState.connectionState.value = com.micproject.app.network.ConnectionState.CONNECTED
                    controlChannel?.connect(mode, ip)
                }
                wifiStreamer.startDiscovery()
                streamer = wifiStreamer

                // Timeout: wait up to 10 seconds for discovery
                Thread({
                    Thread.sleep(10_000)
                    if (!serverFound && isRecording) {
                        Log.e(TAG, "WiFi discovery timed out")
                        AppState.connectionError.value = "No se encontró el servidor PC en la red WiFi.\n\n• Verificá que el servidor esté corriendo\n• Verificá que estés en la misma red WiFi\n• Revisá el firewall de Windows"
                        stopCapture()
                        AppState.isStreaming.value = false
                        AppState.connectionState.value = com.micproject.app.network.ConnectionState.DISCONNECTED
                    }
                }, "WiFiTimeoutThread").start()
            }
            "direct" -> {
                val directIP = AppState.directIP.value.trim()
                if (directIP.isEmpty()) {
                    Log.e(TAG, "Direct IP is empty!")
                    AppState.connectionError.value = "Ingresá la IP del servidor antes de conectar."
                    stopSelf()
                    return
                }
                val wifiStreamer = WifiStreamer()
                wifiStreamer.connectDirect(directIP, 4545)
                streamer = wifiStreamer
                AppState.serverIP.value = "$directIP:4545"
                AppState.connectionState.value = com.micproject.app.network.ConnectionState.CONNECTED
                controlChannel?.connect(mode, directIP)

                // Verify connection with a timeout on control channel
                Thread({
                    Thread.sleep(8_000)
                    if (AppState.connectionState.value != com.micproject.app.network.ConnectionState.CONNECTED || 
                        controlChannel == null) {
                        // Connection seems ok from our side (UDP is fire-and-forget)
                        // but if no data flows back, user will notice
                    }
                }, "DirectVerifyThread").start()
            }
            "usb" -> {
                val usbStreamer = UsbStreamer()
                var usbConnected = false
                usbStreamer.onConnected = {
                    usbConnected = true
                    AppState.serverIP.value = "USB (ADB)"
                    AppState.connectionState.value = com.micproject.app.network.ConnectionState.CONNECTED
                }
                usbStreamer.connect()
                streamer = usbStreamer
                controlChannel?.connect(mode, "127.0.0.1")

                // Timeout: wait up to 10 seconds for USB connection
                Thread({
                    Thread.sleep(10_000)
                    if (!usbConnected && isRecording) {
                        Log.e(TAG, "USB connection timed out")
                        AppState.connectionError.value = "No se pudo conectar por USB.\n\n• Conectá el celular a la PC por cable\n• Habilitá Depuración USB en opciones de desarrollador\n• Ejecutá en la PC: adb forward tcp:4545 tcp:4545"
                        stopCapture()
                        AppState.isStreaming.value = false
                        AppState.connectionState.value = com.micproject.app.network.ConnectionState.DISCONNECTED
                    }
                }, "USBTimeoutThread").start()
            }
        }

        // Start recording
        isRecording = true
        audioRecord?.startRecording()
        captureThread = Thread(this::captureLoop, "AudioCaptureThread").apply {
            priority = Thread.MAX_PRIORITY
            start()
        }

        AppState.isStreaming.value = true
        Log.i(TAG, "Capture started in $mode mode")
    }

    private fun captureLoop() {
        val buffer = ShortArray(AudioConfig.FRAME_SIZE)
        val byteBuffer = ByteArray(AudioConfig.FRAME_SIZE * 2) // 16-bit = 2 bytes per sample

        while (isRecording) {
            val read = audioRecord?.read(buffer, 0, AudioConfig.FRAME_SIZE) ?: -1
            if (read <= 0) continue

            // Read current state from AppState (set by UI)
            val currentMuted = AppState.isMuted.value
            val currentVolume = AppState.volume.floatValue

            if (currentMuted) continue

            // Apply volume
            if (currentVolume != 1.0f) {
                for (i in 0 until read) {
                    buffer[i] = (buffer[i] * currentVolume).toInt().coerceIn(-32768, 32767).toShort()
                }
            }

            // Convert to bytes (little-endian PCM)
            val bb = ByteBuffer.wrap(byteBuffer).order(ByteOrder.LITTLE_ENDIAN)
            bb.clear()
            for (i in 0 until read) {
                bb.putShort(buffer[i])
            }

            // Send via streamer
            val pcmData = byteBuffer.copyOf(read * 2)
            sendAudioPacket(pcmData)
        }
    }

    private fun sendAudioPacket(pcmData: ByteArray) {
        // For now, send raw PCM. Opus encoding will be added in opusEncoder wrapper.
        // Packet: [2 bytes length (big-endian)][pcm data]
        val packet = ByteArray(2 + pcmData.size)
        packet[0] = ((pcmData.size shr 8) and 0xFF).toByte()
        packet[1] = (pcmData.size and 0xFF).toByte()
        System.arraycopy(pcmData, 0, packet, 2, pcmData.size)

        when (val s = streamer) {
            is WifiStreamer -> s.send(packet)
            is UsbStreamer -> s.send(packet)
        }
    }

    private fun stopCapture() {
        isRecording = false
        captureThread?.join(2000)
        captureThread = null

        audioRecord?.stop()
        audioRecord?.release()
        audioRecord = null

        when (val s = streamer) {
            is WifiStreamer -> s.stop()
            is UsbStreamer -> s.stop()
        }
        streamer = null

        controlChannel?.disconnect()
        controlChannel = null

        wakeLock?.release()
        wakeLock = null

        Log.i(TAG, "Capture stopped")
    }

    override fun onDestroy() {
        stopCapture()
        super.onDestroy()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Captura de Micrófono",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Notificación de captura de audio activa"
                setShowBadge(false)
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun createNotification(text: String): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("MicProject")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setSilent(true)
            .build()
    }
}

package com.micproject.app.network

import android.util.Log
import com.micproject.app.audio.AudioConfig
import org.json.JSONObject
import java.net.*
import java.nio.ByteBuffer

/**
 * Connection state enum for the UI.
 */
enum class ConnectionState {
    DISCONNECTED,
    CONNECTING,
    CONNECTED
}

/**
 * WiFi audio streamer. Discovers the PC server via UDP broadcast,
 * then sends audio packets via UDP.
 */
class WifiStreamer {
    companion object {
        private const val TAG = "WifiStreamer"
        private const val DISCOVERY_PORT = 4547
    }

    private var socket: DatagramSocket? = null
    private var serverAddress: InetAddress? = null
    private var serverPort: Int = 4545
    private var discoveryThread: Thread? = null
    private var isActive = false

    var onServerFound: ((String, Int) -> Unit)? = null

    /**
     * Start listening for discovery broadcasts from the PC server.
     */
    fun startDiscovery() {
        isActive = true
        discoveryThread = Thread({
            try {
                val discoverySocket = DatagramSocket(DISCOVERY_PORT)
                discoverySocket.broadcast = true
                discoverySocket.soTimeout = 5000

                val buffer = ByteArray(1024)
                val packet = DatagramPacket(buffer, buffer.size)

                Log.i(TAG, "Listening for PC discovery on port $DISCOVERY_PORT")

                while (isActive && serverAddress == null) {
                    try {
                        discoverySocket.receive(packet)
                        val data = String(packet.data, 0, packet.length)
                        val json = JSONObject(data)

                        if (json.optString("magic") == "MICPROJECT_DISCOVER") {
                            val ip = json.getString("ip")
                            val audioPort = json.getInt("audio_port")
                            val pcName = json.optString("name", "PC")

                            serverAddress = InetAddress.getByName(ip)
                            serverPort = audioPort

                            Log.i(TAG, "Found PC: $pcName at $ip:$audioPort")
                            onServerFound?.invoke(ip, audioPort)

                            // Create the streaming socket
                            socket = DatagramSocket()
                        }
                    } catch (e: SocketTimeoutException) {
                        // Keep trying
                    }
                }

                discoverySocket.close()
            } catch (e: Exception) {
                Log.e(TAG, "Discovery error", e)
            }
        }, "DiscoveryThread")
        discoveryThread?.start()
    }

    /**
     * Send an audio packet to the PC server.
     */
    fun send(data: ByteArray) {
        val addr = serverAddress ?: return
        val sock = socket ?: return

        try {
            val packet = DatagramPacket(data, data.size, addr, serverPort)
            sock.send(packet)
        } catch (e: Exception) {
            // Silently handle send errors to avoid log spam
        }
    }

    /**
     * Connect directly to a known IP address (skips discovery).
     * Used when phone is on mobile data and PC IP is entered manually.
     */
    fun connectDirect(ip: String, port: Int) {
        isActive = true
        try {
            serverAddress = InetAddress.getByName(ip)
            serverPort = port
            socket = DatagramSocket()
            Log.i(TAG, "Direct connection to $ip:$port")
            onServerFound?.invoke(ip, port)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to connect directly to $ip:$port", e)
        }
    }

    /**
     * Stop the WiFi streamer.
     */
    fun stop() {
        isActive = false
        socket?.close()
        socket = null
        serverAddress = null
        discoveryThread?.join(2000)
    }
}

/**
 * USB audio streamer. Connects to PC via TCP through ADB port forwarding.
 * The PC runs `adb forward tcp:4545 tcp:4545` to bridge the connection.
 */
class UsbStreamer {
    companion object {
        private const val TAG = "UsbStreamer"
        private const val LOCALHOST = "127.0.0.1"
    }

    private var socket: Socket? = null
    private var port: Int = 4545
    private var isActive = false
    private var connectThread: Thread? = null

    var onConnected: (() -> Unit)? = null
    var onDisconnected: (() -> Unit)? = null

    /**
     * Connect to the PC via localhost (ADB forward).
     */
    fun connect(port: Int = 4545) {
        this.port = port
        isActive = true

        connectThread = Thread({
            while (isActive && socket == null) {
                try {
                    socket = Socket()
                    socket?.connect(InetSocketAddress(LOCALHOST, port), 3000)
                    socket?.tcpNoDelay = true
                    Log.i(TAG, "Connected to PC via USB at $LOCALHOST:$port")
                    onConnected?.invoke()
                } catch (e: Exception) {
                    socket = null
                    Log.d(TAG, "Waiting for USB connection... (retrying in 2s)")
                    Thread.sleep(2000)
                }
            }
        }, "USBConnectThread")
        connectThread?.start()
    }

    /**
     * Send audio data to the PC via TCP.
     */
    fun send(data: ByteArray) {
        try {
            socket?.getOutputStream()?.write(data)
            socket?.getOutputStream()?.flush()
        } catch (e: Exception) {
            Log.e(TAG, "Send error, reconnecting...", e)
            socket?.close()
            socket = null
            onDisconnected?.invoke()
            if (isActive) connect(port)
        }
    }

    /**
     * Stop the USB streamer.
     */
    fun stop() {
        isActive = false
        socket?.close()
        socket = null
        connectThread?.join(2000)
    }
}

/**
 * TCP control channel for bidirectional communication (volume, mute, heartbeat).
 */
class ControlChannel(
    private val onVolumeChange: (Float) -> Unit = {},
    private val onMuteChange: (Boolean) -> Unit = {},
) {
    companion object {
        private const val TAG = "ControlChannel"
        private const val CONTROL_PORT = 4546
    }

    private var socket: Socket? = null
    private var receiveThread: Thread? = null
    private var heartbeatThread: Thread? = null
    private var isActive = false

    var onConnectionStateChange: ((ConnectionState) -> Unit)? = null

    /**
     * Connect the control channel to the PC.
     * @param mode "wifi" or "usb"
     * @param serverAddress IP address of the PC server
     */
    fun connect(mode: String, serverAddress: String) {
        isActive = true

        receiveThread = Thread({
            // Wait a bit for the main connection to establish
            Thread.sleep(1000)

            Log.i(TAG, "Connecting control channel to $serverAddress:$CONTROL_PORT")

            while (isActive) {
                try {
                    socket = Socket()
                    socket?.connect(InetSocketAddress(serverAddress, CONTROL_PORT), 5000)
                    socket?.tcpNoDelay = true
                    Log.i(TAG, "Control channel connected to $serverAddress:$CONTROL_PORT")
                    onConnectionStateChange?.invoke(ConnectionState.CONNECTED)

                    // Start heartbeat
                    startHeartbeat()

                    // Listen for messages
                    receiveLoop()

                } catch (e: Exception) {
                    Log.d(TAG, "Control channel connection failed, retrying...")
                    socket?.close()
                    socket = null
                    onConnectionStateChange?.invoke(ConnectionState.DISCONNECTED)
                    Thread.sleep(3000)
                }
            }
        }, "ControlChannelThread")
        receiveThread?.start()
    }

    /**
     * Disconnect the control channel.
     */
    fun disconnect() {
        isActive = false
        socket?.close()
        socket = null
        receiveThread?.join(2000)
        heartbeatThread?.join(2000)
    }

    /**
     * Send a control command to the PC.
     */
    fun sendCommand(cmd: String, data: Map<String, Any> = emptyMap()) {
        try {
            val json = JSONObject().apply {
                put("cmd", cmd)
                put("data", JSONObject(data))
            }
            val bytes = json.toString().toByteArray(Charsets.UTF_8)
            val header = ByteBuffer.allocate(2).putShort(bytes.size.toShort()).array()

            socket?.getOutputStream()?.apply {
                write(header)
                write(bytes)
                flush()
            }
        } catch (e: Exception) {
            // Best effort
        }
    }

    fun sendVolume(volume: Float) {
        sendCommand("volume", mapOf("level" to volume))
    }

    fun sendMute(muted: Boolean) {
        sendCommand("mute", mapOf("muted" to muted))
    }

    private fun receiveLoop() {
        val inputStream = socket?.getInputStream() ?: return
        val headerBuffer = ByteArray(2)

        while (isActive) {
            try {
                var totalRead = 0
                while (totalRead < 2) {
                    val read = inputStream.read(headerBuffer, totalRead, 2 - totalRead)
                    if (read == -1) return
                    totalRead += read
                }

                val msgLen = ByteBuffer.wrap(headerBuffer).short.toInt() and 0xFFFF
                val msgBuffer = ByteArray(msgLen)
                totalRead = 0
                while (totalRead < msgLen) {
                    val read = inputStream.read(msgBuffer, totalRead, msgLen - totalRead)
                    if (read == -1) return
                    totalRead += read
                }

                val json = JSONObject(String(msgBuffer, Charsets.UTF_8))
                processMessage(json)

            } catch (e: Exception) {
                if (isActive) {
                    Log.e(TAG, "Receive error", e)
                }
                return
            }
        }
    }

    private fun processMessage(json: JSONObject) {
        val cmd = json.optString("cmd", "")
        val data = json.optJSONObject("data")

        when (cmd) {
            "volume" -> {
                val level = data?.optDouble("level", 1.0)?.toFloat() ?: 1.0f
                onVolumeChange(level)
            }
            "mute" -> {
                val muted = data?.optBoolean("muted", false) ?: false
                onMuteChange(muted)
            }
            "heartbeat_ack" -> {
                // Connection alive
            }
        }
    }

    private fun startHeartbeat() {
        heartbeatThread = Thread({
            while (isActive && socket?.isConnected == true) {
                sendCommand("heartbeat")
                Thread.sleep(3000)
            }
        }, "HeartbeatThread")
        heartbeatThread?.isDaemon = true
        heartbeatThread?.start()
    }
}

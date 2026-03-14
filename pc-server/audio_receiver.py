"""
MicProject - Audio Receiver Module
Receives Opus-encoded audio over UDP (WiFi) or TCP (USB via ADB forward).
"""

import socket
import struct
import threading
import time

try:
    import opuslib
    HAS_OPUS = True
except Exception:
    HAS_OPUS = False
    print("[AudioReceiver] WARNING: opuslib not available. Using raw PCM mode.")


class AudioReceiver:
    """
    Base audio receiver that listens for audio packets and decodes them.
    
    Packet format (simple, low overhead):
        [2 bytes] payload length (uint16 big-endian)
        [N bytes] Opus-encoded audio data (or raw PCM if no Opus)
    """

    def __init__(self, audio_output, sample_rate: int = 48000,
                 channels: int = 1, frame_duration_ms: int = 20):
        self.audio_output = audio_output
        self.sample_rate = sample_rate
        self.channels = channels
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)

        # Opus decoder
        self._decoder = None
        if HAS_OPUS:
            try:
                self._decoder = opuslib.Decoder(sample_rate, channels)
            except Exception as e:
                print(f"[AudioReceiver] Opus decoder init failed: {e}")

        self._running = False
        self._thread = None
        self._stats = {"packets": 0, "bytes": 0, "errors": 0}

    def decode_packet(self, data: bytes) -> bytes | None:
        """Decode an Opus packet to PCM, or return raw PCM if no decoder."""
        if self._decoder:
            try:
                pcm = self._decoder.decode(data, self.frame_size)
                return pcm
            except Exception:
                self._stats["errors"] += 1
                return None
        else:
            # Assume raw PCM int16
            return data

    def stop(self):
        """Stop the receiver."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._thread = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def stats(self) -> dict:
        return self._stats.copy()


class WiFiReceiver(AudioReceiver):
    """Receives audio via UDP on the local network."""

    def __init__(self, audio_output, port: int = 4545, **kwargs):
        super().__init__(audio_output, **kwargs)
        self.port = port
        self._socket = None

    def start(self) -> bool:
        """Start listening for UDP audio packets."""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind(("0.0.0.0", self.port))
            self._socket.settimeout(1.0)
            self._running = True
            self._thread = threading.Thread(target=self._receive_loop, daemon=True)
            self._thread.start()
            print(f"[WiFiReceiver] Listening on UDP port {self.port}")
            return True
        except Exception as e:
            print(f"[WiFiReceiver] Failed to start: {e}")
            return False

    def _receive_loop(self):
        """Main receive loop for UDP packets."""
        while self._running:
            try:
                data, addr = self._socket.recvfrom(4096)
                if len(data) < 2:
                    continue

                # Parse packet: [2 bytes length][payload]
                payload_len = struct.unpack("!H", data[:2])[0]
                payload = data[2:2 + payload_len]

                if len(payload) != payload_len:
                    self._stats["errors"] += 1
                    continue

                pcm = self.decode_packet(payload)
                if pcm:
                    self.audio_output.write(pcm)
                    self._stats["packets"] += 1
                    self._stats["bytes"] += len(data)

            except socket.timeout:
                continue
            except OSError:
                if self._running:
                    time.sleep(0.1)
                break

    def stop(self):
        """Stop the WiFi receiver and close socket."""
        self._running = False
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        super().stop()


class USBReceiver(AudioReceiver):
    """Receives audio via TCP localhost (ADB port forwarding)."""

    def __init__(self, audio_output, port: int = 4545, **kwargs):
        super().__init__(audio_output, **kwargs)
        self.port = port
        self._server_socket = None
        self._client_socket = None

    def start(self) -> bool:
        """Start TCP server for USB audio (via ADB forward)."""
        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind(("127.0.0.1", self.port))
            self._server_socket.listen(1)
            self._server_socket.settimeout(1.0)
            self._running = True
            self._thread = threading.Thread(target=self._accept_loop, daemon=True)
            self._thread.start()
            print(f"[USBReceiver] Listening on TCP 127.0.0.1:{self.port}")
            return True
        except Exception as e:
            print(f"[USBReceiver] Failed to start: {e}")
            return False

    def _accept_loop(self):
        """Accept TCP connections and receive audio."""
        while self._running:
            try:
                self._client_socket, addr = self._server_socket.accept()
                self._client_socket.settimeout(1.0)
                print(f"[USBReceiver] Client connected: {addr}")
                self._receive_from_client()
            except socket.timeout:
                continue
            except OSError:
                if self._running:
                    time.sleep(0.1)

    def _receive_from_client(self):
        """Receive audio data from connected USB client."""
        buffer = b""
        while self._running and self._client_socket:
            try:
                data = self._client_socket.recv(4096)
                if not data:
                    print("[USBReceiver] Client disconnected")
                    break

                buffer += data

                # Process complete packets
                while len(buffer) >= 2:
                    payload_len = struct.unpack("!H", buffer[:2])[0]
                    total_len = 2 + payload_len
                    if len(buffer) < total_len:
                        break

                    payload = buffer[2:total_len]
                    buffer = buffer[total_len:]

                    pcm = self.decode_packet(payload)
                    if pcm:
                        self.audio_output.write(pcm)
                        self._stats["packets"] += 1
                        self._stats["bytes"] += total_len

            except socket.timeout:
                continue
            except OSError:
                break

        if self._client_socket:
            try:
                self._client_socket.close()
            except Exception:
                pass
            self._client_socket = None

    def stop(self):
        """Stop the USB receiver."""
        self._running = False
        if self._client_socket:
            try:
                self._client_socket.close()
            except Exception:
                pass
            self._client_socket = None
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None
        super().stop()

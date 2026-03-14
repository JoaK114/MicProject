"""
MicProject - Audio Output Module
Writes decoded PCM audio to VB-Cable virtual device with volume control.
"""

import threading
import collections
import numpy as np
import sounddevice as sd


class AudioOutput:
    """Manages audio output to a virtual cable device with jitter buffer."""

    def __init__(self, device_name: str = "CABLE Input", sample_rate: int = 48000,
                 channels: int = 1, buffer_size_ms: int = 60):
        self.device_name = device_name
        self.sample_rate = sample_rate
        self.channels = channels
        self.buffer_size_ms = buffer_size_ms
        self.volume = 1.0
        self.muted = False
        self.current_level = 0.0  # Used for VU meter

        # Jitter buffer: ring buffer of PCM frames
        buffer_frames = max(3, buffer_size_ms // 20)  # ~20ms per frame
        self._buffer = collections.deque(maxlen=buffer_frames * 2)
        self._lock = threading.Lock()

        self._stream = None
        self._device_index = None
        self._running = False

    def find_device(self) -> int | None:
        """Find the VB-Cable input device index."""
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if self.device_name.lower() in dev["name"].lower() and dev["max_output_channels"] > 0:
                return i
        return None

    def start(self) -> bool:
        """Start the audio output stream. Returns True on success."""
        self._device_index = self.find_device()
        if self._device_index is None:
            print(f"[AudioOutput] Device '{self.device_name}' not found!")
            print("[AudioOutput] Available devices:")
            for i, dev in enumerate(sd.query_devices()):
                if dev["max_output_channels"] > 0:
                    print(f"  [{i}] {dev['name']}")
            return False

        try:
            self._stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                device=self._device_index,
                blocksize=int(self.sample_rate * 0.02),  # 20ms blocks
                callback=self._audio_callback,
                latency="low",
            )
            self._stream.start()
            self._running = True
            dev_info = sd.query_devices(self._device_index)
            print(f"[AudioOutput] Streaming to: {dev_info['name']}")
            return True
        except Exception as e:
            print(f"[AudioOutput] Failed to start stream: {e}")
            return False

    def stop(self):
        """Stop the audio output stream."""
        self._running = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        with self._lock:
            self._buffer.clear()

    def write(self, pcm_data: bytes):
        """
        Write a PCM frame to the jitter buffer.
        pcm_data: raw int16 PCM bytes
        """
        if not self._running:
            return
        with self._lock:
            self._buffer.append(pcm_data)

    def set_volume(self, volume: float):
        """Set volume multiplier (0.0 to 2.0)."""
        self.volume = max(0.0, min(2.0, volume))

    def set_mute(self, muted: bool):
        """Set mute state."""
        self.muted = muted

    def toggle_mute(self) -> bool:
        """Toggle mute and return new state."""
        self.muted = not self.muted
        return self.muted

    def _audio_callback(self, outdata, frames, time_info, status):
        """sounddevice callback - fills output buffer from jitter buffer."""
        if status:
            pass  # Silently handle underflows

        with self._lock:
            if self._buffer and not self.muted:
                pcm_data = self._buffer.popleft()
                audio = np.frombuffer(pcm_data, dtype=np.int16).copy()

                # Calculate RMS (Root Mean Square) for VU meter (0.0 to 1.0 approx)
                if len(audio) > 0:
                    rms = np.sqrt(np.mean(np.square(audio.astype(np.float32))))
                    # Normalize against typical max 16-bit int (32768)
                    norm_level = min(1.0, rms / 32768.0)
                else:
                    norm_level = 0.0

                # Smooth decay for level
                self.current_level = max(norm_level, self.current_level * 0.8)

                # Apply volume
                if self.volume != 1.0:
                    audio = np.clip(
                        audio.astype(np.float32) * self.volume,
                        -32768, 32767
                    ).astype(np.int16)

                # Pad or trim to match requested frame count
                expected = frames * self.channels
                if len(audio) < expected:
                    audio = np.pad(audio, (0, expected - len(audio)))
                elif len(audio) > expected:
                    audio = audio[:expected]

                outdata[:, 0] = audio if self.channels == 1 else audio.reshape(-1, self.channels)[:, 0]
            else:
                # Silence
                self.current_level *= 0.8
                outdata.fill(0)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def device_info(self) -> dict | None:
        if self._device_index is not None:
            return sd.query_devices(self._device_index)
        return None

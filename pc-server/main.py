"""
MicProject - Main Entry Point
Starts all PC server components with minimal resource usage.
"""

import sys
import signal
import time
import threading
import ctypes

# ─── Single Instance Lock (Windows Mutex) ─────────────────────────────
# Prevents opening the app more than once at the same time.
_mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "Global\\MicProjectSingleInstance")
if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
    # Another instance is already running — show message and exit
    try:
        ctypes.windll.user32.MessageBoxW(
            0,
            "MicProject ya se está ejecutando.\nRevisa la bandeja del sistema (tray).",
            "MicProject",
            0x40  # MB_ICONINFORMATION
        )
    except Exception:
        pass
    sys.exit(0)

from i18n import load_language, save_language, show_language_picker, t
from config import Config
from audio_output import AudioOutput
from audio_receiver import WiFiReceiver, USBReceiver
from connection_manager import ConnectionManager
from hotkey_manager import HotkeyManager
from dashboard import DashboardApp


class MicProjectServer:
    """Main application coordinator."""

    def __init__(self):
        # Language selection on first launch
        lang = load_language()
        if not lang:
            lang = show_language_picker()
            save_language(lang)

        print("=" * 50)
        print(f"  MicProject - {t('app_subtitle')}")
        print("=" * 50)
        print()

        # Initialize components
        self.config = Config()

        self.audio_output = AudioOutput(
            device_name=self.config.get("audio", "device_name"),
            sample_rate=self.config.get("audio", "sample_rate"),
            channels=self.config.get("audio", "channels"),
            buffer_size_ms=self.config.get("audio", "buffer_size_ms"),
        )

        self.connection_mgr = ConnectionManager(self.config, self.audio_output)
        self.hotkey_mgr = HotkeyManager(self.config)
        self.dashboard = DashboardApp(self.config, self.audio_output,
                                       self.connection_mgr, self.hotkey_mgr)

        self.receiver = None
        self._running = False

    def start(self):
        """Start all services."""
        self._running = True

        # 1. Start audio output
        if not self.audio_output.start():
            print(f"\n[Main] ERROR: {t('audio_error')}")
            print(f"[Main] {t('vb_cable_missing')} https://vb-audio.com/Cable/")
            self.audio_output.start()
        else:
            print(f"[Main] ✅ Audio output {t('start').lower()}")

        # 2. Start receiver
        self._start_receiver()

        # 3. Start connection manager
        self.connection_mgr.on_connect = self._on_phone_connected
        self.connection_mgr.on_disconnect = self._on_phone_disconnected
        self.connection_mgr.on_volume_change = self._on_volume_changed
        self.connection_mgr.start()

        # 4. Start hotkeys
        self._setup_hotkeys()
        self.hotkey_mgr.start()

        # 5. Start dashboard (includes tray icon)
        self.dashboard.on_mode_change = self._on_mode_change
        self.dashboard.on_quit = self.stop
        self.dashboard.on_start = self._start_receiver
        self.dashboard.on_stop = self.stop_receiver
        self.dashboard.start()

        # 6. Restore volume
        vol = self.config.get("audio", "volume", default=1.0)
        self.audio_output.set_volume(vol)

        print()
        print(f"[Main] 🎤 {t('connection_mode')}: {self.config.get('connection', 'mode').upper()}")
        print(f"[Main] 🌐 IP: {self.connection_mgr.get_local_ip()}")
        print(f"[Main] 📡 Port: {self.config.get('connection', 'port')}")
        print(f"[Main] {t('waiting_connection')}")
        print()

    def stop(self):
        """Stop all services cleanly."""
        if not self._running:
            return
        self._running = False
        print(f"\n[Main] {t('closing')}")

        self.hotkey_mgr.stop()
        if self.receiver:
            self.receiver.stop()
        self.connection_mgr.stop()
        self.audio_output.stop()
        self.dashboard.stop()

        print(f"[Main] {t('goodbye')} 👋")

    def _start_receiver(self):
        if self.receiver:
            self.receiver.stop()

        mode = self.config.get("connection", "mode")
        port = self.config.get("connection", "port")
        sr = self.config.get("audio", "sample_rate")
        ch = self.config.get("audio", "channels")
        frame_ms = self.config.get("audio", "frame_duration_ms")

        if mode == "usb":
            if self.connection_mgr.setup_adb_forward():
                self.receiver = USBReceiver(
                    self.audio_output, port=port,
                    sample_rate=sr, channels=ch, frame_duration_ms=frame_ms,
                )
            else:
                self.receiver = WiFiReceiver(
                    self.audio_output, port=port,
                    sample_rate=sr, channels=ch, frame_duration_ms=frame_ms,
                )
        else:
            self.receiver = WiFiReceiver(
                self.audio_output, port=port,
                sample_rate=sr, channels=ch, frame_duration_ms=frame_ms,
            )

        self.receiver.start()

        # Restart connection manager so it listens for new connections
        self.connection_mgr.on_connect = self._on_phone_connected
        self.connection_mgr.on_disconnect = self._on_phone_disconnected
        self.connection_mgr.on_volume_change = self._on_volume_changed
        self.connection_mgr.start()

    def stop_receiver(self):
        """Stop the audio receiver (called by the UI Stop button)."""
        # Stop the connection manager completely (closes server socket + disconnects phone)
        self.connection_mgr.stop()
        # Stop the audio receiver
        if self.receiver:
            self.receiver.stop()
            self.receiver = None

    def _setup_hotkeys(self):
        callbacks = {
            "mute_toggle": self._hotkey_mute_toggle,
            "volume_up": self._hotkey_volume_up,
            "volume_down": self._hotkey_volume_down,
        }
        self.hotkey_mgr.load_from_config(callbacks)

        ptt_key = self.config.get("hotkeys", "push_to_talk")
        if ptt_key:
            self.hotkey_mgr.register_push_to_talk(
                ptt_key,
                on_press=lambda: self.audio_output.set_mute(False),
                on_release=lambda: self.audio_output.set_mute(True),
            )

    def _hotkey_mute_toggle(self):
        muted = self.audio_output.toggle_mute()
        self.connection_mgr.send_mute(muted)
        state = "🔇" if muted else "🔊"
        print(f"[Hotkey] {state}")

    def _hotkey_volume_up(self):
        new_vol = min(2.0, self.audio_output.volume + 0.1)
        self.audio_output.set_volume(new_vol)
        self.connection_mgr.send_volume(new_vol)
        self.config.set("audio", "volume", new_vol)

    def _hotkey_volume_down(self):
        new_vol = max(0.0, self.audio_output.volume - 0.1)
        self.audio_output.set_volume(new_vol)
        self.connection_mgr.send_volume(new_vol)
        self.config.set("audio", "volume", new_vol)

    def _on_phone_connected(self, mode: str, addr: str):
        print(f"[Main] 📱 {t('phone_connected')} ({mode}: {addr})")
        self.dashboard.update_connection_status(True, mode, addr)

    def _on_phone_disconnected(self):
        print(f"[Main] 📱 {t('phone_disconnected')}")
        self.dashboard.update_connection_status(False)

    def _on_volume_changed(self, volume: float):
        pass  # Handled by audio_output directly

    def _on_mode_change(self, mode: str):
        self._start_receiver()


def main():
    server = MicProjectServer()

    def signal_handler(sig, frame):
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    server.start()

    try:
        while server._running:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()

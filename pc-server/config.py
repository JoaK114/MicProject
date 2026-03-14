"""
MicProject - Configuration Module
Manages app settings with JSON persistence in %APPDATA%.
"""

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = {
    "connection": {
        "mode": "wifi",          # "wifi" or "usb"
        "port": 4545,            # Audio streaming port (UDP)
        "control_port": 4546,    # Control channel port (TCP)
        "auto_discovery": True,
    },
    "audio": {
        "sample_rate": 48000,
        "channels": 1,
        "frame_duration_ms": 20,    # Opus frame size
        "buffer_size_ms": 60,       # Jitter buffer
        "volume": 1.0,              # 0.0 - 2.0
        "device_name": "CABLE Input",  # VB-Cable device
    },
    "hotkeys": {
        "mute_toggle": "ctrl+m",
        "push_to_talk": "",          # Empty = disabled
        "volume_up": "ctrl+up",
        "volume_down": "ctrl+down",
    },
    "general": {
        "start_minimized": True,
        "auto_connect": True,
        "language": "es",
    },
}


def get_config_dir() -> Path:
    """Get the app config directory in %APPDATA%."""
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    config_dir = Path(appdata) / "MicProject"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get the full path to config.json."""
    return get_config_dir() / "config.json"


class Config:
    """Application configuration manager with auto-save."""

    def __init__(self):
        self._data: dict = {}
        self._path = get_config_path()
        self.load()

    def load(self):
        """Load config from disk, merging with defaults for missing keys."""
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._data = self._deep_merge(DEFAULT_CONFIG, saved)
            except (json.JSONDecodeError, OSError):
                self._data = DEFAULT_CONFIG.copy()
        else:
            self._data = DEFAULT_CONFIG.copy()
            self.save()

    def save(self):
        """Persist current config to disk."""
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"[Config] Error saving config: {e}")

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Get a nested config value.
        Usage: config.get("audio", "volume") -> 1.0
        """
        current = self._data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def set(self, *keys_and_value):
        """
        Set a nested config value and auto-save.
        Usage: config.set("audio", "volume", 0.8)
        """
        if len(keys_and_value) < 2:
            raise ValueError("Need at least one key and a value")

        keys = keys_and_value[:-1]
        value = keys_and_value[-1]

        current = self._data
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
        self.save()

    @property
    def data(self) -> dict:
        """Read-only access to the full config dict."""
        return self._data.copy()

    @staticmethod
    def _deep_merge(defaults: dict, overrides: dict) -> dict:
        """Recursively merge overrides into defaults."""
        result = defaults.copy()
        for key, value in overrides.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = Config._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

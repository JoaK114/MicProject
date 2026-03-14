"""
MicProject - Hotkey Manager
Global keyboard shortcuts for mute, push-to-talk, volume control.
"""

import threading
from pynput import keyboard


# Map human-readable key names to pynput key objects
SPECIAL_KEYS = {
    "ctrl": keyboard.Key.ctrl_l,
    "ctrl_l": keyboard.Key.ctrl_l,
    "ctrl_r": keyboard.Key.ctrl_r,
    "alt": keyboard.Key.alt_l,
    "alt_l": keyboard.Key.alt_l,
    "alt_r": keyboard.Key.alt_r,
    "shift": keyboard.Key.shift_l,
    "shift_l": keyboard.Key.shift_l,
    "shift_r": keyboard.Key.shift_r,
    "up": keyboard.Key.up,
    "down": keyboard.Key.down,
    "left": keyboard.Key.left,
    "right": keyboard.Key.right,
    "space": keyboard.Key.space,
    "tab": keyboard.Key.tab,
    "f1": keyboard.Key.f1,
    "f2": keyboard.Key.f2,
    "f3": keyboard.Key.f3,
    "f4": keyboard.Key.f4,
    "f5": keyboard.Key.f5,
    "f6": keyboard.Key.f6,
    "f7": keyboard.Key.f7,
    "f8": keyboard.Key.f8,
    "f9": keyboard.Key.f9,
    "f10": keyboard.Key.f10,
    "f11": keyboard.Key.f11,
    "f12": keyboard.Key.f12,
}


def parse_hotkey(hotkey_str: str) -> set:
    """
    Parse a hotkey string like 'ctrl+m' into a set of pynput key objects.
    Returns an empty set if the string is empty.
    """
    if not hotkey_str or not hotkey_str.strip():
        return set()

    keys = set()
    for part in hotkey_str.lower().split("+"):
        part = part.strip()
        if part in SPECIAL_KEYS:
            keys.add(SPECIAL_KEYS[part])
        elif len(part) == 1:
            keys.add(keyboard.KeyCode.from_char(part))
        else:
            print(f"[Hotkey] Unknown key: '{part}'")
    return keys


class HotkeyManager:
    """
    Manages global hotkeys using pynput.
    Low overhead: only checks key combos on key events.
    """

    def __init__(self, config):
        self.config = config
        self._listener = None
        self._pressed_keys = set()
        self._lock = threading.Lock()

        # Registered hotkeys: {name: (key_set, callback)}
        self._hotkeys: dict[str, tuple[set, callable]] = {}

        # Push-to-talk state
        self._ptt_active = False
        self._ptt_callback_press = None
        self._ptt_callback_release = None

    def register(self, name: str, hotkey_str: str, callback: callable):
        """Register a hotkey with a callback."""
        keys = parse_hotkey(hotkey_str)
        if keys:
            self._hotkeys[name] = (keys, callback)
            print(f"[Hotkey] Registered: {name} = {hotkey_str}")
        else:
            # Remove if previously registered
            self._hotkeys.pop(name, None)

    def register_push_to_talk(self, hotkey_str: str,
                               on_press: callable, on_release: callable):
        """Register push-to-talk with press/release callbacks."""
        keys = parse_hotkey(hotkey_str)
        if keys:
            self._hotkeys["push_to_talk"] = (keys, None)  # Handled specially
            self._ptt_callback_press = on_press
            self._ptt_callback_release = on_release
            print(f"[Hotkey] Registered PTT: {hotkey_str}")

    def load_from_config(self, callbacks: dict[str, callable]):
        """
        Load hotkeys from config and bind callbacks.
        callbacks: {"mute_toggle": func, "volume_up": func, "volume_down": func}
        """
        hotkey_config = self.config.get("hotkeys") or {}

        for name, cb in callbacks.items():
            hotkey_str = hotkey_config.get(name, "")
            if hotkey_str:
                self.register(name, hotkey_str, cb)

    def start(self):
        """Start the global key listener."""
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()
        print("[Hotkey] Listener started")

    def stop(self):
        """Stop the key listener."""
        if self._listener:
            self._listener.stop()
            self._listener = None
        print("[Hotkey] Listener stopped")

    def _normalize_key(self, key):
        """Normalize a key to a comparable form."""
        if isinstance(key, keyboard.Key):
            # Normalize left/right modifiers
            if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                return keyboard.Key.ctrl_l
            if key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
                return keyboard.Key.alt_l
            if key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
                return keyboard.Key.shift_l
            return key
        elif isinstance(key, keyboard.KeyCode):
            if key.char:
                return keyboard.KeyCode.from_char(key.char.lower())
            return key
        return key

    def _on_press(self, key):
        """Handle key press events."""
        normalized = self._normalize_key(key)
        with self._lock:
            self._pressed_keys.add(normalized)
            self._check_hotkeys(pressed=True)

    def _on_release(self, key):
        """Handle key release events."""
        normalized = self._normalize_key(key)
        with self._lock:
            # Check PTT release before removing the key
            if "push_to_talk" in self._hotkeys and self._ptt_active:
                ptt_keys = self._hotkeys["push_to_talk"][0]
                if normalized in ptt_keys:
                    self._ptt_active = False
                    if self._ptt_callback_release:
                        threading.Thread(
                            target=self._ptt_callback_release, daemon=True
                        ).start()

            self._pressed_keys.discard(normalized)

    def _check_hotkeys(self, pressed: bool = True):
        """Check if any registered hotkey combo is active."""
        for name, (keys, callback) in self._hotkeys.items():
            if keys and keys.issubset(self._pressed_keys):
                if name == "push_to_talk":
                    if not self._ptt_active and pressed:
                        self._ptt_active = True
                        if self._ptt_callback_press:
                            threading.Thread(
                                target=self._ptt_callback_press, daemon=True
                            ).start()
                elif callback and pressed:
                    threading.Thread(target=callback, daemon=True).start()

    @property
    def registered_hotkeys(self) -> dict[str, str]:
        """Get dict of registered hotkey names and their key strings."""
        result = {}
        for name in self._hotkeys:
            hotkey_config = self.config.get("hotkeys") or {}
            result[name] = hotkey_config.get(name, "")
        return result

"""
MicProject - System Tray Application
Lightweight system tray UI with settings window using tkinter.
"""

import threading
import tkinter as tk
from tkinter import ttk
import pystray
from PIL import Image, ImageDraw


def create_tray_icon(connected: bool = False) -> Image.Image:
    """Create a simple tray icon programmatically (no external file needed)."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Microphone body
    color = (76, 175, 80, 255) if connected else (158, 158, 158, 255)  # Green / Gray
    # Mic head (rounded rect approximation)
    draw.rounded_rectangle([20, 8, 44, 36], radius=8, fill=color)
    # Mic stem
    draw.rectangle([29, 36, 35, 48], fill=color)
    # Mic base arc
    draw.arc([14, 24, 50, 50], start=0, end=180, fill=color, width=3)
    # Base
    draw.rectangle([24, 48, 40, 52], fill=color)

    # Connection indicator dot
    if connected:
        draw.ellipse([46, 4, 58, 16], fill=(76, 175, 80, 255))  # Green dot
    else:
        draw.ellipse([46, 4, 58, 16], fill=(244, 67, 54, 255))  # Red dot

    return img


class TrayApp:
    """System tray application with settings window."""

    def __init__(self, config, audio_output, connection_manager, hotkey_manager):
        self.config = config
        self.audio_output = audio_output
        self.connection_mgr = connection_manager
        self.hotkey_mgr = hotkey_manager

        self._tray = None
        self._settings_window = None
        self._tray_thread = None

        # Callbacks
        self.on_mode_change = None  # func(mode: str)
        self.on_quit = None         # func()

    def start(self):
        """Start the system tray icon."""
        icon_image = create_tray_icon(connected=False)

        menu = pystray.Menu(
            pystray.MenuItem(
                "Estado: Desconectado",
                lambda: None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Modo",
                pystray.Menu(
                    pystray.MenuItem(
                        "WiFi",
                        self._set_wifi,
                        checked=lambda item: self.config.get("connection", "mode") == "wifi",
                        radio=True,
                    ),
                    pystray.MenuItem(
                        "USB",
                        self._set_usb,
                        checked=lambda item: self.config.get("connection", "mode") == "usb",
                        radio=True,
                    ),
                ),
            ),
            pystray.MenuItem(
                "Mutear / Desmutear",
                self._toggle_mute,
            ),
            pystray.MenuItem(
                "Configuración",
                self._open_settings,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Salir",
                self._quit,
            ),
        )

        self._tray = pystray.Icon(
            "MicProject",
            icon_image,
            "MicProject - Micrófono Remoto",
            menu,
        )

        self._tray_thread = threading.Thread(target=self._tray.run, daemon=True)
        self._tray_thread.start()
        print("[Tray] System tray icon started")

    def update_connection_status(self, connected: bool, mode: str = "", addr: str = ""):
        """Update the tray icon to reflect connection status."""
        if self._tray:
            self._tray.icon = create_tray_icon(connected)
            if connected:
                self._tray.title = f"MicProject - Conectado ({mode}: {addr})"
            else:
                self._tray.title = "MicProject - Desconectado"

    def stop(self):
        """Stop the tray icon."""
        if self._tray:
            self._tray.stop()

    def _set_wifi(self):
        self.config.set("connection", "mode", "wifi")
        if self.on_mode_change:
            self.on_mode_change("wifi")

    def _set_usb(self):
        self.config.set("connection", "mode", "usb")
        if self.on_mode_change:
            self.on_mode_change("usb")

    def _toggle_mute(self):
        muted = self.audio_output.toggle_mute()
        self.connection_mgr.send_mute(muted)

    def _quit(self):
        if self.on_quit:
            self.on_quit()
        if self._tray:
            self._tray.stop()

    def _open_settings(self):
        """Open the settings window (tkinter, lightweight)."""
        if self._settings_window and self._settings_window.winfo_exists():
            self._settings_window.focus_force()
            return

        threading.Thread(target=self._create_settings_window, daemon=True).start()

    def _create_settings_window(self):
        """Create the settings window using tkinter."""
        root = tk.Tk()
        root.title("MicProject - Configuración")
        root.geometry("450x500")
        root.resizable(False, False)
        root.configure(bg="#1e1e2e")

        self._settings_window = root

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TFrame", background="#1e1e2e")
        style.configure("Dark.TLabel", background="#1e1e2e", foreground="#cdd6f4",
                         font=("Segoe UI", 10))
        style.configure("DarkTitle.TLabel", background="#1e1e2e", foreground="#89b4fa",
                         font=("Segoe UI", 12, "bold"))
        style.configure("Dark.TButton", background="#313244", foreground="#cdd6f4",
                         font=("Segoe UI", 10))
        style.configure("Dark.TEntry", fieldbackground="#313244", foreground="#cdd6f4")

        main_frame = ttk.Frame(root, style="Dark.TFrame", padding=20)
        main_frame.pack(fill="both", expand=True)

        # --- Connection Section ---
        ttk.Label(main_frame, text="🔌 Conexión", style="DarkTitle.TLabel").pack(anchor="w", pady=(0, 5))

        conn_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        conn_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(conn_frame, text="Puerto de audio:", style="Dark.TLabel").grid(row=0, column=0, sticky="w")
        port_var = tk.StringVar(value=str(self.config.get("connection", "port")))
        port_entry = ttk.Entry(conn_frame, textvariable=port_var, width=10, style="Dark.TEntry")
        port_entry.grid(row=0, column=1, padx=10)

        ip_label = ttk.Label(conn_frame, text=f"IP: {self.connection_mgr.get_local_ip()}",
                              style="Dark.TLabel")
        ip_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(5, 0))

        # --- Volume Section ---
        ttk.Label(main_frame, text="🔊 Volumen", style="DarkTitle.TLabel").pack(anchor="w", pady=(0, 5))

        vol_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        vol_frame.pack(fill="x", pady=(0, 15))

        vol_value_label = ttk.Label(vol_frame, text=f"{int(self.audio_output.volume * 100)}%",
                                     style="Dark.TLabel")
        vol_value_label.pack(side="right", padx=10)

        vol_scale = ttk.Scale(
            vol_frame, from_=0, to=200, orient="horizontal",
            value=self.audio_output.volume * 100,
            command=lambda v: self._on_volume_change(float(v), vol_value_label)
        )
        vol_scale.pack(fill="x", expand=True)

        # --- Hotkeys Section ---
        ttk.Label(main_frame, text="⌨️ Teclas Rápidas", style="DarkTitle.TLabel").pack(anchor="w", pady=(0, 5))

        hotkey_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        hotkey_frame.pack(fill="x", pady=(0, 15))

        hotkey_entries = {}
        hotkey_labels = {
            "mute_toggle": "Mutear/Desmutear",
            "push_to_talk": "Push to Talk",
            "volume_up": "Subir Volumen",
            "volume_down": "Bajar Volumen",
        }

        for i, (key, label) in enumerate(hotkey_labels.items()):
            ttk.Label(hotkey_frame, text=f"{label}:", style="Dark.TLabel").grid(
                row=i, column=0, sticky="w", pady=2)
            var = tk.StringVar(value=self.config.get("hotkeys", key) or "")
            entry = ttk.Entry(hotkey_frame, textvariable=var, width=20, style="Dark.TEntry")
            entry.grid(row=i, column=1, padx=10, pady=2)
            hotkey_entries[key] = var

            # Capture button
            btn = ttk.Button(
                hotkey_frame, text="⏺",
                command=lambda e=entry, k=key: self._capture_hotkey(e, k),
                style="Dark.TButton", width=3,
            )
            btn.grid(row=i, column=2, pady=2)

        # --- Save Button ---
        def save_settings():
            # Save port
            try:
                new_port = int(port_var.get())
                self.config.set("connection", "port", new_port)
            except ValueError:
                pass

            # Save hotkeys
            for key, var in hotkey_entries.items():
                self.config.set("hotkeys", key, var.get())

            root.destroy()

        ttk.Button(main_frame, text="💾 Guardar", command=save_settings,
                    style="Dark.TButton").pack(pady=15)

        root.mainloop()

    def _on_volume_change(self, value: float, label: ttk.Label):
        """Handle volume slider change."""
        volume = value / 100.0
        self.audio_output.set_volume(volume)
        self.connection_mgr.send_volume(volume)
        self.config.set("audio", "volume", volume)
        label.config(text=f"{int(value)}%")

    def _capture_hotkey(self, entry_widget, key_name: str):
        """Open a small dialog to capture a key combination."""
        capture_win = tk.Toplevel()
        capture_win.title("Capturar tecla")
        capture_win.geometry("300x100")
        capture_win.configure(bg="#1e1e2e")
        capture_win.grab_set()
        capture_win.focus_force()

        label = tk.Label(capture_win, text="Presiona la combinación de teclas...",
                         bg="#1e1e2e", fg="#cdd6f4", font=("Segoe UI", 11))
        label.pack(expand=True)

        pressed = set()
        result_parts = []

        def on_key(event):
            key = event.keysym.lower()
            modifiers = []
            if event.state & 0x4:
                modifiers.append("ctrl")
            if event.state & 0x8:
                modifiers.append("alt")
            if event.state & 0x1:
                modifiers.append("shift")

            if key not in ("control_l", "control_r", "alt_l", "alt_r",
                           "shift_l", "shift_r"):
                parts = modifiers + [key]
                result = "+".join(parts)
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, result)
                capture_win.destroy()

        capture_win.bind("<KeyPress>", on_key)

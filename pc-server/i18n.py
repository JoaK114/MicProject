"""
MicProject - Internationalization (i18n) System
Supports English and Spanish with first-launch language picker.
"""

import os
import json

# ─── String Tables ────────────────────────────────────────────────────

STRINGS = {
    "es": {
        # General
        "app_name": "MicProject",
        "app_subtitle": "Micrófono Remoto para PC",

        # Language picker
        "lang_title": "Seleccionar Idioma / Select Language",
        "lang_confirm": "Confirmar",

        # Dashboard
        "dashboard": "Dashboard",
        "settings": "Configuración",
        "help": "Ayuda",
        "support": "Apoyar",

        # Connection
        "connection_status": "ESTADO DE CONEXIÓN",
        "connected": "Conectado",
        "disconnected": "Desconectado",
        "connecting": "Conectando...",
        "searching": "Buscando dispositivo en la red...",
        "retry": "Reintentar",
        "connection_mode": "Modo de Conexión",
        "wifi_label": "WiFi (Inalámbrico)",
        "usb_label": "USB (Cable)",
        "direct_label": "IP Directa",

        # Volume
        "volume": "Volumen General",
        "gain": "Ganancia",
        "mute": "MUTEAR",
        "muted": "MUTEADO",
        "unmute": "DESMUTEAR",
        "start": "INICIAR",
        "stop": "DETENER",

        # System Info
        "system_info": "Información del Sistema",
        "latency": "LATENCIA",
        "bitrate": "BITRATE",
        "frequency": "FRECUENCIA",
        "channels": "CANALES",
        "mono": "Mono",
        "stereo": "Estéreo",

        # Input Monitor
        "input_monitor": "Monitor de Entrada",
        "realtime_vu": "TIEMPO REAL / VU METER",

        # Settings
        "audio_port": "Puerto de audio:",
        "local_ip": "IP Local:",
        "hotkeys_title": "Teclas Rápidas",
        "mute_toggle": "Mutear/Desmutear",
        "push_to_talk": "Push to Talk",
        "volume_up": "Subir Volumen",
        "volume_down": "Bajar Volumen",
        "save": "Guardar",
        "capture_key": "Presiona la combinación de teclas...",

        # Status
        "server_running": "Servidor activo",
        "waiting_connection": "Esperando conexión del celular...",
        "waiting_signal": "Buscando señal...",
        "server_stopped": "Servidor detenido.",
        "phone_connected": "Celular conectado",
        "phone_disconnected": "Celular desconectado",
        "closing": "Cerrando MicProject...",
        "goodbye": "¡Hasta luego!",

        # Settings extras
        "language": "Idioma",
        "lang_restart_note": "Los cambios de idioma se aplican al guardar.",

        # Errors
        "audio_error": "No se pudo iniciar la salida de audio.",
        "vb_cable_missing": "¿Está instalado VB-Cable?",

        # Tray
        "tray_status_disconnected": "Estado: Desconectado",
        "tray_status_connected": "Estado: Conectado",
        "tray_mode": "Modo",
        "tray_mute_toggle": "Mutear / Desmutear",
        "tray_settings": "Configuración",
        "tray_quit": "Salir",
        "tray_title_disconnected": "MicProject - Desconectado",
        "tray_title_connected": "MicProject - Conectado ({mode}: {addr})",
    },
    "en": {
        # General
        "app_name": "MicProject",
        "app_subtitle": "Remote Microphone for PC",

        # Language picker
        "lang_title": "Select Language / Seleccionar Idioma",
        "lang_confirm": "Confirm",

        # Dashboard
        "dashboard": "Dashboard",
        "settings": "Settings",
        "help": "Help",
        "support": "Support",

        # Connection
        "connection_status": "CONNECTION STATUS",
        "connected": "Connected",
        "disconnected": "Disconnected",
        "connecting": "Connecting...",
        "searching": "Searching for device on the network...",
        "retry": "Retry",
        "connection_mode": "Connection Mode",
        "wifi_label": "WiFi (Wireless)",
        "usb_label": "USB (Cable)",
        "direct_label": "Direct IP",

        # Volume
        "volume": "Master Volume",
        "gain": "Gain",
        "mute": "MUTE",
        "muted": "MUTED",
        "unmute": "UNMUTE",
        "start": "START",
        "stop": "STOP",

        # System Info
        "system_info": "System Information",
        "latency": "LATENCY",
        "bitrate": "BITRATE",
        "frequency": "FREQUENCY",
        "channels": "CHANNELS",
        "mono": "Mono",
        "stereo": "Stereo",

        # Input Monitor
        "input_monitor": "Input Monitor",
        "realtime_vu": "REAL TIME / VU METER",

        # Settings
        "audio_port": "Audio port:",
        "local_ip": "Local IP:",
        "hotkeys_title": "Hotkeys",
        "mute_toggle": "Mute/Unmute",
        "push_to_talk": "Push to Talk",
        "volume_up": "Volume Up",
        "volume_down": "Volume Down",
        "save": "Save",
        "capture_key": "Press a key combination...",

        # Status
        "server_running": "Server active",
        "waiting_connection": "Waiting for phone connection...",
        "waiting_signal": "Searching for signal...",
        "server_stopped": "Server stopped.",
        "phone_connected": "Phone connected",
        "phone_disconnected": "Phone disconnected",
        "closing": "Closing MicProject...",
        "goodbye": "Goodbye!",

        # Settings extras
        "language": "Language",
        "lang_restart_note": "Language changes apply when you save.",

        # Errors
        "audio_error": "Could not start audio output.",
        "vb_cable_missing": "Is VB-Cable installed?",

        # Tray
        "tray_status_disconnected": "Status: Disconnected",
        "tray_status_connected": "Status: Connected",
        "tray_mode": "Mode",
        "tray_mute_toggle": "Mute / Unmute",
        "tray_settings": "Settings",
        "tray_quit": "Quit",
        "tray_title_disconnected": "MicProject - Disconnected",
        "tray_title_connected": "MicProject - Connected ({mode}: {addr})",
    },
}

# ─── i18n Manager ─────────────────────────────────────────────────────

_current_lang = "es"
_config_path = None


def _get_config_path() -> str:
    """Get the path for storing language preference."""
    global _config_path
    if _config_path:
        return _config_path
    app_data = os.path.join(os.path.expanduser("~"), ".micproject")
    os.makedirs(app_data, exist_ok=True)
    _config_path = os.path.join(app_data, "lang.json")
    return _config_path


def load_language() -> str:
    """Load saved language preference. Returns '' if not set yet."""
    global _current_lang
    path = _get_config_path()
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
                _current_lang = data.get("lang", "es")
                return _current_lang
        except Exception:
            pass
    return ""


def save_language(lang: str):
    """Save language preference."""
    global _current_lang
    _current_lang = lang
    path = _get_config_path()
    with open(path, "w") as f:
        json.dump({"lang": lang}, f)


def t(key: str, **kwargs) -> str:
    """Get a translated string by key."""
    text = STRINGS.get(_current_lang, STRINGS["es"]).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text


def get_lang() -> str:
    """Get current language code."""
    return _current_lang


def set_language(lang: str):
    """Change the language at runtime (for Settings dialog)."""
    global _current_lang
    _current_lang = lang


def show_language_picker() -> str:
    """Show a tkinter dialog for language selection. Returns 'es' or 'en'."""
    import tkinter as tk

    selected = {"lang": "es"}

    root = tk.Tk()
    root.title("MicProject")
    root.geometry("400x280")
    root.resizable(False, False)
    root.configure(bg="#0A0A14")

    # Center on screen
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - 200
    y = (root.winfo_screenheight() // 2) - 140
    root.geometry(f"+{x}+{y}")

    # Title
    tk.Label(
        root, text="🎤 MicProject",
        bg="#0A0A14", fg="#F0F0F5",
        font=("Segoe UI", 18, "bold"),
    ).pack(pady=(25, 5))

    tk.Label(
        root, text="Select Language / Seleccionar Idioma",
        bg="#0A0A14", fg="#7A7A95",
        font=("Segoe UI", 10),
    ).pack(pady=(0, 20))

    btn_frame = tk.Frame(root, bg="#0A0A14")
    btn_frame.pack(pady=5)

    lang_var = tk.StringVar(value="es")

    def make_btn(text, lang_code, col):
        btn = tk.Radiobutton(
            btn_frame, text=text, variable=lang_var, value=lang_code,
            bg="#14142A", fg="#F0F0F5", selectcolor="#7C6FFF",
            activebackground="#1E1E3A", activeforeground="#F0F0F5",
            font=("Segoe UI", 12), indicatoron=0,
            width=14, height=2, borderwidth=0, relief="flat",
            cursor="hand2",
        )
        btn.grid(row=0, column=col, padx=8)

    make_btn("🇪🇸  Español", "es", 0)
    make_btn("🇺🇸  English", "en", 1)

    def confirm():
        selected["lang"] = lang_var.get()
        root.destroy()

    confirm_btn = tk.Button(
        root, text="Confirmar / Confirm",
        bg="#7C6FFF", fg="white",
        activebackground="#9B8FFF", activeforeground="white",
        font=("Segoe UI", 11, "bold"),
        borderwidth=0, padx=30, pady=8, cursor="hand2",
        command=confirm,
    )
    confirm_btn.pack(pady=20)

    root.mainloop()
    return selected["lang"]

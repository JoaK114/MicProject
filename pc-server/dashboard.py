"""
MicProject - Dashboard GUI
Full tkinter dashboard with sidebar navigation, matching the dark purple/green theme.
"""

import tkinter as tk
from tkinter import ttk, font as tkfont
import threading
import webbrowser
import time

import pystray
from PIL import Image, ImageDraw

from i18n import t
from version import APP_VERSION

# ─── Color Palette ────────────────────────────────────────────────────

BG_DARK     = "#0A0A14"
BG_SIDEBAR  = "#0E0E1C"
BG_CARD     = "#14142A"
BG_CARD_LT  = "#1E1E3A"
ACCENT      = "#7C6FFF"
ACCENT_LT   = "#9B8FFF"
GREEN       = "#00E676"
GREEN_DK    = "#00C853"
RED         = "#FF5252"
ORANGE      = "#FFAB40"
TEXT_PRI    = "#F0F0F5"
TEXT_SEC    = "#7A7A95"
TEXT_DIM    = "#50506A"

# Patreon placeholder URL
PATREON_URL = "https://patreon.com/MicProject"


# ─── Tray Icon ────────────────────────────────────────────────────────

def create_tray_icon(connected: bool = False) -> Image.Image:
    """Create the tray icon. Uses custom icon.png if available."""
    import os, sys
    # PyInstaller bundles data to sys._MEIPASS
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    icon_path = os.path.join(base_dir, "assets", "icon.png")
    try:
        if os.path.exists(icon_path):
            img = Image.open(icon_path).convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
            # Add a small status dot overlay
            draw = ImageDraw.Draw(img)
            if connected:
                draw.ellipse([46, 4, 58, 16], fill=(0, 230, 118, 255))
            else:
                draw.ellipse([46, 4, 58, 16], fill=(255, 82, 82, 255))
            return img
    except Exception:
        pass

    # Fallback: draw programmatically
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (0, 230, 118, 255) if connected else (158, 158, 158, 255)
    draw.rounded_rectangle([20, 8, 44, 36], radius=8, fill=color)
    draw.rectangle([29, 36, 35, 48], fill=color)
    draw.arc([14, 24, 50, 50], start=0, end=180, fill=color, width=3)
    draw.rectangle([24, 48, 40, 52], fill=color)
    if connected:
        draw.ellipse([46, 4, 58, 16], fill=(0, 230, 118, 255))
    else:
        draw.ellipse([46, 4, 58, 16], fill=(255, 82, 82, 255))
    return img


# ─── Dashboard App ────────────────────────────────────────────────────

class DashboardApp:
    """Full dashboard GUI with system tray integration."""

    def __init__(self, config, audio_output, connection_manager, hotkey_manager):
        self.config = config
        self.audio_output = audio_output
        self.connection_mgr = connection_manager
        self.hotkey_mgr = hotkey_manager

        self._root = None
        self._tray = None
        self._tray_thread = None
        self._running = False
        self._connected = False
        self._server_running = True  # Starts true initially
        self._connection_mode = ""
        self._client_addr = ""

        # UI element references for live updates
        self._status_dot = None
        self._status_label = None
        self._status_detail = None
        self._vol_label = None
        self._vol_scale = None
        self._mute_btn = None
        self._start_btn = None
        self._vu_bars = []
        self._mode_toggles = []

        # Callbacks
        self.on_mode_change = None
        self.on_quit = None
        self.on_start = None
        self.on_stop = None

    # ─── Start / Stop ─────────────────────────────────────────────

    def start(self):
        """Start the dashboard and tray icon."""
        self._running = True
        self._start_tray()
        threading.Thread(target=self._create_dashboard, daemon=True).start()

    def stop(self):
        """Stop everything."""
        self._running = False
        if self._tray:
            try:
                self._tray.stop()
            except Exception:
                pass
        if self._root:
            try:
                self._root.quit()
            except Exception:
                pass

    def update_connection_status(self, connected: bool, mode: str = "", addr: str = ""):
        """Update status from main thread."""
        self._connected = connected
        self._connection_mode = mode
        self._client_addr = addr

        # If phone connected, server must be running
        if connected:
            self._server_running = True

        # Update tray
        if self._tray:
            self._tray.icon = create_tray_icon(connected)
            if connected:
                self._tray.title = t("tray_title_connected", mode=mode, addr=addr)
            else:
                self._tray.title = t("tray_title_disconnected")

        # Update dashboard (thread-safe)
        if self._root:
            self._root.after(0, self._refresh_status_ui)

    # ─── System Tray ──────────────────────────────────────────────

    def _start_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem(t("tray_status_disconnected"), lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("tray_mute_toggle"), self._toggle_mute),
            pystray.MenuItem(t("tray_settings"), self._show_window),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("tray_quit"), self._quit),
        )
        self._tray = pystray.Icon("MicProject", create_tray_icon(False),
                                   "MicProject", menu)
        self._tray_thread = threading.Thread(target=self._tray.run, daemon=True)
        self._tray_thread.start()

    def _show_window(self):
        if self._root:
            self._root.after(0, lambda: (self._root.deiconify(), self._root.focus_force()))

    def _toggle_mute(self):
        muted = self.audio_output.toggle_mute()
        self.connection_mgr.send_mute(muted)

    def _quit(self):
        if self.on_quit:
            self.on_quit()
        self.stop()

    def _check_updates(self):
        """Check for app updates."""
        if self._root:
            from updater import check_and_prompt
            check_and_prompt(self._root)

    # ─── Dashboard Window ─────────────────────────────────────────

    def _create_dashboard(self):
        self._root = tk.Tk()
        self._root.title("MicProject")
        self._root.geometry("960x620")
        self._root.minsize(800, 550)
        self._root.configure(bg=BG_DARK)

        # Center on screen
        self._root.update_idletasks()
        x = (self._root.winfo_screenwidth() // 2) - 480
        y = (self._root.winfo_screenheight() // 2) - 310
        self._root.geometry(f"+{x}+{y}")

        # Set window icon
        try:
            import os, sys
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(base_dir, "assets", "icon.ico")
            if os.path.exists(icon_path):
                self._root.iconbitmap(icon_path)
        except Exception:
            pass

        # Handle close button → minimize to tray
        self._root.protocol("WM_DELETE_WINDOW", self._root.withdraw)

        # Build layout
        self._build_sidebar()
        self._build_main_area()

        # Start VU meter refresh
        self._vu_update_loop()

        self._root.mainloop()

    # ─── Sidebar ──────────────────────────────────────────────────

    def _build_sidebar(self):
        sidebar = tk.Frame(self._root, bg=BG_SIDEBAR, width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Logo
        logo_frame = tk.Frame(sidebar, bg=BG_SIDEBAR)
        logo_frame.pack(fill="x", pady=(20, 30), padx=16)

        tk.Label(logo_frame, text="🎤", bg=BG_SIDEBAR, fg=ACCENT,
                 font=("Segoe UI", 22)).pack(side="left")
        tk.Label(logo_frame, text="MicProject", bg=BG_SIDEBAR, fg=TEXT_PRI,
                 font=("Segoe UI", 15, "bold")).pack(side="left", padx=(8, 0))

        # Nav buttons
        self._sidebar_btn(sidebar, "⊞", t("dashboard"), active=True)
        self._sidebar_btn(sidebar, "⚙", t("settings"), command=self._open_settings)
        self._sidebar_btn(sidebar, "🔄", "Updates", command=self._check_updates)
        self._sidebar_btn(sidebar, "?", t("help"))

        # Spacer
        tk.Frame(sidebar, bg=BG_SIDEBAR).pack(fill="both", expand=True)

        # Support / Patreon button
        support_frame = tk.Frame(sidebar, bg=BG_SIDEBAR)
        support_frame.pack(fill="x", padx=16, pady=(0, 10))

        support_btn = tk.Button(
            support_frame, text=f"❤  {t('support')}",
            bg=ACCENT, fg="white", activebackground=ACCENT_LT, activeforeground="white",
            font=("Segoe UI", 10, "bold"), borderwidth=0,
            padx=10, pady=8, cursor="hand2",
            command=lambda: webbrowser.open(PATREON_URL),
        )
        support_btn.pack(fill="x")

        # User info at bottom
        user_frame = tk.Frame(sidebar, bg=BG_SIDEBAR)
        user_frame.pack(fill="x", padx=16, pady=(0, 16))

        tk.Label(user_frame, text=f"🌐 {self.connection_mgr.get_local_ip()}",
                 bg=BG_SIDEBAR, fg=TEXT_SEC,
                 font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(user_frame, text=f"v{APP_VERSION}",
                 bg=BG_SIDEBAR, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(2, 0))

    def _sidebar_btn(self, parent, icon, text, active=False, command=None):
        bg = ACCENT if active else BG_SIDEBAR
        fg = "white" if active else TEXT_SEC

        btn = tk.Button(
            parent, text=f"  {icon}  {text}",
            bg=bg, fg=fg, activebackground=ACCENT_LT if active else BG_CARD,
            activeforeground="white",
            font=("Segoe UI", 10), borderwidth=0, anchor="w",
            padx=16, pady=10, cursor="hand2",
            command=command or (lambda: None),
        )
        btn.pack(fill="x", padx=8, pady=2)

    # ─── Main Area ────────────────────────────────────────────────

    def _build_main_area(self):
        main = tk.Frame(self._root, bg=BG_DARK)
        main.pack(side="left", fill="both", expand=True, padx=16, pady=16)

        # Top row: Status + Input Monitor
        top_row = tk.Frame(main, bg=BG_DARK)
        top_row.pack(fill="x", pady=(0, 12))

        self._build_status_card(top_row)
        self._build_input_monitor(top_row)

        # Middle row: Connection Mode + Volume
        mid_row = tk.Frame(main, bg=BG_DARK)
        mid_row.pack(fill="x", pady=(0, 12))

        self._build_connection_mode(mid_row)
        self._build_volume_card(mid_row)

        # Bottom row: System Info
        self._build_system_info(main)

    # ─── Status Card ──────────────────────────────────────────────

    def _build_status_card(self, parent):
        card = tk.Frame(parent, bg=BG_CARD, padx=20, pady=16)
        card.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # Header
        tk.Label(card, text=t("connection_status"), bg=BG_CARD, fg=TEXT_SEC,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")

        # Status row
        status_row = tk.Frame(card, bg=BG_CARD)
        status_row.pack(fill="x", pady=(8, 4))

        self._status_dot = tk.Canvas(status_row, width=14, height=14,
                                      bg=BG_CARD, highlightthickness=0)
        self._status_dot.pack(side="left")

        # Render correct initial state based on current flags
        if self._connected:
            dot_color = GREEN
            label_text = t("connected")
            detail_text = f"{self._connection_mode.upper()}: {self._client_addr}"
        elif self._server_running:
            dot_color = ORANGE
            label_text = t("searching")
            detail_text = t("waiting_signal")
        else:
            dot_color = RED
            label_text = t("disconnected")
            detail_text = t("server_stopped")

        self._status_dot.create_oval(2, 2, 12, 12, fill=dot_color, outline="")

        self._status_label = tk.Label(status_row, text=label_text,
                                       bg=BG_CARD, fg=TEXT_PRI,
                                       font=("Segoe UI", 16, "bold"))
        self._status_label.pack(side="left", padx=(8, 0))

        self._status_detail = tk.Label(card, text=detail_text,
                                        bg=BG_CARD, fg=TEXT_SEC,
                                        font=("Segoe UI", 9))
        self._status_detail.pack(anchor="w", pady=(2, 0))

    # ─── Input Monitor ────────────────────────────────────────────

    def _build_input_monitor(self, parent):
        card = tk.Frame(parent, bg=BG_CARD, padx=24, pady=20)
        card.pack(side="left", fill="both", expand=True, padx=(8, 0))

        tk.Label(card, text=f"📊  {t('input_monitor')}", bg=BG_CARD, fg=TEXT_PRI,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")

        # VU bars
        vu_frame = tk.Frame(card, bg=BG_CARD)
        vu_frame.pack(fill="x", pady=(10, 4))

        self._vu_bars = []
        for i in range(12):
            bar = tk.Canvas(vu_frame, width=18, height=60, bg=BG_CARD, highlightthickness=0)
            bar.pack(side="left", padx=2)
            self._vu_bars.append(bar)

        tk.Label(card, text=t("realtime_vu"), bg=BG_CARD, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(anchor="w")

        # Mute + Start buttons
        btn_frame = tk.Frame(card, bg=BG_CARD)
        btn_frame.pack(fill="x", pady=(15, 0))

        self._mute_btn = tk.Button(
            btn_frame, text=f"🔇  {t('mute')}",
            bg=BG_CARD_LT, fg=TEXT_PRI, activebackground=RED, activeforeground="white",
            font=("Segoe UI", 10, "bold"), borderwidth=0,
            padx=16, pady=10, cursor="hand2",
            command=self._toggle_mute,
        )
        self._mute_btn.pack(side="left", padx=(0, 10))

        # Dynamic Start/Stop button
        btn_bg = RED if self._server_running else GREEN
        btn_fg = "white"
        btn_text = f"⏹  {t('stop')}" if self._server_running else f"▶  {t('start')}"
        
        self._start_btn = tk.Button(
            btn_frame, text=btn_text,
            bg=btn_bg, fg=btn_fg, activebackground=btn_bg, activeforeground="white",
            font=("Segoe UI", 10, "bold"), borderwidth=0,
            padx=24, pady=10, cursor="hand2",
            command=self._toggle_server,
        )
        self._start_btn.pack(side="left")

    def _toggle_server(self):
        """Toggle server listening state."""
        if self._server_running:
            self._server_running = False
            self._connected = False
            if self.on_stop:
                self.on_stop()
        else:
            self._server_running = True
            if self.on_start:
                self.on_start()
        
        # Refresh status + button in-place (no rebuild)
        self._refresh_status_ui()
        self._sync_button_state()
        self._sync_mode_lock()

    # ─── Connection Mode ──────────────────────────────────────────

    def _build_connection_mode(self, parent):
        card = tk.Frame(parent, bg=BG_CARD, padx=20, pady=16)
        card.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(card, text=f"🔗  {t('connection_mode')}", bg=BG_CARD, fg=TEXT_PRI,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 12))

        mode = self.config.get("connection", "mode")
        self._mode_var = tk.StringVar(value=mode)
        self._mode_toggles = []  # Reset for rebuild

        modes = [
            ("📶", t("wifi_label"), "wifi"),
            ("🔌", t("usb_label"), "usb"),
            ("🌐", t("direct_label"), "direct"),
        ]

        for icon, label, value in modes:
            row = tk.Frame(card, bg=BG_CARD)
            row.pack(fill="x", pady=3)

            tk.Label(row, text=f"  {icon}  {label}", bg=BG_CARD, fg=TEXT_PRI,
                     font=("Segoe UI", 10)).pack(side="left")

            is_on = mode == value
            
            # Disable toggles if server is running or connected
            is_disabled = self._server_running or self._connected
            btn_state = "disabled" if is_disabled else "normal"
            
            toggle = tk.Button(
                row, text="  ON " if is_on else " OFF ",
                bg=ACCENT if is_on else BG_CARD_LT,
                fg="white" if is_on else TEXT_SEC,
                font=("Segoe UI", 9, "bold"), borderwidth=0,
                padx=8, pady=2, cursor="hand2" if not is_disabled else "arrow",
                command=lambda v=value: self._set_mode(v),
                state=btn_state,
            )
            toggle.pack(side="right")
            self._mode_toggles.append(toggle)
            
        if self._server_running or self._connected:
            tk.Label(card, text="🔌 Detén el servidor para cambiar", bg=BG_CARD, fg=TEXT_SEC, 
                     font=("Segoe UI", 8, "italic")).pack(anchor="w", pady=(10, 0))

    def _set_mode(self, mode):
        self.config.set("connection", "mode", mode)
        self._mode_var.set(mode)
        if self.on_mode_change:
            self.on_mode_change(mode)
        # Rebuild to update toggle states
        if self._root:
            self._root.after(100, self._rebuild_main)

    def _rebuild_main(self):
        """Refresh the main area."""
        for widget in self._root.winfo_children():
            if widget.cget("bg") == BG_DARK:
                widget.destroy()
        self._build_main_area()

    # ─── Volume Card ──────────────────────────────────────────────

    def _build_volume_card(self, parent):
        card = tk.Frame(parent, bg=BG_CARD, padx=20, pady=16)
        card.pack(side="left", fill="both", expand=True, padx=(8, 0))

        tk.Label(card, text=f"🔊  {t('volume')}", bg=BG_CARD, fg=TEXT_PRI,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")

        # Big volume number
        vol_pct = int(self.audio_output.volume * 100)
        self._vol_label = tk.Label(card, text=f"{vol_pct}%",
                                    bg=BG_CARD, fg=ACCENT,
                                    font=("Segoe UI", 32, "bold"))
        self._vol_label.pack(anchor="w", pady=(8, 0))

        # Gain label
        gain_db = round(20 * (self.audio_output.volume if self.audio_output.volume > 0 else 0.001).__class__(self.audio_output.volume), 1) if self.audio_output.volume > 0 else -60
        try:
            import math
            gain_db = round(20 * math.log10(max(self.audio_output.volume, 0.001)), 1)
        except Exception:
            gain_db = 0
        sign = "+" if gain_db >= 0 else ""
        tk.Label(card, text=f"{t('gain')}: {sign}{gain_db}dB",
                 bg=BG_CARD, fg=TEXT_SEC, font=("Segoe UI", 9)).pack(anchor="e")

        # Volume slider
        slider_frame = tk.Frame(card, bg=BG_CARD)
        slider_frame.pack(fill="x", pady=(8, 4))

        self._vol_scale = ttk.Scale(
            slider_frame, from_=0, to=200, orient="horizontal",
            value=self.audio_output.volume * 100,
            command=self._on_volume_change,
        )
        self._vol_scale.pack(fill="x")

        # Scale labels
        lbl_frame = tk.Frame(card, bg=BG_CARD)
        lbl_frame.pack(fill="x")
        tk.Label(lbl_frame, text="0%", bg=BG_CARD, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(side="left")
        tk.Label(lbl_frame, text="50%", bg=BG_CARD, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(side="left", expand=True)
        tk.Label(lbl_frame, text="100%", bg=BG_CARD, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(side="right")

    def _on_volume_change(self, value):
        vol = float(value) / 100.0
        self.audio_output.set_volume(vol)
        self.connection_mgr.send_volume(vol)
        self.config.set("audio", "volume", vol)
        if self._vol_label:
            self._vol_label.config(text=f"{int(float(value))}%")

    # ─── System Info ──────────────────────────────────────────────

    def _build_system_info(self, parent):
        card = tk.Frame(parent, bg=BG_CARD, padx=20, pady=16)
        card.pack(fill="x")

        tk.Label(card, text=t("system_info"), bg=BG_CARD, fg=TEXT_PRI,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 12))

        stats_frame = tk.Frame(card, bg=BG_CARD)
        stats_frame.pack(fill="x")

        # Gather real system info
        import platform
        os_name = f"{platform.system()} {platform.release()}"

        # CPU
        try:
            cpu = platform.processor()
            if not cpu or len(cpu) < 4:
                import subprocess
                r = subprocess.run(
                    ['wmic', 'cpu', 'get', 'name'],
                    capture_output=True, text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                lines = [l.strip() for l in r.stdout.strip().split('\n') if l.strip() and l.strip() != 'Name']
                cpu = lines[0] if lines else platform.processor()
        except Exception:
            cpu = platform.processor()
        # Shorten CPU name
        for rem in ['(R)', '(TM)', 'CPU ', '@ ', '  ']:
            cpu = cpu.replace(rem, '')
        if len(cpu) > 22:
            cpu = cpu[:20] + '…'

        # RAM
        try:
            import psutil
            ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)
            ram = f"{ram_gb} GB"
        except ImportError:
            ram = "N/A"

        # Audio device
        try:
            import sounddevice as sd
            default_out = sd.query_devices(kind='output')
            audio_dev = default_out['name']
            if len(audio_dev) > 22:
                audio_dev = audio_dev[:20] + '…'
        except Exception:
            audio_dev = "Default"

        info = [
            ("OS", os_name),
            ("CPU", cpu),
            ("RAM", ram),
            (t("audio_port").replace(':', ''), audio_dev),
        ]

        for label, value in info:
            box = tk.Frame(stats_frame, bg=BG_CARD_LT, padx=16, pady=10)
            box.pack(side="left", fill="both", expand=True, padx=(0, 8))

            tk.Label(box, text=label, bg=BG_CARD_LT, fg=TEXT_SEC,
                     font=("Segoe UI", 8, "bold")).pack(anchor="w")
            tk.Label(box, text=value, bg=BG_CARD_LT, fg=TEXT_PRI,
                     font=("Segoe UI", 11, "bold")).pack(anchor="w")

    # ─── VU Meter Animation ───────────────────────────────────────

    def _vu_update_loop(self):
        if not self._running or not self._root:
            return

        import random
        import math

        # Read real audio level from the audio output module
        level = getattr(self.audio_output, 'current_level', 0.0)

        # Apply perceptual curve so quiet sounds still show some bars
        boosted = math.pow(level, 0.4) if level > 0.001 else 0
        target_h = int(boosted * 55)  # max bar height = 55px

        for i, bar in enumerate(self._vu_bars):
            bar.delete("all")

            # Add slight random variation per bar for a spectrum-like look
            variation = random.randint(0, max(1, int(target_h * 0.25)))
            h = max(2, target_h - variation)

            y_top = 60 - h
            if h > 45:
                color = RED
            elif h > 30:
                color = ORANGE
            else:
                color = ACCENT
            bar.create_rectangle(2, y_top, 16, 60, fill=color, outline="")

        self._root.after(80, self._vu_update_loop)

    # ─── Live UI Refresh ──────────────────────────────────────────

    def _refresh_status_ui(self):
        if self._connected:
            if self._status_dot:
                self._status_dot.delete("all")
                self._status_dot.create_oval(2, 2, 12, 12, fill=GREEN, outline="")
            if self._status_label:
                self._status_label.config(text=t("connected"))
            if self._status_detail:
                self._status_detail.config(
                    text=f"{self._connection_mode.upper()}: {self._client_addr}")
        elif self._server_running:
            if self._status_dot:
                self._status_dot.delete("all")
                self._status_dot.create_oval(2, 2, 12, 12, fill=ORANGE, outline="")
            if self._status_label:
                self._status_label.config(text=t("searching"))
            if self._status_detail:
                self._status_detail.config(text=t("waiting_signal"))
        else:
            if self._status_dot:
                self._status_dot.delete("all")
                self._status_dot.create_oval(2, 2, 12, 12, fill=RED, outline="")
            if self._status_label:
                self._status_label.config(text=t("disconnected"))
            if self._status_detail:
                self._status_detail.config(text=t("server_stopped"))

        # Always keep button and mode toggles in sync
        self._sync_button_state()
        self._sync_mode_lock()

    def _sync_button_state(self):
        """Keep Start/Stop button visually in sync with actual state."""
        if not self._start_btn:
            return
        try:
            if self._server_running:
                self._start_btn.config(
                    text=f"⏹  {t('stop')}",
                    bg=RED, activebackground=RED,
                )
            else:
                self._start_btn.config(
                    text=f"▶  {t('start')}",
                    bg=GREEN, activebackground=GREEN,
                )
        except Exception:
            pass

    def _sync_mode_lock(self):
        """Enable/disable mode toggles based on server state."""
        if not hasattr(self, '_mode_toggles'):
            return
        locked = self._server_running or self._connected
        for toggle in self._mode_toggles:
            try:
                toggle.config(state="disabled" if locked else "normal")
            except Exception:
                pass

    # ─── Settings Dialog ──────────────────────────────────────────

    def _open_settings(self):
        win = tk.Toplevel(self._root)
        win.title(f"MicProject - {t('settings')}")
        win.geometry("450x560")
        win.resizable(False, False)
        win.configure(bg=BG_DARK)
        win.grab_set()

        # Center
        win.update_idletasks()
        x = (win.winfo_screenwidth() // 2) - 225
        y = (win.winfo_screenheight() // 2) - 280
        win.geometry(f"+{x}+{y}")

        main = tk.Frame(win, bg=BG_DARK, padx=20, pady=20)
        main.pack(fill="both", expand=True)

        # ── Language ──
        tk.Label(main, text=f"🌐 {t('language')}", bg=BG_DARK, fg=ACCENT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 5))

        lang_frame = tk.Frame(main, bg=BG_DARK)
        lang_frame.pack(fill="x", pady=(0, 15))

        from i18n import load_language, save_language, set_language
        current_lang = load_language() or "es"
        lang_var = tk.StringVar(value=current_lang)

        for lang_code, lang_name, flag in [("es", "Español", "🇪🇸"), ("en", "English", "🇺🇸")]:
            tk.Radiobutton(
                lang_frame, text=f"  {flag}  {lang_name}",
                variable=lang_var, value=lang_code,
                bg=BG_DARK, fg=TEXT_PRI, selectcolor=BG_CARD,
                activebackground=BG_DARK, activeforeground=TEXT_PRI,
                font=("Segoe UI", 10),
            ).pack(anchor="w", pady=2)

        tk.Label(lang_frame, text=t("lang_restart_note"),
                 bg=BG_DARK, fg=TEXT_DIM,
                 font=("Segoe UI", 8, "italic")).pack(anchor="w", pady=(4, 0))

        # ── Connection ──
        tk.Label(main, text=f"🔌 {t('connection_mode')}", bg=BG_DARK, fg=ACCENT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 5))

        conn_frame = tk.Frame(main, bg=BG_DARK)
        conn_frame.pack(fill="x", pady=(0, 15))

        tk.Label(conn_frame, text=t("audio_port"), bg=BG_DARK, fg=TEXT_PRI,
                 font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
        port_var = tk.StringVar(value=str(self.config.get("connection", "port")))
        port_entry = tk.Entry(conn_frame, textvariable=port_var, width=10,
                               bg=BG_CARD, fg=TEXT_PRI, insertbackground=TEXT_PRI,
                               borderwidth=0, font=("Segoe UI", 10))
        port_entry.grid(row=0, column=1, padx=10)

        ip = self.connection_mgr.get_local_ip()
        tk.Label(conn_frame, text=f"{t('local_ip')} {ip}",
                 bg=BG_DARK, fg=TEXT_SEC, font=("Segoe UI", 9)).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(5, 0))

        # ── Hotkeys ──
        tk.Label(main, text=f"⌨️ {t('hotkeys_title')}", bg=BG_DARK, fg=ACCENT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 5))

        hk_frame = tk.Frame(main, bg=BG_DARK)
        hk_frame.pack(fill="x", pady=(0, 15))

        hotkey_entries = {}
        hotkey_labels = {
            "mute_toggle": t("mute_toggle"),
            "push_to_talk": t("push_to_talk"),
            "volume_up": t("volume_up"),
            "volume_down": t("volume_down"),
        }

        for i, (key, label) in enumerate(hotkey_labels.items()):
            tk.Label(hk_frame, text=f"{label}:", bg=BG_DARK, fg=TEXT_PRI,
                     font=("Segoe UI", 10)).grid(row=i, column=0, sticky="w", pady=2)
            var = tk.StringVar(value=self.config.get("hotkeys", key) or "")
            entry = tk.Entry(hk_frame, textvariable=var, width=18,
                              bg=BG_CARD, fg=TEXT_PRI, insertbackground=TEXT_PRI,
                              borderwidth=0, font=("Segoe UI", 10))
            entry.grid(row=i, column=1, padx=10, pady=2)
            hotkey_entries[key] = var

            cap_btn = tk.Button(
                hk_frame, text="⏺",
                bg=BG_CARD_LT, fg=TEXT_SEC,
                font=("Segoe UI", 10), borderwidth=0, cursor="hand2",
                command=lambda e=entry: self._capture_hotkey(e, win),
            )
            cap_btn.grid(row=i, column=2, pady=2)

        # Save
        def save():
            # Save language
            new_lang = lang_var.get()
            if new_lang != current_lang:
                save_language(new_lang)
                set_language(new_lang)
            try:
                self.config.set("connection", "port", int(port_var.get()))
            except ValueError:
                pass
            for key, var in hotkey_entries.items():
                self.config.set("hotkeys", key, var.get())
            win.destroy()
            # Rebuild UI with new language
            if new_lang != current_lang and self._root:
                self._root.after(100, self._rebuild_main)

        tk.Button(
            main, text=f"💾  {t('save')}",
            bg=ACCENT, fg="white", activebackground=ACCENT_LT,
            font=("Segoe UI", 11, "bold"), borderwidth=0,
            padx=30, pady=8, cursor="hand2", command=save,
        ).pack(pady=15)

    def _capture_hotkey(self, entry_widget, parent_win):
        cap = tk.Toplevel(parent_win)
        cap.title("⌨")
        cap.geometry("300x100")
        cap.configure(bg=BG_DARK)
        cap.grab_set()
        cap.focus_force()

        tk.Label(cap, text=t("capture_key"),
                 bg=BG_DARK, fg=TEXT_PRI, font=("Segoe UI", 11)).pack(expand=True)

        def on_key(event):
            key = event.keysym.lower()
            mods = []
            if event.state & 0x4: mods.append("ctrl")
            if event.state & 0x8: mods.append("alt")
            if event.state & 0x1: mods.append("shift")
            if key not in ("control_l", "control_r", "alt_l", "alt_r",
                           "shift_l", "shift_r"):
                result = "+".join(mods + [key])
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, result)
                cap.destroy()

        cap.bind("<KeyPress>", on_key)

"""
MicProject - Auto Updater
Checks for updates from a remote version.json and self-replaces the exe.

version.json format (host this on GitHub, your server, etc.):
{
    "version": "1.1.0",
    "url": "https://example.com/MicProject.exe",
    "changelog": "Fixed bugs, improved UI"
}
"""

import json
import os
import sys
import tempfile
import threading
import tkinter as tk
import urllib.request
import subprocess

from version import APP_VERSION, UPDATE_CHECK_URL
from i18n import t

# ─── Semantic Version Comparison ───────────────────────────────────────

def _parse_version(v: str):
    """Parse '1.2.3' into tuple (1, 2, 3)."""
    parts = v.strip().split(".")
    return tuple(int(p) for p in parts)


def is_newer(remote_version: str, local_version: str = APP_VERSION) -> bool:
    """Return True if remote_version is newer than local_version."""
    try:
        return _parse_version(remote_version) > _parse_version(local_version)
    except Exception:
        return False


# ─── Check for Update ──────────────────────────────────────────────────

def check_for_update() -> dict | None:
    """
    Check remote URL for a newer version.
    Returns dict with {version, url, changelog} or None if up to date / error.
    """
    try:
        req = urllib.request.Request(UPDATE_CHECK_URL, headers={"User-Agent": "MicProject-Updater/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        remote_ver = data.get("version", "0.0.0")
        if is_newer(remote_ver):
            return {
                "version": remote_ver,
                "url": data.get("url", ""),
                "changelog": data.get("changelog", ""),
            }
    except Exception as e:
        print(f"[Updater] Check failed: {e}")
    return None


# ─── Download + Replace ────────────────────────────────────────────────

def download_update(url: str, progress_callback=None) -> str | None:
    """Download the new exe to a temp file. Returns temp file path or None."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MicProject-Updater/1.0"})
        resp = urllib.request.urlopen(req, timeout=120)

        content_length = resp.headers.get("Content-Length")
        total = int(content_length) if content_length else 0

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".exe")
        downloaded = 0
        block_size = 65536

        while True:
            chunk = resp.read(block_size)
            if not chunk:
                break
            tmp.write(chunk)
            downloaded += len(chunk)
            if progress_callback and total > 0:
                progress_callback(downloaded / total)

        tmp.close()
        return tmp.name
    except Exception as e:
        print(f"[Updater] Download failed: {e}")
        return None


def apply_update(new_exe_path: str):
    """
    Replace the current exe with the new one and restart.
    Uses a small batch script to handle the file swap while the process exits.
    """
    current_exe = sys.executable
    if not getattr(sys, 'frozen', False):
        print("[Updater] Not running as a frozen exe, skipping apply.")
        return

    # Create a batch script that waits for us to exit, swaps the file, and relaunches
    batch_content = f"""@echo off
echo Updating MicProject...
timeout /t 2 /nobreak >nul
del "{current_exe}"
move "{new_exe_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
    batch_path = os.path.join(tempfile.gettempdir(), "micproject_update.bat")
    with open(batch_path, "w") as f:
        f.write(batch_content)

    # Launch the batch script and exit
    subprocess.Popen(["cmd", "/c", batch_path], shell=True,
                     creationflags=subprocess.CREATE_NO_WINDOW)
    sys.exit(0)


# ─── UI Dialog ─────────────────────────────────────────────────────────

BG_DARK   = "#0A0A14"
BG_CARD   = "#14142A"
ACCENT    = "#7C6FFF"
ACCENT_LT = "#9B8FFF"
GREEN     = "#00E676"
TEXT_PRI  = "#F0F0F5"
TEXT_SEC  = "#7A7A95"


class UpdateDialog:
    """Tkinter dialog for update prompt + progress."""

    def __init__(self, parent, update_info: dict):
        self.update_info = update_info
        self.result = False  # True if user accepted

        self.win = tk.Toplevel(parent)
        self.win.title("MicProject - Update")
        self.win.geometry("420x280")
        self.win.resizable(False, False)
        self.win.configure(bg=BG_DARK)
        self.win.grab_set()

        # Center
        self.win.update_idletasks()
        x = (self.win.winfo_screenwidth() // 2) - 210
        y = (self.win.winfo_screenheight() // 2) - 140
        self.win.geometry(f"+{x}+{y}")

        main = tk.Frame(self.win, bg=BG_DARK, padx=24, pady=20)
        main.pack(fill="both", expand=True)

        # Title
        tk.Label(main, text="🔄  Nueva versión disponible",
                 bg=BG_DARK, fg=TEXT_PRI,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w")

        # Version info
        tk.Label(main,
                 text=f"Versión actual: {APP_VERSION}  →  Nueva: {update_info['version']}",
                 bg=BG_DARK, fg=TEXT_SEC,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(8, 4))

        # Changelog
        changelog = update_info.get("changelog", "")
        if changelog:
            tk.Label(main, text=changelog, bg=BG_DARK, fg=TEXT_SEC,
                     font=("Segoe UI", 9), wraplength=370,
                     justify="left").pack(anchor="w", pady=(0, 8))

        # Progress bar (hidden initially)
        self._progress_frame = tk.Frame(main, bg=BG_DARK)
        self._progress_var = tk.DoubleVar(value=0)
        self._progress_bar = None
        self._progress_label = tk.Label(self._progress_frame,
                                         text="Descargando...",
                                         bg=BG_DARK, fg=TEXT_SEC,
                                         font=("Segoe UI", 9))

        # Buttons (at the bottom)
        btn_frame = tk.Frame(main, bg=BG_DARK)
        btn_frame.pack(side="bottom", fill="x", pady=(10, 0))

        self._update_btn = tk.Button(
            btn_frame, text="⬇  Actualizar ahora",
            bg=GREEN, fg="white", activebackground=GREEN,
            font=("Segoe UI", 10, "bold"), borderwidth=0,
            padx=20, pady=8, cursor="hand2",
            command=self._start_update,
        )
        self._update_btn.pack(side="left")

        tk.Button(
            btn_frame, text="Después",
            bg=BG_CARD, fg=TEXT_SEC, activebackground=BG_CARD,
            font=("Segoe UI", 10), borderwidth=0,
            padx=16, pady=8, cursor="hand2",
            command=self.win.destroy,
        ).pack(side="right")

    def _start_update(self):
        """Start downloading the update."""
        self._update_btn.config(state="disabled", text="Descargando...")

        # Show progress bar
        self._progress_frame.pack(fill="x", pady=(4, 0))
        self._progress_label.pack(anchor="w")

        from tkinter import ttk
        self._progress_bar = ttk.Progressbar(
            self._progress_frame, length=370, mode="determinate",
            maximum=100, variable=self._progress_var,
        )
        self._progress_bar.pack(fill="x", pady=(4, 0))

        # Download in background thread
        def do_download():
            url = self.update_info.get("url", "")
            if not url:
                self._progress_label.config(text="Error: URL no disponible")
                return

            def on_progress(pct):
                self._progress_var.set(pct * 100)
                self._progress_label.config(text=f"Descargando... {int(pct * 100)}%")

            new_exe = download_update(url, on_progress)
            if new_exe:
                self._progress_label.config(text="Aplicando actualización...")
                self.win.after(500, lambda: apply_update(new_exe))
            else:
                self._progress_label.config(text="Error al descargar. Inténtalo de nuevo.")
                self._update_btn.config(state="normal", text="⬇  Reintentar")

        threading.Thread(target=do_download, daemon=True).start()


def check_and_prompt(parent_window):
    """Check for updates and show dialog if available. Call from dashboard."""
    def do_check():
        info = check_for_update()
        if info:
            parent_window.after(0, lambda: UpdateDialog(parent_window, info))
        else:
            parent_window.after(0, lambda: _show_up_to_date(parent_window))

    threading.Thread(target=do_check, daemon=True).start()


def _show_up_to_date(parent):
    """Quick popup: no updates available."""
    win = tk.Toplevel(parent)
    win.title("MicProject")
    win.geometry("300x120")
    win.configure(bg=BG_DARK)
    win.grab_set()
    win.update_idletasks()
    x = (win.winfo_screenwidth() // 2) - 150
    y = (win.winfo_screenheight() // 2) - 60
    win.geometry(f"+{x}+{y}")

    tk.Label(win, text=f"✅  Estás al día (v{APP_VERSION})",
             bg=BG_DARK, fg=TEXT_PRI,
             font=("Segoe UI", 12, "bold")).pack(expand=True)
    tk.Button(win, text="OK", bg=ACCENT, fg="white",
              font=("Segoe UI", 10, "bold"), borderwidth=0,
              padx=20, pady=6, command=win.destroy).pack(pady=(0, 16))

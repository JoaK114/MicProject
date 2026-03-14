"""
MicProject Setup - Installer Wizard
Downloads and installs VB-Cable, MicProject.exe, and creates shortcuts.
Compile to exe with: python -m PyInstaller installer.spec --noconfirm --clean
"""

import os
import sys
import ctypes
import shutil
import tempfile
import threading
import subprocess
import urllib.request
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# ─── Config ────────────────────────────────────────────────────────────

APP_NAME = "MicProject"
# VB-Cable download URL (official)
VBCABLE_URL = "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack43.zip"
# MicProject.exe download URL (placeholder — replace with your real URL)
APP_EXE_URL = "https://github.com/MicProject/releases/download/latest/MicProject.exe"
DEFAULT_INSTALL_DIR = os.path.join(os.environ.get("LOCALAPPDATA", "C:\\Users\\Default\\AppData\\Local"), APP_NAME)

# ─── Colors ────────────────────────────────────────────────────────────

BG_DARK    = "#0A0A14"
BG_CARD    = "#14142A"
BG_CARD_LT = "#1E1E3A"
ACCENT     = "#7C6FFF"
ACCENT_LT  = "#9B8FFF"
GREEN      = "#00E676"
RED        = "#FF5252"
TEXT_PRI   = "#F0F0F5"
TEXT_SEC   = "#7A7A95"
TEXT_DIM   = "#50506A"

# ─── Helpers ───────────────────────────────────────────────────────────

def is_admin():
    """Check if running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin():
    """Re-launch the script as administrator."""
    if getattr(sys, 'frozen', False):
        exe = sys.executable
    else:
        exe = sys.executable
    params = " ".join([f'"{arg}"' for arg in sys.argv])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    sys.exit(0)


def download_file(url, dest_path, progress_callback=None):
    """Download a file with progress reporting."""
    req = urllib.request.Request(url, headers={"User-Agent": "MicProject-Installer/1.0"})
    resp = urllib.request.urlopen(req, timeout=120)
    content_length = resp.headers.get("Content-Length")
    total = int(content_length) if content_length else 0

    downloaded = 0
    block = 65536

    with open(dest_path, "wb") as f:
        while True:
            chunk = resp.read(block)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            if progress_callback and total > 0:
                progress_callback(downloaded / total)

    return dest_path


def create_shortcut(target_exe, shortcut_path, description=""):
    """Create a Windows shortcut (.lnk) using PowerShell."""
    ps_cmd = f'''
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("{shortcut_path}")
$s.TargetPath = "{target_exe}"
$s.Description = "{description}"
$s.WorkingDirectory = "{os.path.dirname(target_exe)}"
$s.Save()
'''
    subprocess.run(["powershell", "-Command", ps_cmd],
                   capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)


# ─── Installer GUI ────────────────────────────────────────────────────

class InstallerApp:
    """Branded setup wizard for MicProject."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} Setup")
        self.root.geometry("560x420")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_DARK)

        # Center
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - 280
        y = (self.root.winfo_screenheight() // 2) - 210
        self.root.geometry(f"+{x}+{y}")

        # Try to set icon
        try:
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            ico = os.path.join(base_dir, "assets", "icon.ico")
            if os.path.exists(ico):
                self.root.iconbitmap(ico)
        except Exception:
            pass

        self.install_dir = tk.StringVar(value=DEFAULT_INSTALL_DIR)
        self.install_vbcable = tk.BooleanVar(value=True)
        self.create_desktop_shortcut = tk.BooleanVar(value=True)
        self.create_startmenu = tk.BooleanVar(value=True)

        self._current_step = 0
        self._steps = [
            self._step_welcome,
            self._step_options,
            self._step_installing,
            self._step_done,
        ]

        self._main_frame = tk.Frame(self.root, bg=BG_DARK)
        self._main_frame.pack(fill="both", expand=True)

        self._show_step(0)
        self.root.mainloop()

    def _clear_frame(self):
        for w in self._main_frame.winfo_children():
            w.destroy()

    def _show_step(self, idx):
        self._current_step = idx
        self._clear_frame()
        self._steps[idx]()

    # ─── Step 1: Welcome ──────────────────────────────────────────

    def _step_welcome(self):
        f = tk.Frame(self._main_frame, bg=BG_DARK, padx=40, pady=30)
        f.pack(fill="both", expand=True)

        # Logo
        tk.Label(f, text="🎤", bg=BG_DARK, fg=ACCENT,
                 font=("Segoe UI", 48)).pack(pady=(10, 0))
        tk.Label(f, text=APP_NAME, bg=BG_DARK, fg=TEXT_PRI,
                 font=("Segoe UI", 28, "bold")).pack()
        tk.Label(f, text="Tu celular como micrófono para PC",
                 bg=BG_DARK, fg=TEXT_SEC,
                 font=("Segoe UI", 11)).pack(pady=(4, 0))

        tk.Label(f, text="Este asistente instalará todo lo necesario\npara usar MicProject en tu PC.",
                 bg=BG_DARK, fg=TEXT_SEC,
                 font=("Segoe UI", 10), justify="center").pack(pady=(30, 0))

        # Bottom buttons
        btn_f = tk.Frame(f, bg=BG_DARK)
        btn_f.pack(side="bottom", fill="x", pady=(20, 0))

        tk.Button(btn_f, text="Siguiente  →", bg=ACCENT, fg="white",
                  activebackground=ACCENT_LT, font=("Segoe UI", 11, "bold"),
                  borderwidth=0, padx=24, pady=10, cursor="hand2",
                  command=lambda: self._show_step(1)).pack(side="right")

        tk.Button(btn_f, text="Cancelar", bg=BG_CARD, fg=TEXT_SEC,
                  font=("Segoe UI", 10), borderwidth=0, padx=16, pady=10,
                  cursor="hand2", command=self.root.destroy).pack(side="left")

    # ─── Step 2: Options ──────────────────────────────────────────

    def _step_options(self):
        f = tk.Frame(self._main_frame, bg=BG_DARK, padx=40, pady=24)
        f.pack(fill="both", expand=True)

        tk.Label(f, text="⚙  Opciones de instalación", bg=BG_DARK, fg=TEXT_PRI,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w")

        # Install directory
        tk.Label(f, text="Carpeta de instalación:", bg=BG_DARK, fg=TEXT_SEC,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(16, 4))

        dir_frame = tk.Frame(f, bg=BG_DARK)
        dir_frame.pack(fill="x")
        tk.Entry(dir_frame, textvariable=self.install_dir, bg=BG_CARD, fg=TEXT_PRI,
                 insertbackground=TEXT_PRI, borderwidth=0,
                 font=("Segoe UI", 10)).pack(side="left", fill="x", expand=True, ipady=6)
        tk.Button(dir_frame, text="📁", bg=BG_CARD_LT, fg=TEXT_PRI,
                  font=("Segoe UI", 10), borderwidth=0, padx=10,
                  command=self._browse_dir).pack(side="right", padx=(4, 0))

        # Components
        tk.Label(f, text="Componentes:", bg=BG_DARK, fg=TEXT_SEC,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(20, 8))

        tk.Checkbutton(f, text="  Instalar VB-Cable (driver de audio virtual)",
                       variable=self.install_vbcable,
                       bg=BG_DARK, fg=TEXT_PRI, selectcolor=BG_CARD,
                       activebackground=BG_DARK, activeforeground=TEXT_PRI,
                       font=("Segoe UI", 10)).pack(anchor="w")

        tk.Checkbutton(f, text="  Crear acceso directo en el Escritorio",
                       variable=self.create_desktop_shortcut,
                       bg=BG_DARK, fg=TEXT_PRI, selectcolor=BG_CARD,
                       activebackground=BG_DARK, activeforeground=TEXT_PRI,
                       font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 0))

        tk.Checkbutton(f, text="  Agregar al menú Inicio",
                       variable=self.create_startmenu,
                       bg=BG_DARK, fg=TEXT_PRI, selectcolor=BG_CARD,
                       activebackground=BG_DARK, activeforeground=TEXT_PRI,
                       font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 0))

        # Info about VB-Cable (if needed)
        tk.Label(f, text="ℹ VB-Cable es necesario para que la PC reciba el audio.\n"
                         "  Requiere permisos de administrador para instalarse.",
                 bg=BG_DARK, fg=TEXT_DIM,
                 font=("Segoe UI", 8), justify="left").pack(anchor="w", pady=(16, 0))

        # Buttons
        btn_f = tk.Frame(f, bg=BG_DARK)
        btn_f.pack(side="bottom", fill="x", pady=(10, 0))

        tk.Button(btn_f, text="Instalar  →", bg=GREEN, fg="white",
                  activebackground=GREEN, font=("Segoe UI", 11, "bold"),
                  borderwidth=0, padx=24, pady=10, cursor="hand2",
                  command=lambda: self._show_step(2)).pack(side="right")

        tk.Button(btn_f, text="←  Atrás", bg=BG_CARD, fg=TEXT_SEC,
                  font=("Segoe UI", 10), borderwidth=0, padx=16, pady=10,
                  cursor="hand2", command=lambda: self._show_step(0)).pack(side="left")

    def _browse_dir(self):
        d = filedialog.askdirectory(initialdir=self.install_dir.get())
        if d:
            self.install_dir.set(d)

    # ─── Step 3: Installing ───────────────────────────────────────

    def _step_installing(self):
        f = tk.Frame(self._main_frame, bg=BG_DARK, padx=40, pady=30)
        f.pack(fill="both", expand=True)

        tk.Label(f, text="⏳  Instalando...", bg=BG_DARK, fg=TEXT_PRI,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w")

        self._log_text = tk.Text(f, bg=BG_CARD, fg=TEXT_SEC,
                                  font=("Consolas", 9), borderwidth=0,
                                  height=12, state="disabled")
        self._log_text.pack(fill="both", expand=True, pady=(16, 8))

        self._progress = ttk.Progressbar(f, length=480, mode="determinate", maximum=100)
        self._progress.pack(fill="x")

        self._status_label = tk.Label(f, text="Preparando...", bg=BG_DARK, fg=TEXT_SEC,
                                       font=("Segoe UI", 9))
        self._status_label.pack(anchor="w", pady=(4, 0))

        threading.Thread(target=self._run_install, daemon=True).start()

    def _log(self, msg):
        def _do():
            self._log_text.config(state="normal")
            self._log_text.insert("end", msg + "\n")
            self._log_text.see("end")
            self._log_text.config(state="disabled")
        self.root.after(0, _do)

    def _set_progress(self, value, status=""):
        def _do():
            self._progress["value"] = value
            if status:
                self._status_label.config(text=status)
        self.root.after(0, _do)

    def _run_install(self):
        """Main install logic — runs in background thread."""
        install_dir = self.install_dir.get()
        os.makedirs(install_dir, exist_ok=True)
        self._log(f"📁 Carpeta: {install_dir}")

        total_steps = 3
        step = 0

        # ── Step 1: VB-Cable ──
        if self.install_vbcable.get():
            step += 1
            self._set_progress((step / total_steps) * 30, "Descargando VB-Cable...")
            self._log("🔽 Descargando VB-Cable driver...")

            try:
                zip_path = os.path.join(tempfile.gettempdir(), "vbcable.zip")
                download_file(VBCABLE_URL, zip_path,
                              lambda p: self._set_progress(p * 30, f"VB-Cable: {int(p*100)}%"))

                self._log("📦 Extrayendo VB-Cable...")
                import zipfile
                extract_dir = os.path.join(tempfile.gettempdir(), "vbcable")
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(extract_dir)

                # Find the setup executable
                setup_exe = None
                for root, dirs, files in os.walk(extract_dir):
                    for fname in files:
                        if fname.lower() == "vbcable_setup_x64.exe":
                            setup_exe = os.path.join(root, fname)
                            break
                    if not setup_exe:
                        for fname in files:
                            if fname.lower() == "vbcable_setup.exe":
                                setup_exe = os.path.join(root, fname)
                                break

                if setup_exe:
                    self._log("🔧 Instalando VB-Cable (requiere admin)...")
                    self._set_progress(35, "Instalando VB-Cable (ventana de admin)...")
                    # Run the installer — it will trigger UAC prompt
                    result = subprocess.run(
                        [setup_exe, "-i", "-h"],  # -i = install, -h = silent (if supported)
                        capture_output=True, timeout=60
                    )
                    if result.returncode == 0:
                        self._log("✅ VB-Cable instalado correctamente")
                    else:
                        # Try interactive install
                        self._log("⚠ Instalación silenciosa no disponible, abriendo instalador...")
                        subprocess.run([setup_exe], timeout=120)
                        self._log("✅ VB-Cable instalado (manual)")
                else:
                    self._log("⚠ No se encontró el instalador de VB-Cable en el zip")

                # Cleanup
                try:
                    os.remove(zip_path)
                    shutil.rmtree(extract_dir, ignore_errors=True)
                except Exception:
                    pass

            except Exception as e:
                self._log(f"❌ Error con VB-Cable: {e}")
                self._log("💡 Puedes instalar VB-Cable manualmente desde:")
                self._log("   https://vb-audio.com/Cable/")

        self._set_progress(40, "Descargando MicProject...")

        # ── Step 2: Download MicProject.exe ──
        self._log("🔽 Descargando MicProject.exe...")
        exe_dest = os.path.join(install_dir, "MicProject.exe")

        try:
            # First check if exe is bundled with the installer
            bundled_exe = None
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            bundled_path = os.path.join(base_dir, "bundled", "MicProject.exe")
            if os.path.exists(bundled_path):
                # Copy bundled exe instead of downloading
                self._log("📦 Usando MicProject.exe empaquetado...")
                shutil.copy2(bundled_path, exe_dest)
                self._set_progress(70, "MicProject.exe copiado")
                self._log("✅ MicProject.exe instalado")
            else:
                # Download from URL
                download_file(APP_EXE_URL, exe_dest,
                              lambda p: self._set_progress(40 + p * 30, f"MicProject: {int(p*100)}%"))
                self._log("✅ MicProject.exe descargado")
        except Exception as e:
            self._log(f"❌ Error descargando: {e}")
            self._log("💡 Descarga manual: coloca MicProject.exe en la carpeta de instalación")

        self._set_progress(75, "Creando accesos directos...")

        # ── Step 3: Shortcuts ──
        if self.create_desktop_shortcut.get():
            try:
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                shortcut_path = os.path.join(desktop, f"{APP_NAME}.lnk")
                create_shortcut(exe_dest, shortcut_path, "Tu celular como micrófono para PC")
                self._log(f"🔗 Acceso directo creado en el Escritorio")
            except Exception as e:
                self._log(f"⚠ Error creando acceso directo: {e}")

        if self.create_startmenu.get():
            try:
                start_menu = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs")
                sm_folder = os.path.join(start_menu, APP_NAME)
                os.makedirs(sm_folder, exist_ok=True)
                shortcut_path = os.path.join(sm_folder, f"{APP_NAME}.lnk")
                create_shortcut(exe_dest, shortcut_path, "Tu celular como micrófono para PC")
                self._log(f"📌 Agregado al menú Inicio")
            except Exception as e:
                self._log(f"⚠ Error en menú Inicio: {e}")

        self._set_progress(100, "¡Instalación completada!")
        self._log("")
        self._log("🎉 ¡Instalación completada!")
        self._log(f"📁 MicProject instalado en: {install_dir}")

        # Go to done step
        self.root.after(1500, lambda: self._show_step(3))

    # ─── Step 4: Done ─────────────────────────────────────────────

    def _step_done(self):
        f = tk.Frame(self._main_frame, bg=BG_DARK, padx=40, pady=30)
        f.pack(fill="both", expand=True)

        tk.Label(f, text="✅", bg=BG_DARK, fg=GREEN,
                 font=("Segoe UI", 48)).pack(pady=(20, 0))
        tk.Label(f, text="¡Instalación completada!", bg=BG_DARK, fg=TEXT_PRI,
                 font=("Segoe UI", 20, "bold")).pack(pady=(8, 0))
        tk.Label(f, text="MicProject está listo para usar.\n\n"
                         "1. Abre MicProject en tu PC\n"
                         "2. Instala la app en tu celular Android\n"
                         "3. Conéctate por WiFi, USB o IP directa",
                 bg=BG_DARK, fg=TEXT_SEC,
                 font=("Segoe UI", 10), justify="center").pack(pady=(16, 0))

        btn_f = tk.Frame(f, bg=BG_DARK)
        btn_f.pack(side="bottom", fill="x", pady=(20, 0))

        exe_path = os.path.join(self.install_dir.get(), "MicProject.exe")

        def launch_and_close():
            if os.path.exists(exe_path):
                subprocess.Popen([exe_path])
            self.root.destroy()

        tk.Button(btn_f, text="🚀  Iniciar MicProject", bg=GREEN, fg="white",
                  activebackground=GREEN, font=("Segoe UI", 11, "bold"),
                  borderwidth=0, padx=24, pady=10, cursor="hand2",
                  command=launch_and_close).pack(side="right")

        tk.Button(btn_f, text="Cerrar", bg=BG_CARD, fg=TEXT_SEC,
                  font=("Segoe UI", 10), borderwidth=0, padx=16, pady=10,
                  cursor="hand2", command=self.root.destroy).pack(side="left")


# ─── Entry Point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    InstallerApp()

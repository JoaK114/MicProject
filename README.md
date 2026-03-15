# 🎤 MicProject - Micrófono Remoto para PC

Usa el micrófono de tu celular Android como micrófono en tu PC con Windows.

## Características

- 📡 **Conexión WiFi** — auto-discovery en la misma red local
- 🔌 **Conexión USB** — vía ADB port forwarding, mínima latencia
- 🔊 **Control de volumen** — desde el celular y desde la PC
- ⌨️ **Teclas rápidas** — mute, push-to-talk, volumen (configurables)
- 🪶 **Ultra liviano** — ~25 MB RAM, sin Electron, sin frameworks pesados
- 🛡️ **Anti-detección** — firmado, sin hooks, sin packers, anti-cheat friendly

---

## Requisitos

### PC (Windows)
- **Python 3.10+** → [Descargar](https://www.python.org/downloads/)
- **VB-Cable** → [Descargar](https://vb-audio.com/Cable/) (instalar una vez)

### Celular
- **Android 8.0+** (API 26)

EN CASO DE INSTALAR MEDIANTE CODIGO
- **Android Studio** para compilar la app (o APK precompilado)
- **Depuración USB activada** (para modo USB)

---

## Instalación

### 1. Servidor PC

```bash
cd pc-server
pip install -r requirements.txt
python main.py
```

### 2. App Android

1. Abrir `android-app/` como proyecto en Android Studio
2. Compilar e instalar en el celular
3. ¡Listo!

---

## Uso

### Modo WiFi
1. Conecta PC y celular a la **misma red WiFi**
2. Ejecuta `python main.py` en la PC
3. Abre la app en el celular → se conecta automáticamente

### Modo USB
1. Conecta el celular por USB con **depuración USB** activada
2. La app detecta automáticamente el modo USB
3. Mayor estabilidad y menor latencia que WiFi

### Hotkeys (por defecto)
| Tecla | Acción |
|-------|--------|
| `Ctrl+M` | Mutear / Desmutear |
| `Ctrl+↑` | Subir volumen |
| `Ctrl+↓` | Bajar volumen |

Configurables desde el menú de la bandeja del sistema.

---

## Configuración

El archivo de configuración se guarda automáticamente en:
```
%APPDATA%/MicProject/config.json
```

---

## Compilar ejecutable (.exe)

```bash
cd pc-server
pip install pyinstaller
pyinstaller build.spec
```

El ejecutable estará en `dist/MicProject.exe`.

---

## Estructura del Proyecto

```
MicProject/
├── pc-server/                # Servidor para Windows
│   ├── main.py               # Entry point
│   ├── config.py             # Configuración
│   ├── audio_output.py       # Salida a VB-Cable
│   ├── audio_receiver.py     # Receptor WiFi/USB
│   ├── connection_manager.py # Descubrimiento + control
│   ├── hotkey_manager.py     # Teclas rápidas globales
│   ├── tray_app.py           # UI en bandeja del sistema
│   ├── build.spec            # PyInstaller config
│   └── requirements.txt
├── android-app/              # App Android (Kotlin)
│   ├── app/src/main/
│   │   ├── java/com/micproject/app/
│   │   │   ├── MainActivity.kt
│   │   │   ├── audio/
│   │   │   │   ├── MicCaptureService.kt
│   │   │   │   └── AudioConfig.kt
│   │   │   └── network/
│   │   │       └── NetworkStreamer.kt
│   │   └── AndroidManifest.xml
│   ├── app/build.gradle.kts
│   ├── build.gradle.kts
│   └── settings.gradle.kts
└── README.md
```

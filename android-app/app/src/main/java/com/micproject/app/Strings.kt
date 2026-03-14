package com.micproject.app

import android.content.Context
import android.content.SharedPreferences

/**
 * Lightweight i18n system for MicProject.
 * Supports English (en) and Spanish (es).
 * Language choice is persisted via SharedPreferences.
 */
object Strings {

    private var lang: String = "es"

    private val table: Map<String, Map<String, String>> = mapOf(
        "es" to mapOf(
            // General
            "app_name" to "MicProject",
            "app_subtitle" to "Micrófono Remoto para PC",

            // Language picker
            "lang_title" to "Seleccionar Idioma",
            "lang_confirm" to "Confirmar",

            // Connection
            "connected" to "Conectado",
            "disconnected" to "Desconectado",
            "connecting" to "Conectando...",
            "searching" to "Buscando servidor...",
            "detected_server" to "Servidor detectado",

            // Connection mode
            "connection_mode" to "MODO DE CONEXIÓN",
            "wifi" to "WiFi",
            "direct" to "Directa",
            "usb" to "USB",
            "disconnect_to_change" to "Desconectá para cambiar de modo",
            "server_ip" to "IP del Servidor",
            "server_ip_hint" to "ej. 192.168.1.100",
            "auto_detect" to "Auto-detectar",

            // Volume
            "volume" to "Volumen",

            // Buttons
            "mute" to "MUTEAR",
            "muted" to "MUTEADO",
            "start" to "INICIAR",
            "stop" to "DETENER",

            // Support
            "support" to "❤ Apoyar en Patreon",

            // Errors
            "connection_error" to "Error de Conexión",
            "ok" to "ENTENDIDO",
            "empty_ip" to "Ingresá la IP del servidor antes de conectar.",
            "wifi_timeout" to "No se encontró el servidor PC en la red WiFi.\n\n• Verificá que el servidor esté corriendo\n• Verificá que estés en la misma red WiFi\n• Revisá el firewall de Windows",
            "usb_timeout" to "No se pudo conectar por USB.\n\n• Conectá el celular a la PC por cable\n• Habilitá Depuración USB en opciones de desarrollador\n• Ejecutá en la PC: adb forward tcp:4545 tcp:4545",
        ),
        "en" to mapOf(
            // General
            "app_name" to "MicProject",
            "app_subtitle" to "Remote Microphone for PC",

            // Language picker
            "lang_title" to "Select Language",
            "lang_confirm" to "Confirm",

            // Connection
            "connected" to "Connected",
            "disconnected" to "Disconnected",
            "connecting" to "Connecting...",
            "searching" to "Searching for server...",
            "detected_server" to "Server detected",

            // Connection mode
            "connection_mode" to "CONNECTION MODE",
            "wifi" to "WiFi",
            "direct" to "Direct",
            "usb" to "USB",
            "disconnect_to_change" to "Disconnect to change mode",
            "server_ip" to "Server IP",
            "server_ip_hint" to "e.g. 192.168.1.100",
            "auto_detect" to "Auto-detect",

            // Volume
            "volume" to "Volume",

            // Buttons
            "mute" to "MUTE",
            "muted" to "MUTED",
            "start" to "START",
            "stop" to "STOP",

            // Support
            "support" to "❤ Support on Patreon",

            // Errors
            "connection_error" to "Connection Error",
            "ok" to "OK",
            "empty_ip" to "Enter a server IP before connecting.",
            "wifi_timeout" to "PC server not found on WiFi network.\n\n• Make sure the server is running\n• Make sure you're on the same WiFi\n• Check Windows Firewall",
            "usb_timeout" to "Could not connect via USB.\n\n• Connect phone to PC with a cable\n• Enable USB Debugging in Developer Options\n• Run on PC: adb forward tcp:4545 tcp:4545",
        ),
    )

    /** Get a translated string */
    fun get(key: String): String {
        return table[lang]?.get(key) ?: table["es"]?.get(key) ?: key
    }

    /** Get current language */
    fun getLang(): String = lang

    /** Set language (without saving) */
    fun setLang(language: String) {
        lang = language
    }

    /** Load saved language from SharedPreferences. Returns true if already saved. */
    fun loadLanguage(context: Context): Boolean {
        val prefs = context.getSharedPreferences("micproject_settings", Context.MODE_PRIVATE)
        val saved = prefs.getString("language", null)
        if (saved != null) {
            lang = saved
            return true
        }
        return false
    }

    /** Save language to SharedPreferences */
    fun saveLanguage(context: Context, language: String) {
        lang = language
        context.getSharedPreferences("micproject_settings", Context.MODE_PRIVATE)
            .edit()
            .putString("language", language)
            .apply()
    }
}

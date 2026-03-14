package com.micproject.app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.micproject.app.audio.MicCaptureService
import com.micproject.app.network.ConnectionState
import java.net.DatagramPacket
import java.net.DatagramSocket
import org.json.JSONObject

// Patreon placeholder - update with real URL
const val PATREON_URL = "https://patreon.com/MicProject"

class MainActivity : ComponentActivity() {

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        if (permissions[Manifest.permission.RECORD_AUDIO] == true) {
            // Permission granted
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestPermissions()
        autoDetectServerIP()

        // Check if language already selected
        val hasLanguage = Strings.loadLanguage(this)

        setContent {
            MicProjectTheme {
                if (!hasLanguage && !AppState.languageSelected.value) {
                    LanguagePickerScreen()
                } else {
                    MicProjectApp(
                        onStartService = { mode -> startMicService(mode) },
                        onStopService = { stopMicService() }
                    )
                }
            }
        }
    }

    private fun requestPermissions() {
        val permissions = mutableListOf(Manifest.permission.RECORD_AUDIO)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissions.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        val neededPermissions = permissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (neededPermissions.isNotEmpty()) {
            requestPermissionLauncher.launch(neededPermissions.toTypedArray())
        }
    }

    private fun autoDetectServerIP() {
        Thread({
            try {
                val socket = DatagramSocket(4547)
                socket.broadcast = true
                socket.soTimeout = 0
                val buffer = ByteArray(1024)
                val packet = DatagramPacket(buffer, buffer.size)
                while (true) {
                    try {
                        socket.receive(packet)
                        val data = String(packet.data, 0, packet.length)
                        val json = JSONObject(data)
                        if (json.optString("magic") == "MICPROJECT_DISCOVER") {
                            val ip = json.getString("ip")
                            AppState.detectedServerIP.value = ip
                            if (AppState.directIP.value.isEmpty()) {
                                AppState.directIP.value = ip
                            }
                        }
                    } catch (_: Exception) { }
                }
            } catch (_: Exception) { }
        }, "AutoDetectIP").apply { isDaemon = true; start() }
    }

    private fun startMicService(mode: String) {
        val intent = Intent(this, MicCaptureService::class.java).apply {
            action = MicCaptureService.ACTION_START
            putExtra(MicCaptureService.EXTRA_MODE, mode)
        }
        ContextCompat.startForegroundService(this, intent)
    }

    private fun stopMicService() {
        val intent = Intent(this, MicCaptureService::class.java).apply {
            action = MicCaptureService.ACTION_STOP
        }
        startService(intent)
    }
}

// ─── Color Palette ────────────────────────────────────────────────────

val DarkBackground = Color(0xFF0A0A14)
val DarkSurface = Color(0xFF14142A)
val DarkSurfaceLight = Color(0xFF1E1E3A)
val AccentPurple = Color(0xFF7C6FFF)
val AccentPurpleLight = Color(0xFF9B8FFF)
val AccentGreen = Color(0xFF00E676)
val AccentGreenDark = Color(0xFF00C853)
val AccentRed = Color(0xFFFF5252)
val AccentOrange = Color(0xFFFFAB40)
val TextPrimary = Color(0xFFF0F0F5)
val TextSecondary = Color(0xFF7A7A95)

@Composable
fun MicProjectTheme(content: @Composable () -> Unit) {
    val colorScheme = darkColorScheme(
        primary = AccentPurple,
        secondary = AccentGreen,
        background = DarkBackground,
        surface = DarkSurface,
        onPrimary = Color.White,
        onBackground = TextPrimary,
        onSurface = TextPrimary,
        error = AccentRed,
    )
    MaterialTheme(colorScheme = colorScheme, content = content)
}

// ─── Language Picker Screen ───────────────────────────────────────────

@Composable
fun LanguagePickerScreen() {
    val context = LocalContext.current
    var selectedLang by remember { mutableStateOf("es") }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBackground),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.padding(32.dp),
        ) {
            // Mic icon
            Box(
                modifier = Modifier
                    .size(72.dp)
                    .clip(CircleShape)
                    .background(
                        Brush.linearGradient(listOf(AccentPurple, AccentPurpleLight))
                    ),
                contentAlignment = Alignment.Center,
            ) {
                Icon(Icons.Default.Mic, contentDescription = null,
                    tint = Color.White, modifier = Modifier.size(36.dp))
            }

            Spacer(modifier = Modifier.height(20.dp))

            Text("MicProject", fontSize = 28.sp, fontWeight = FontWeight.ExtraBold,
                color = TextPrimary)
            Spacer(modifier = Modifier.height(8.dp))
            Text("Select Language / Seleccionar Idioma",
                fontSize = 14.sp, color = TextSecondary, textAlign = TextAlign.Center)

            Spacer(modifier = Modifier.height(40.dp))

            // Language options
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                LangOption("🇪🇸", "Español", "es", selectedLang) { selectedLang = it }
                LangOption("🇺🇸", "English", "en", selectedLang) { selectedLang = it }
            }

            Spacer(modifier = Modifier.height(40.dp))

            // Confirm button
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp)
                    .clip(RoundedCornerShape(16.dp))
                    .background(Brush.horizontalGradient(listOf(AccentPurple, AccentPurpleLight)))
                    .clickable {
                        Strings.saveLanguage(context, selectedLang)
                        AppState.languageSelected.value = true
                    },
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    if (selectedLang == "es") "Confirmar" else "Confirm",
                    fontSize = 16.sp, fontWeight = FontWeight.Bold,
                    color = Color.White, letterSpacing = 1.sp,
                )
            }
        }
    }
}

@Composable
fun LangOption(flag: String, label: String, code: String,
               selected: String, onSelect: (String) -> Unit) {
    val isSelected = code == selected
    val bg by animateColorAsState(
        if (isSelected) AccentPurple else DarkSurface,
        animationSpec = tween(200), label = "langBg"
    )
    val borderCol by animateColorAsState(
        if (isSelected) AccentPurple else DarkSurfaceLight,
        animationSpec = tween(200), label = "langBorder"
    )

    Surface(
        modifier = Modifier
            .width(140.dp)
            .height(80.dp)
            .clip(RoundedCornerShape(16.dp))
            .border(2.dp, borderCol, RoundedCornerShape(16.dp))
            .clickable { onSelect(code) },
        shape = RoundedCornerShape(16.dp),
        color = bg,
    ) {
        Column(
            modifier = Modifier.fillMaxSize(),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Text(flag, fontSize = 28.sp)
            Text(label, fontSize = 13.sp, fontWeight = FontWeight.SemiBold,
                color = Color.White)
        }
    }
}

// ─── Main App ─────────────────────────────────────────────────────────

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MicProjectApp(
    onStartService: (String) -> Unit,
    onStopService: () -> Unit
) {
    val isStreaming by AppState.isStreaming
    val isMuted by AppState.isMuted
    val volume by AppState.volume
    val connectionMode by AppState.connectionMode
    val connectionState by AppState.connectionState
    val serverIP by AppState.serverIP
    val detectedIP by AppState.detectedServerIP
    val connectionError by AppState.connectionError
    val context = LocalContext.current

    // Error dialog
    if (connectionError.isNotEmpty()) {
        AlertDialog(
            onDismissRequest = { AppState.connectionError.value = "" },
            confirmButton = {
                TextButton(onClick = { AppState.connectionError.value = "" }) {
                    Text(Strings.get("ok"), fontWeight = FontWeight.Bold)
                }
            },
            icon = {
                Icon(Icons.Default.Warning, contentDescription = null, tint = AccentRed,
                    modifier = Modifier.size(32.dp))
            },
            title = { Text(Strings.get("connection_error"), fontWeight = FontWeight.Bold) },
            text = { Text(connectionError, color = TextSecondary, fontSize = 14.sp) },
            containerColor = DarkSurface,
            titleContentColor = TextPrimary,
            shape = RoundedCornerShape(20.dp),
        )
    }

    Scaffold(
        containerColor = DarkBackground,
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            HeaderSection(connectionState, isStreaming)
            Spacer(modifier = Modifier.height(20.dp))
            StatusCard(connectionState, serverIP, detectedIP)
            Spacer(modifier = Modifier.height(16.dp))
            ConnectionModeCard(connectionMode, isLocked = isStreaming)
            Spacer(modifier = Modifier.height(16.dp))
            VolumeCard(volume, isMuted)
            Spacer(modifier = Modifier.height(24.dp))
            MuteButton(isMuted)
            Spacer(modifier = Modifier.height(12.dp))
            StartStopButton(
                isStreaming = isStreaming,
                connectionMode = connectionMode,
                onStart = { onStartService(connectionMode) },
                onStop = onStopService
            )
            Spacer(modifier = Modifier.height(16.dp))

            // ─── Patreon Support Button ───
            Surface(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp)
                    .clip(RoundedCornerShape(14.dp))
                    .clickable {
                        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(PATREON_URL))
                        context.startActivity(intent)
                    },
                shape = RoundedCornerShape(14.dp),
                color = DarkSurface,
            ) {
                Row(
                    modifier = Modifier.fillMaxSize(),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(Icons.Default.Favorite, contentDescription = null,
                        tint = AccentRed, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(Strings.get("support"), fontSize = 13.sp,
                        fontWeight = FontWeight.SemiBold, color = TextSecondary)
                }
            }

            Spacer(modifier = Modifier.height(20.dp))
        }
    }
}

// ─── Header ───────────────────────────────────────────────────────────

@Composable
fun HeaderSection(connectionState: ConnectionState, isStreaming: Boolean) {
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val pulseScale by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = if (isStreaming) 1.15f else 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(800, easing = EaseInOutCubic),
            repeatMode = RepeatMode.Reverse
        ), label = "pulseScale"
    )
    val glowAlpha by infiniteTransition.animateFloat(
        initialValue = 0.3f,
        targetValue = if (isStreaming) 0.8f else 0.3f,
        animationSpec = infiniteRepeatable(
            animation = tween(800, easing = EaseInOutCubic),
            repeatMode = RepeatMode.Reverse
        ), label = "glowAlpha"
    )

    val glowColor = when (connectionState) {
        ConnectionState.CONNECTED -> AccentGreen
        ConnectionState.CONNECTING -> AccentOrange
        ConnectionState.DISCONNECTED -> AccentPurple
    }

    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier.size(80.dp).scale(pulseScale)
        ) {
            Box(
                modifier = Modifier.size(80.dp).clip(CircleShape)
                    .background(glowColor.copy(alpha = glowAlpha * 0.15f))
                    .border(
                        width = 2.dp,
                        brush = Brush.radialGradient(
                            colors = listOf(glowColor.copy(alpha = glowAlpha), Color.Transparent)
                        ),
                        shape = CircleShape
                    )
            )
            Box(
                modifier = Modifier.size(56.dp).clip(CircleShape)
                    .background(Brush.linearGradient(listOf(AccentPurple, AccentPurpleLight))),
                contentAlignment = Alignment.Center,
            ) {
                Icon(Icons.Default.Mic, contentDescription = null,
                    tint = Color.White, modifier = Modifier.size(28.dp))
            }
        }
        Spacer(modifier = Modifier.height(12.dp))
        Text(Strings.get("app_name"), fontSize = 26.sp, fontWeight = FontWeight.ExtraBold,
            color = TextPrimary, letterSpacing = (-0.5).sp)
        Text(Strings.get("app_subtitle"), fontSize = 13.sp,
            color = TextSecondary, letterSpacing = 0.5.sp)
    }
}

// ─── Status Card ──────────────────────────────────────────────────────

@Composable
fun StatusCard(connectionState: ConnectionState, serverIP: String, detectedIP: String) {
    val statusColor = when (connectionState) {
        ConnectionState.CONNECTED -> AccentGreen
        ConnectionState.CONNECTING -> AccentOrange
        ConnectionState.DISCONNECTED -> TextSecondary
    }
    val statusText = when (connectionState) {
        ConnectionState.CONNECTED -> Strings.get("connected")
        ConnectionState.CONNECTING -> Strings.get("connecting")
        ConnectionState.DISCONNECTED -> Strings.get("disconnected")
    }
    val statusIcon = when (connectionState) {
        ConnectionState.CONNECTED -> Icons.Filled.CheckCircle
        ConnectionState.CONNECTING -> Icons.Filled.Sync
        ConnectionState.DISCONNECTED -> Icons.Outlined.Info
    }

    Card(
        modifier = Modifier.fillMaxWidth()
            .shadow(
                elevation = if (connectionState == ConnectionState.CONNECTED) 8.dp else 0.dp,
                shape = RoundedCornerShape(20.dp),
                ambientColor = AccentGreen.copy(alpha = 0.3f),
                spotColor = AccentGreen.copy(alpha = 0.3f),
            ),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = DarkSurface),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(18.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier.size(44.dp).clip(RoundedCornerShape(14.dp))
                    .background(statusColor.copy(alpha = 0.12f)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(statusIcon, contentDescription = null, tint = statusColor,
                    modifier = Modifier.size(22.dp))
            }
            Spacer(modifier = Modifier.width(14.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(statusText, fontSize = 16.sp, fontWeight = FontWeight.SemiBold,
                    color = TextPrimary)
                Spacer(modifier = Modifier.height(2.dp))
                val ipDisplay = when {
                    connectionState == ConnectionState.CONNECTED -> serverIP
                    detectedIP.isNotEmpty() -> "${Strings.get("detected_server")}: $detectedIP"
                    else -> Strings.get("searching")
                }
                Text(ipDisplay, fontSize = 12.sp, color = TextSecondary)
            }
            if (connectionState == ConnectionState.CONNECTED) {
                val dotAlpha = rememberInfiniteTransition(label = "dot")
                    .animateFloat(
                        initialValue = 0.3f, targetValue = 1f,
                        animationSpec = infiniteRepeatable(
                            tween(1000), RepeatMode.Reverse
                        ), label = "dotAlpha"
                    )
                Box(
                    modifier = Modifier.size(10.dp).clip(CircleShape)
                        .background(AccentGreen.copy(alpha = dotAlpha.value))
                )
            }
        }
    }
}

// ─── Connection Mode Card ─────────────────────────────────────────────

@Composable
fun ConnectionModeCard(currentMode: String, isLocked: Boolean = false) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = DarkSurface),
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Text(Strings.get("connection_mode"), fontSize = 11.sp,
                fontWeight = FontWeight.Bold, color = TextSecondary, letterSpacing = 1.5.sp)
            Spacer(modifier = Modifier.height(14.dp))
            Row(modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ModeChip(Strings.get("wifi"), Icons.Default.Wifi, "wifi",
                    currentMode, Modifier.weight(1f), isLocked)
                ModeChip(Strings.get("direct"), Icons.Default.Language, "direct",
                    currentMode, Modifier.weight(1f), isLocked)
                ModeChip(Strings.get("usb"), Icons.Default.Usb, "usb",
                    currentMode, Modifier.weight(1f), isLocked)
            }

            if (isLocked) {
                Spacer(modifier = Modifier.height(8.dp))
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.padding(horizontal = 4.dp),
                ) {
                    Icon(Icons.Default.Lock, contentDescription = null,
                        tint = TextSecondary, modifier = Modifier.size(12.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(Strings.get("disconnect_to_change"),
                        fontSize = 11.sp, color = TextSecondary)
                }
            }

            AnimatedVisibility(
                visible = currentMode == "direct",
                enter = expandVertically() + fadeIn(),
                exit = shrinkVertically() + fadeOut(),
            ) {
                Column {
                    Spacer(modifier = Modifier.height(14.dp))
                    val directIP by AppState.directIP
                    val detectedIP by AppState.detectedServerIP

                    OutlinedTextField(
                        value = directIP,
                        onValueChange = { AppState.directIP.value = it },
                        label = { Text(Strings.get("server_ip")) },
                        placeholder = { Text(Strings.get("server_ip_hint"),
                            color = TextSecondary.copy(alpha = 0.5f)) },
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                        leadingIcon = {
                            Icon(Icons.Default.Router, contentDescription = null,
                                tint = AccentPurple, modifier = Modifier.size(20.dp))
                        },
                        trailingIcon = {
                            if (detectedIP.isNotEmpty()) {
                                IconButton(onClick = { AppState.directIP.value = detectedIP }) {
                                    Icon(Icons.Default.MyLocation,
                                        contentDescription = Strings.get("auto_detect"),
                                        tint = AccentGreen, modifier = Modifier.size(20.dp))
                                }
                            }
                        },
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedTextColor = TextPrimary,
                            unfocusedTextColor = TextPrimary,
                            focusedBorderColor = AccentPurple,
                            unfocusedBorderColor = DarkSurfaceLight,
                            focusedLabelColor = AccentPurple,
                            unfocusedLabelColor = TextSecondary,
                            cursorColor = AccentPurple,
                            focusedContainerColor = DarkSurfaceLight.copy(alpha = 0.3f),
                            unfocusedContainerColor = DarkSurfaceLight.copy(alpha = 0.3f),
                        ),
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(14.dp),
                    )

                    if (detectedIP.isNotEmpty() && directIP != detectedIP) {
                        Spacer(modifier = Modifier.height(6.dp))
                        Row(
                            modifier = Modifier
                                .clickable { AppState.directIP.value = detectedIP }
                                .padding(horizontal = 4.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Icon(Icons.Default.AutoAwesome, contentDescription = null,
                                tint = AccentGreen, modifier = Modifier.size(14.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("${Strings.get("detected_server")}: $detectedIP",
                                fontSize = 12.sp, color = AccentGreen)
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun ModeChip(
    label: String, icon: ImageVector, mode: String,
    currentMode: String, modifier: Modifier = Modifier, isLocked: Boolean = false,
) {
    val isSelected = mode == currentMode
    val bgColor by animateColorAsState(
        when {
            isSelected -> AccentPurple
            isLocked -> DarkSurfaceLight.copy(alpha = 0.5f)
            else -> DarkSurfaceLight
        }, animationSpec = tween(200), label = "modeBg"
    )
    val contentAlpha by animateFloatAsState(
        when {
            isLocked && !isSelected -> 0.35f
            isSelected -> 1f
            else -> 0.7f
        }, animationSpec = tween(200), label = "modeAlpha"
    )

    Surface(
        modifier = modifier.height(48.dp).clip(RoundedCornerShape(14.dp))
            .then(if (!isLocked) Modifier.clickable {
                AppState.connectionMode.value = mode
            } else Modifier),
        shape = RoundedCornerShape(14.dp),
        color = bgColor, shadowElevation = if (isSelected) 4.dp else 0.dp,
    ) {
        Row(
            modifier = Modifier.fillMaxSize(),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(icon, contentDescription = null,
                tint = Color.White.copy(alpha = contentAlpha),
                modifier = Modifier.size(18.dp))
            Spacer(modifier = Modifier.width(6.dp))
            Text(label, fontSize = 13.sp, fontWeight = FontWeight.SemiBold,
                color = Color.White.copy(alpha = contentAlpha))
        }
    }
}

// ─── Volume Card ──────────────────────────────────────────────────────

@Composable
fun VolumeCard(volume: Float, isMuted: Boolean) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = DarkSurface),
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth()
            ) {
                Box(
                    modifier = Modifier.size(38.dp).clip(RoundedCornerShape(12.dp))
                        .background(
                            if (isMuted) AccentRed.copy(alpha = 0.12f)
                            else AccentPurple.copy(alpha = 0.12f)
                        ),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        if (isMuted) Icons.Default.VolumeOff else Icons.Default.VolumeUp,
                        contentDescription = null,
                        tint = if (isMuted) AccentRed else AccentPurple,
                        modifier = Modifier.size(20.dp),
                    )
                }
                Spacer(modifier = Modifier.width(12.dp))
                Text(Strings.get("volume"), fontWeight = FontWeight.SemiBold,
                    fontSize = 15.sp, color = TextPrimary)
                Spacer(modifier = Modifier.weight(1f))
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = AccentPurple.copy(alpha = 0.15f),
                ) {
                    Text("${(volume * 100).toInt()}%", fontSize = 13.sp,
                        fontWeight = FontWeight.Bold, color = AccentPurpleLight,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp))
                }
            }
            Spacer(modifier = Modifier.height(12.dp))
            Slider(
                value = volume,
                onValueChange = { AppState.volume.floatValue = it },
                valueRange = 0f..2f,
                colors = SliderDefaults.colors(
                    thumbColor = AccentPurple,
                    activeTrackColor = AccentPurple,
                    inactiveTrackColor = DarkSurfaceLight,
                ),
            )
        }
    }
}

// ─── Mute Button ──────────────────────────────────────────────────────

@Composable
fun MuteButton(isMuted: Boolean) {
    val bgColor by animateColorAsState(
        if (isMuted) AccentRed else DarkSurface,
        animationSpec = tween(250), label = "muteBg"
    )
    val borderColor by animateColorAsState(
        if (isMuted) AccentRed else DarkSurfaceLight,
        animationSpec = tween(250), label = "muteBorder"
    )

    Surface(
        modifier = Modifier.fillMaxWidth().height(52.dp)
            .clip(RoundedCornerShape(16.dp))
            .border(1.dp, borderColor, RoundedCornerShape(16.dp))
            .clickable { AppState.isMuted.value = !AppState.isMuted.value },
        shape = RoundedCornerShape(16.dp),
        color = bgColor,
    ) {
        Row(
            modifier = Modifier.fillMaxSize(),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                if (isMuted) Icons.Default.MicOff else Icons.Default.Mic,
                contentDescription = null, tint = Color.White,
                modifier = Modifier.size(22.dp),
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                if (isMuted) Strings.get("muted") else Strings.get("mute"),
                fontSize = 14.sp, fontWeight = FontWeight.Bold,
                color = Color.White, letterSpacing = 1.sp,
            )
        }
    }
}

// ─── Start/Stop Button ────────────────────────────────────────────────

@Composable
fun StartStopButton(
    isStreaming: Boolean, connectionMode: String,
    onStart: () -> Unit, onStop: () -> Unit,
) {
    val bgGradient = if (isStreaming) {
        Brush.horizontalGradient(listOf(AccentRed, AccentRed.copy(alpha = 0.8f)))
    } else {
        Brush.horizontalGradient(listOf(AccentGreen, AccentGreenDark))
    }

    Box(
        modifier = Modifier.fillMaxWidth().height(60.dp)
            .clip(RoundedCornerShape(18.dp))
            .background(bgGradient)
            .clickable {
                if (isStreaming) {
                    onStop()
                    AppState.isStreaming.value = false
                    AppState.connectionState.value = ConnectionState.DISCONNECTED
                    AppState.serverIP.value = Strings.get("searching")
                } else {
                    onStart()
                    AppState.connectionState.value = ConnectionState.CONNECTING
                }
            },
        contentAlignment = Alignment.Center,
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center,
        ) {
            Icon(
                if (isStreaming) Icons.Default.Stop else Icons.Default.PlayArrow,
                contentDescription = null, tint = Color.White,
                modifier = Modifier.size(26.dp),
            )
            Spacer(modifier = Modifier.width(10.dp))
            Text(
                if (isStreaming) Strings.get("stop") else Strings.get("start"),
                fontSize = 17.sp, fontWeight = FontWeight.ExtraBold,
                color = Color.White, letterSpacing = 1.5.sp,
            )
        }
    }
}

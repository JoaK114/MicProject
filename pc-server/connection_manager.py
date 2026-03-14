"""
MicProject - Connection Manager
Handles WiFi auto-discovery, ADB USB forwarding, and the control channel.
"""

import json
import socket
import subprocess
import threading
import time
import struct


class ConnectionManager:
    """
    Manages connections between PC and phone.
    - WiFi: UDP broadcast for auto-discovery on LAN
    - USB: ADB port forwarding
    - Control channel: TCP for volume sync, mute commands, heartbeat
    """

    DISCOVERY_PORT = 4547
    DISCOVERY_MAGIC = b"MICPROJECT_DISCOVER"
    HEARTBEAT_INTERVAL = 3  # seconds

    def __init__(self, config, audio_output):
        self.config = config
        self.audio_output = audio_output

        self._control_server = None
        self._control_client = None
        self._discovery_thread = None
        self._control_thread = None
        self._heartbeat_thread = None
        self._running = False
        self._connected = False
        self._connection_mode = None  # "wifi" or "usb"
        self._client_ip = None

        # Callbacks
        self.on_connect = None     # func(mode: str, addr: str)
        self.on_disconnect = None  # func()
        self.on_volume_change = None  # func(volume: float)

    def start(self):
        """Start connection manager services."""
        self._running = True

        # Start control channel server
        self._start_control_server()

        # Start WiFi discovery broadcast
        mode = self.config.get("connection", "mode")
        if mode == "wifi":
            self._start_discovery()

        print("[ConnectionManager] Started")

    def stop(self):
        """Stop all connection services."""
        self._running = False
        self.disconnect_client()

        if self._control_server:
            try:
                self._control_server.close()
            except Exception:
                pass
        self._connected = False
        print("[ConnectionManager] Stopped")

    def disconnect_client(self):
        """Send disconnect to phone and close the TCP control socket."""
        if self._control_client:
            # Send disconnect command so the phone knows
            try:
                self.send_control("disconnect")
            except Exception:
                pass
            # Close the TCP socket — phone will get EOF
            try:
                self._control_client.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self._control_client.close()
            except Exception:
                pass
            self._control_client = None

        if self._connected:
            self._connected = False
            if self.on_disconnect:
                self.on_disconnect()

    def setup_adb_forward(self) -> bool:
        """Set up ADB port forwarding for USB connection."""
        port = self.config.get("connection", "port")
        control_port = self.config.get("connection", "control_port")
        try:
            # Forward audio port
            result = subprocess.run(
                ["adb", "forward", f"tcp:{port}", f"tcp:{port}"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                print(f"[ConnectionManager] ADB forward audio failed: {result.stderr}")
                return False

            # Forward control port
            result = subprocess.run(
                ["adb", "forward", f"tcp:{control_port}", f"tcp:{control_port}"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                print(f"[ConnectionManager] ADB forward control failed: {result.stderr}")
                return False

            print(f"[ConnectionManager] ADB forwarding active on ports {port}, {control_port}")
            return True
        except FileNotFoundError:
            print("[ConnectionManager] ADB not found! Install Android SDK Platform Tools.")
            return False
        except subprocess.TimeoutExpired:
            print("[ConnectionManager] ADB command timed out")
            return False

    def remove_adb_forward(self):
        """Remove ADB port forwarding."""
        try:
            subprocess.run(["adb", "forward", "--remove-all"],
                           capture_output=True, timeout=5)
        except Exception:
            pass

    def send_control(self, command: str, data: dict = None):
        """Send a control command to the connected phone."""
        if not self._control_client:
            return
        msg = json.dumps({"cmd": command, "data": data or {}})
        try:
            encoded = msg.encode("utf-8")
            header = struct.pack("!H", len(encoded))
            self._control_client.sendall(header + encoded)
        except Exception:
            pass

    def send_volume(self, volume: float):
        """Send volume update to phone."""
        self.send_control("volume", {"level": volume})

    def send_mute(self, muted: bool):
        """Send mute state to phone."""
        self.send_control("mute", {"muted": muted})

    def get_local_ip(self) -> str:
        """Get the local WiFi/LAN IP address. Prioritizes 192.168.x.x."""
        primary_ip = "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            primary_ip = s.getsockname()[0]
            s.close()
        except Exception:
            pass

        try:
            hostname = socket.gethostname()
            _, _, ips = socket.gethostbyname_ex(hostname)

            # Prioritize 192.168.x.x (most common home routers)
            for addr in ips:
                if addr.startswith("192.168."):
                    return addr
                    
            # Then 10.x.x.x
            for addr in ips:
                if addr.startswith("10."):
                    return addr

            # If default route IP is valid, use it
            if primary_ip != "127.0.0.1" and not primary_ip.startswith("172."):
                return primary_ip

            # Otherwise return first non-loopback
            for addr in ips:
                if not addr.startswith("127."):
                    return addr
        except Exception:
            pass

        return primary_ip

    def _start_discovery(self):
        """Start broadcasting discovery packets on LAN."""
        self._discovery_thread = threading.Thread(target=self._discovery_loop, daemon=True)
        self._discovery_thread.start()

    def _discovery_loop(self):
        """Broadcast discovery packets so the phone can find the PC."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(1.0)

        port = self.config.get("connection", "port")
        control_port = self.config.get("connection", "control_port")
        local_ip = self.get_local_ip()

        discovery_data = json.dumps({
            "magic": self.DISCOVERY_MAGIC.decode(),
            "ip": local_ip,
            "audio_port": port,
            "control_port": control_port,
            "name": socket.gethostname(),
        }).encode("utf-8")

        print(f"[Discovery] Broadcasting on LAN (IP: {local_ip})")

        while self._running:
            try:
                sock.sendto(discovery_data, ("255.255.255.255", self.DISCOVERY_PORT))
            except Exception:
                pass
            time.sleep(2)

        sock.close()

    def _start_control_server(self):
        """Start TCP server for control channel."""
        control_port = self.config.get("connection", "control_port")
        self._control_thread = threading.Thread(target=self._control_loop,
                                                args=(control_port,), daemon=True)
        self._control_thread.start()

    def _control_loop(self, port):
        """Accept and handle control channel connections."""
        try:
            self._control_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._control_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._control_server.bind(("0.0.0.0", port))
            self._control_server.listen(1)
            self._control_server.settimeout(1.0)
            print(f"[Control] Listening on TCP port {port}")
        except Exception as e:
            print(f"[Control] Failed to start: {e}")
            return

        while self._running:
            try:
                client, addr = self._control_server.accept()
                self._control_client = client
                self._client_ip = addr[0]
                self._connected = True
                self._connection_mode = "wifi" if addr[0] != "127.0.0.1" else "usb"

                print(f"[Control] Phone connected: {addr} (mode: {self._connection_mode})")
                if self.on_connect:
                    self.on_connect(self._connection_mode, addr[0])

                self._handle_control_client(client)

            except socket.timeout:
                continue
            except OSError:
                if self._running:
                    time.sleep(0.5)

    def _handle_control_client(self, client: socket.socket):
        """Handle control messages from the phone."""
        client.settimeout(self.HEARTBEAT_INTERVAL * 2)
        buffer = b""

        while self._running:
            try:
                data = client.recv(4096)
                if not data:
                    break

                buffer += data

                while len(buffer) >= 2:
                    msg_len = struct.unpack("!H", buffer[:2])[0]
                    if len(buffer) < 2 + msg_len:
                        break

                    msg_data = buffer[2:2 + msg_len]
                    buffer = buffer[2 + msg_len:]

                    try:
                        msg = json.loads(msg_data.decode("utf-8"))
                        self._process_control_message(msg)
                    except json.JSONDecodeError:
                        pass

            except socket.timeout:
                # No heartbeat received
                print("[Control] Phone connection timed out")
                break
            except OSError:
                break

        self._connected = False
        self._control_client = None
        print("[Control] Phone disconnected")
        if self.on_disconnect:
            self.on_disconnect()

    def _process_control_message(self, msg: dict):
        """Process a control message from the phone."""
        cmd = msg.get("cmd", "")
        data = msg.get("data", {})

        if cmd == "volume":
            volume = float(data.get("level", 1.0))
            self.audio_output.set_volume(volume)
            if self.on_volume_change:
                self.on_volume_change(volume)

        elif cmd == "mute":
            muted = bool(data.get("muted", False))
            self.audio_output.set_mute(muted)

        elif cmd == "heartbeat":
            # Respond with heartbeat ack
            self.send_control("heartbeat_ack")

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def connection_mode(self) -> str | None:
        return self._connection_mode

    @property
    def client_ip(self) -> str | None:
        return self._client_ip

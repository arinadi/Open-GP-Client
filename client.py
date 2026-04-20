"""GPClient — subprocess wrapper around gpclient/gpauth CLI."""

import enum
import errno
import os
import pty
import re
import select
import shutil
import signal
import subprocess
import threading
import logging
import sys
from pathlib import Path

logger = logging.getLogger("open-gp-client.client")

# Regex to strip ANSI escape sequences from terminal output
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b\].*?\x07")


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from a string."""
    return _ANSI_RE.sub("", text).strip()


class VPNState(enum.Enum):
    DISCONNECTED = "disconnected"
    AUTHENTICATING = "authenticating"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    ERROR = "error"


class GPClient:
    """Wraps gpclient/gpauth CLI tools for VPN management."""

    def __init__(self):
        logger.debug("Initializing GPClient instance")
        self._process: subprocess.Popen | None = None
        self._auth_process: subprocess.Popen | None = None
        self._master_fd: int | None = None
        self._state = VPNState.DISCONNECTED
        self._lock = threading.Lock()

        # Find binaries: prefer local bundled ones, fallback to system PATH
        self._bin_dir = Path(__file__).parent.parent / "bin"
        local_gpclient = self._bin_dir / "gpclient"
        local_gpauth = self._bin_dir / "gpauth"

        self._gpclient = str(local_gpclient) if local_gpclient.exists() else shutil.which("gpclient")
        self._gpauth = str(local_gpauth) if local_gpauth.exists() else shutil.which("gpauth")

        if not self._gpclient:
            raise FileNotFoundError("gpclient not found. Bundle it in bin/ or install GlobalProtect-openconnect.")
        if not self._gpauth:
            raise FileNotFoundError("gpauth not found. Bundle it in bin/ or install GlobalProtect-openconnect.")

    @property
    def state(self) -> VPNState:
        return self._state

    def connect_with_auth(
        self,
        server: str,
        browser: str = "default",
        fix_openssl: bool = False,
        ignore_tls_errors: bool = False,
        on_state_change=None,
        on_output=None,
    ):
        """
        Two-step auth flow: gpauth → cookie → gpclient connect --cookie-on-stdin.
        Uses a pseudo-TTY so gpclient sees a real terminal (fixes 'not a TTY' error).
        Runs in the calling thread (caller should use a background thread).
        """

        def _set_state(state: VPNState):
            self._state = state
            if on_state_change:
                on_state_change(state)

        def _log(msg: str):
            if on_output:
                on_output(msg)

        try:
            # Step 1: Authenticate
            # Per official docs: gpauth <portal> --browser 2>/dev/null | sudo gpclient connect <portal> --cookie-on-stdin
            # gpauth writes the COOKIE to stdout, and all log messages to stderr.
            _set_state(VPNState.AUTHENTICATING)
            _log(f"Authenticating to {server}...")

            auth_cmd = [self._gpauth, server]
            if browser and browser != "built-in":
                auth_cmd.extend(["--browser", browser])
            if fix_openssl:
                auth_cmd.append("--fix-openssl")
            if ignore_tls_errors:
                auth_cmd.append("--ignore-tls-errors")

            _log(f"Running: {' '.join(auth_cmd)}")
            logger.debug(f"Executing: {' '.join(auth_cmd)}")

            self._auth_process = subprocess.Popen(
                auth_cmd,
                stdout=subprocess.PIPE,  # Cookie comes out here
                stderr=None,             # Let stderr (logs) print directly to our terminal
                text=True,
                env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")},
            )

            logger.debug("Waiting for gpauth to produce cookie on stdout...")
            # gpauth will exit after writing the cookie to stdout
            cookie_output, _ = self._auth_process.communicate()
            auth_rc = self._auth_process.returncode
            self._auth_process = None

            cookie = cookie_output.strip() if cookie_output else ""
            logger.debug(f"gpauth exit code: {auth_rc}, cookie length: {len(cookie)}")

            if auth_rc != 0 or not cookie:
                logger.error(f"Auth failed. RC={auth_rc}, cookie found={bool(cookie)}")
                _log(f"Authentication failed (exit code {auth_rc}). Check terminal for gpauth logs.")
                _set_state(VPNState.ERROR)
                return

            logger.debug("Auth successful, cookie obtained.")
            _log("Authentication successful. Connecting VPN...")

            # Step 2: Connect via PTY (gpclient needs a TTY)
            _set_state(VPNState.CONNECTING)

            connect_cmd = [
                "pkexec", self._gpclient, "connect", server, "--cookie-on-stdin",
            ]
            if fix_openssl:
                connect_cmd = [
                    "pkexec", self._gpclient, "--fix-openssl",
                    "connect", server, "--cookie-on-stdin",
                ]
            if ignore_tls_errors:
                idx = connect_cmd.index("connect")
                connect_cmd.insert(idx, "--ignore-tls-errors")

            _log(f"Running: {' '.join(connect_cmd)}")

            # Create a pseudo-TTY so gpclient thinks it has a terminal
            master_fd, slave_fd = pty.openpty()
            self._master_fd = master_fd

            self._process = subprocess.Popen(
                connect_cmd,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
            )
            os.close(slave_fd)  # Parent doesn't need the slave side

            # Write cookie through the master (appears on gpclient's stdin)
            os.write(master_fd, (cookie + "\n").encode())

            # Read output from master fd and stream to GUI
            connected = False
            gateway_selected = False
            already_running = False
            buf = b""
            while True:
                try:
                    ready, _, _ = select.select([master_fd], [], [], 1.0)
                    if ready:
                        data = os.read(master_fd, 4096)
                        if not data:
                            break
                        buf += data

                        # Detect gateway selection prompt and auto-select first
                        decoded_buf = buf.decode("utf-8", errors="replace")
                        if not gateway_selected and "which gateway" in decoded_buf.lower():
                            import time
                            time.sleep(0.3)  # Let the prompt fully render
                            os.write(master_fd, b"\n")  # Press Enter = select first
                            gateway_selected = True
                            _log("Auto-selecting first gateway...")

                        while b"\n" in buf:
                            line_bytes, buf = buf.split(b"\n", 1)
                            line = line_bytes.decode("utf-8", errors="replace").rstrip()
                            # Strip ANSI escape codes for clean log
                            clean = _strip_ansi(line)
                            if clean:
                                _log(clean)
                                lower = clean.lower()
                                if ("connected" in lower and "tunnel" in lower) or "established" in lower:
                                    if not connected:
                                        connected = True
                                        _set_state(VPNState.CONNECTED)
                                elif "already running" in lower:
                                    # If another instance is running, we are already connected!
                                    if not connected:
                                        connected = True
                                        already_running = True
                                        _set_state(VPNState.CONNECTED)
                    elif self._process.poll() is not None:
                        # Process exited
                        break
                except OSError as e:
                    if e.errno == errno.EIO:
                        # PTY closed (process exited)
                        break
                    raise

            # Flush remaining buffer
            remaining = buf.decode("utf-8", errors="replace").rstrip()
            if remaining:
                _log(remaining)

            rc = self._process.wait()
            self._close_master()
            self._process = None

            if rc == 0 and connected and not already_running:
                _log("VPN session ended cleanly.")
            elif rc == -signal.SIGTERM or rc == -signal.SIGINT:
                _log("VPN disconnected.")
            elif already_running:
                _log("Attached to existing background VPN session.")
            else:
                _log(f"VPN process exited with code {rc}")

            if not already_running:
                _set_state(VPNState.DISCONNECTED)

        except Exception as e:
            _log(f"Error: {e}")
            _set_state(VPNState.ERROR)

    def _close_master(self):
        """Close the PTY master fd if open."""
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = None

    def disconnect(self, on_output=None):
        """Disconnect the VPN."""
        self._state = VPNState.DISCONNECTING

        def _log(msg: str):
            if on_output:
                on_output(msg)

        try:
            # Kill auth process if running (runs as current user, no pkexec needed)
            if self._auth_process and self._auth_process.poll() is None:
                self._auth_process.terminate()
                self._auth_process = None
                _log("Authentication cancelled.")

            # Send Ctrl+C to the PTY to gracefully terminate gpclient
            # This avoids the need for ANY pkexec password prompts during disconnect!
            if self._process and self._process.poll() is None:
                _log("Sending graceful termination signal...")
                if self._master_fd is not None:
                    try:
                        os.write(self._master_fd, b"\x03")
                    except OSError:
                        pass

                # Wait up to 5 seconds for it to exit cleanly
                try:
                    self._process.wait(timeout=5.0)
                    _log("VPN disconnected gracefully.")
                except subprocess.TimeoutExpired:
                    _log("Graceful termination timed out. Force disconnecting...")
                    # Fallback to pkexec gpclient disconnect
                    subprocess.run(
                        ["pkexec", self._gpclient, "disconnect"],
                        capture_output=True, text=True, timeout=10,
                    )
                    
                    if self._process.poll() is None:
                        # Hard kill if still alive
                        pid = self._process.pid
                        subprocess.run(["pkexec", "kill", "-9", str(pid)], timeout=5, capture_output=True)
                        self._process.wait(timeout=2.0)
                
                self._process = None

            self._close_master()
            _log("Disconnected.")

        except Exception as e:
            _log(f"Disconnect error: {e}")
        finally:
            self._state = VPNState.DISCONNECTED

    def is_connected(self) -> bool:
        """Check if a VPN tunnel appears active."""
        try:
            result = subprocess.run(
                ["ip", "link", "show", "type", "tun"],
                capture_output=True, text=True, timeout=5,
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

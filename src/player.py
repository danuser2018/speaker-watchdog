import json
import logging
import os
import socket
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_MPV_SOCKET_PATH = "/tmp/speaker-watchdog.sock"
_IPC_CONNECT_TIMEOUT = 2.0   # seconds to wait for socket connection
_IPC_SEND_TIMEOUT = 2.0       # seconds to wait for socket send


class MpvDaemonPlayer:
    """
    Manages a persistent mpv process running in daemon mode with a Unix IPC socket.

    Instead of spawning a new mpv process per audio file, this class keeps a single
    mpv instance alive and sends JSON commands over the IPC socket to trigger playback.

    The 'replace' mode ensures any currently playing sound is interrupted immediately
    and replaced by the incoming one — no queue, no waiting.
    """

    def __init__(self, mpv_path: str = "mpv", socket_path: str = _MPV_SOCKET_PATH):
        self.mpv_path = mpv_path
        self.socket_path = socket_path
        self._process: subprocess.Popen | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
        """
        Ensures the mpv daemon is running and the IPC socket is responsive.
        Called once during service initialization.
        """
        logger.info("Initializing mpv daemon player...")
        self._ensure_daemon_running()
        logger.info("mpv daemon player ready.")

    def stop(self):
        """
        Terminates the mpv daemon process and removes the socket file.
        Called during service shutdown.
        """
        logger.info("Stopping mpv daemon player...")
        self._terminate_daemon()
        logger.info("mpv daemon player stopped.")

    def play(self, filepath: Path):
        """
        Sends a 'loadfile ... replace' IPC command to the mpv daemon.

        The file is deleted immediately after the command is accepted by mpv;
        mpv already holds an open file descriptor at that point, so deletion
        is safe and does not interrupt playback on Linux.

        If the IPC socket is unavailable, the daemon is restarted and the
        operation is retried once before giving up.
        """
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}. Skipping playback.")
            return

        logger.info(f"Requesting playback: {filepath.name}")

        success = self._send_loadfile(filepath)

        if not success:
            # Socket was unavailable — daemon has been restarted inside
            # _send_loadfile; retry the command once.
            logger.info(f"Retrying playback after daemon restart: {filepath.name}")
            success = self._send_loadfile(filepath, retry=True)

        # Delete the file regardless of whether playback succeeded, to avoid
        # leaving stale files in the watched directory.
        self._delete_file(filepath)

        if success:
            logger.info(f"Playback command accepted for: {filepath.name}")

    # ------------------------------------------------------------------
    # IPC
    # ------------------------------------------------------------------

    def _send_loadfile(self, filepath: Path, *, retry: bool = False) -> bool:
        """
        Sends the JSON loadfile command to the mpv IPC socket.

        Returns True if the command was sent successfully, False otherwise.
        On failure, attempts to restart the mpv daemon before returning.
        """
        command = json.dumps({"command": ["loadfile", str(filepath), "replace"]}) + "\n"

        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(_IPC_CONNECT_TIMEOUT)
                sock.connect(self.socket_path)
                sock.settimeout(_IPC_SEND_TIMEOUT)
                sock.sendall(command.encode("utf-8"))
            return True

        except FileNotFoundError:
            # The socket file does not exist at all.
            if retry:
                logger.error(
                    f"IPC socket still missing on retry for '{filepath.name}'. "
                    "Giving up on this file."
                )
                return False
            logger.warning(
                f"IPC socket not found at '{self.socket_path}'. "
                "Attempting to restart mpv daemon..."
            )
            self._restart_daemon()
            return False

        except (ConnectionRefusedError, OSError) as exc:
            if retry:
                # Already retried once — log as error and give up.
                logger.error(
                    f"IPC connection failed on retry for '{filepath.name}': {exc}. "
                    "Giving up on this file."
                )
                return False

            logger.error(
                f"IPC connection failed for '{filepath.name}': {exc}. "
                "Restarting mpv daemon..."
            )
            self._restart_daemon()
            return False

    # ------------------------------------------------------------------
    # Daemon lifecycle
    # ------------------------------------------------------------------

    def _ensure_daemon_running(self):
        """
        Checks whether the mpv daemon is alive and responsive.
        Starts a fresh daemon if the socket is missing or not responding.
        """
        if self._is_socket_responsive():
            logger.debug("Existing mpv daemon is responsive. Reusing it.")
            return

        # Socket missing or stale — clean up and start fresh.
        self._remove_stale_socket()
        self._start_daemon()

    def _is_socket_responsive(self) -> bool:
        """Returns True if the IPC socket exists and accepts connections."""
        if not Path(self.socket_path).exists():
            return False

        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(_IPC_CONNECT_TIMEOUT)
                sock.connect(self.socket_path)
            return True
        except (FileNotFoundError, ConnectionRefusedError, OSError):
            return False

    def _start_daemon(self):
        """Launches the mpv process in daemon (idle) mode with IPC socket."""
        cmd = [
            self.mpv_path,
            "--idle=yes",
            "--no-video",
            "--quiet",
            f"--input-ipc-server={self.socket_path}",
        ]
        logger.info(f"Starting mpv daemon: {' '.join(cmd)}")

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                # stderr intentionally not suppressed: mpv errors flow to journald
                # alongside the service logs, making failures diagnosable.
            )
            # Give mpv a moment to create the socket before we try to use it.
            self._wait_for_socket()

            returncode = self._process.poll()
            if returncode is not None:
                logger.error(
                    f"mpv daemon exited prematurely with code {returncode}. "
                    "Check journald output above for mpv error details."
                )
                self._process = None
                raise RuntimeError(
                    f"mpv daemon failed to start (exit code {returncode})."
                )

            logger.info(f"mpv daemon started (PID {self._process.pid}).")
        except FileNotFoundError:
            logger.critical(
                f"Failed to start '{self.mpv_path}'. "
                "Please verify that mpv is installed and available in PATH."
            )
            raise

    def _restart_daemon(self):
        """Terminates the current daemon (if any) and starts a new one."""
        logger.info("Restarting mpv daemon...")
        self._terminate_daemon()
        self._start_daemon()

    def _terminate_daemon(self):
        """Sends SIGTERM to the mpv process and waits for it to exit."""
        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(timeout=5.0)
                logger.info("mpv daemon process terminated.")
            except subprocess.TimeoutExpired:
                logger.warning("mpv daemon did not stop in time; sending SIGKILL.")
                self._process.kill()
                self._process.wait()
            except Exception as exc:
                logger.error(f"Error while terminating mpv daemon: {exc}")
            finally:
                self._process = None

        self._remove_stale_socket()

    def _remove_stale_socket(self):
        """Removes the socket file if it exists, to allow a clean restart."""
        try:
            os.remove(self.socket_path)
            logger.debug(f"Removed stale socket: {self.socket_path}")
        except FileNotFoundError:
            pass  # Nothing to remove — that's fine.
        except OSError as exc:
            logger.warning(f"Could not remove socket '{self.socket_path}': {exc}")

    def _wait_for_socket(self, timeout: float = 5.0, interval: float = 0.1):
        """Blocks until the IPC socket becomes responsive or the timeout expires."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            # Exit early if mpv has already died — no point waiting for its socket.
            if self._process is not None and self._process.poll() is not None:
                logger.error(
                    f"mpv process exited with code {self._process.returncode} "
                    "before the IPC socket became available."
                )
                return
            if self._is_socket_responsive():
                return
            time.sleep(interval)

        logger.warning(
            f"mpv daemon socket did not become responsive within {timeout}s."
        )

    # ------------------------------------------------------------------
    # File management
    # ------------------------------------------------------------------

    def _delete_file(self, filepath: Path):
        """Removes the audio file from disk after the IPC command has been sent."""
        try:
            filepath.unlink(missing_ok=True)
            logger.info(f"Deleted file from disk: {filepath.name}")
        except Exception as exc:
            logger.error(f"Failed to delete file '{filepath}': {exc}")

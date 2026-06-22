import logging
import subprocess
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


class MpvPlayer:
    """
    Plays audio files using mpv with "last sound wins" semantics.

    Each call to play() immediately stops any ongoing playback and starts the
    new file. No IPC socket, no FIFO, no daemon process required.

    A lock serializes concurrent calls from the filesystem watcher thread.
    """

    def __init__(self, mpv_path: str = "mpv"):
        self.mpv_path = mpv_path
        self._current: subprocess.Popen | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
        """Called during service initialization."""
        logger.info("MpvPlayer ready (process-per-file, last sound wins).")

    def stop(self):
        """Terminates any ongoing playback during service shutdown."""
        logger.info("Stopping MpvPlayer...")
        with self._lock:
            self._terminate_current()
        logger.info("MpvPlayer stopped.")

    def play(self, filepath: Path):
        """
        Plays the given audio file, stopping any currently playing audio first.

        The file is deleted immediately after mpv opens it. On Linux an open
        file descriptor survives unlink, so playback continues uninterrupted.
        """
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}. Skipping playback.")
            return

        logger.info(f"Requesting playback: {filepath.name}")

        with self._lock:
            self._terminate_current()
            self._start_playback(filepath)

        # Delete outside the lock: file is already open by mpv.
        self._delete_file(filepath)

    # ------------------------------------------------------------------
    # Internal playback management
    # ------------------------------------------------------------------

    def _start_playback(self, filepath: Path):
        """Launches a new mpv process for the given file. Must hold _lock."""
        cmd = [self.mpv_path, "--no-video", "--quiet", str(filepath)]
        logger.debug(f"Spawning: {' '.join(cmd)}")

        try:
            self._current = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info(f"Playback started (PID {self._current.pid}): {filepath.name}")
        except FileNotFoundError:
            logger.critical(
                f"Failed to execute '{self.mpv_path}'. "
                "Please verify that mpv is installed and available in PATH."
            )
            self._current = None

    def _terminate_current(self):
        """Stops the current mpv process if one is running. Must hold _lock."""
        if self._current is None:
            return

        if self._current.poll() is not None:
            self._current = None
            return

        logger.info(f"Stopping current playback (PID {self._current.pid}).")
        try:
            self._current.terminate()
            self._current.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            logger.warning(f"mpv PID {self._current.pid} did not stop; sending SIGKILL.")
            self._current.kill()
            self._current.wait()
        finally:
            self._current = None

    # ------------------------------------------------------------------
    # File management
    # ------------------------------------------------------------------

    def _delete_file(self, filepath: Path):
        """Removes the audio file from disk after mpv has opened it."""
        try:
            filepath.unlink(missing_ok=True)
            logger.info(f"Deleted file from disk: {filepath.name}")
        except Exception as exc:
            logger.error(f"Failed to delete file '{filepath}': {exc}")

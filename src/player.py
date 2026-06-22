import logging
import subprocess
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


class MpvPlayer:
    """
    Plays audio files using mpv with "last sound wins" semantics.

    Each call to play() immediately stops any ongoing playback and starts the
    new file. The audio file is deleted only after mpv exits, avoiding the race
    condition where the file is unlinked before mpv has opened it.
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

        File deletion is deferred to a background thread that waits for mpv to
        exit. This avoids the race condition where the file is unlinked before
        mpv has had time to open it (Popen returns before the child process
        executes its first instruction).
        """
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}. Skipping playback.")
            return

        logger.info(f"Requesting playback: {filepath.name}")

        with self._lock:
            self._terminate_current()
            process = self._start_playback(filepath)
            self._current = process

        if process is not None:
            threading.Thread(
                target=self._wait_and_delete,
                args=(process, filepath),
                daemon=True,
                name=f"MpvWaiter-{filepath.name}",
            ).start()

    # ------------------------------------------------------------------
    # Internal playback management
    # ------------------------------------------------------------------

    def _start_playback(self, filepath: Path) -> "subprocess.Popen | None":
        """Launches a new mpv process. Must hold _lock."""
        cmd = [self.mpv_path, "--no-video", "--quiet", str(filepath)]
        logger.debug(f"Spawning: {' '.join(cmd)}")
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info(f"Playback started (PID {process.pid}): {filepath.name}")
            return process
        except FileNotFoundError:
            logger.critical(
                f"Failed to execute '{self.mpv_path}'. "
                "Please verify that mpv is installed and available in PATH."
            )
            return None

    def _wait_and_delete(self, process: subprocess.Popen, filepath: Path):
        """
        Waits for mpv to exit, then deletes the audio file.

        Deferring deletion here (rather than immediately after Popen) ensures
        that mpv has already opened the file before we unlink it. On Linux an
        open file descriptor survives unlink, so if we delete while mpv is
        playing, playback continues uninterrupted. But if we delete before mpv
        opens the file, mpv finds nothing and exits silently.
        """
        try:
            process.wait()
        except Exception:
            pass
        self._delete_file(filepath)

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
        """Removes the audio file from disk after mpv has exited."""
        try:
            filepath.unlink(missing_ok=True)
            logger.info(f"Deleted file from disk: {filepath.name}")
        except Exception as exc:
            logger.error(f"Failed to delete file '{filepath}': {exc}")

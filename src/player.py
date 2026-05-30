import queue
import subprocess
import threading
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class AudioPlayerWorker:
    """
    Worker class that runs a background thread to consume audio files from a Queue,
    plays them sequentially using the 'mpv' player, and deletes them immediately after.
    """
    def __init__(self, audio_queue: queue.Queue, mpv_path: str = "mpv"):
        self.queue = audio_queue
        self.mpv_path = mpv_path
        self._thread = None
        self._stop_event = threading.Event()

    def start(self):
        """Starts the background worker thread."""
        if self._thread is not None:
            logger.warning("Audio player worker thread is already running.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="AudioPlayerWorkerThread", daemon=True)
        self._thread.start()
        logger.info("Audio player worker thread started successfully.")

    def stop(self):
        """Signals the worker thread to stop and waits for it to exit."""
        logger.info("Stopping audio player worker thread...")
        self._stop_event.set()
        
        # Enqueue None as a sentinel value to unblock the get() call
        self.queue.put(None)
        
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                logger.warning("Audio player worker thread did not terminate within timeout.")
            else:
                logger.info("Audio player worker thread stopped cleanly.")
            self._thread = None

    def _run(self):
        """Main loop of the worker thread."""
        while not self._stop_event.is_set():
            try:
                # Wait for a new audio file path with a short timeout to check stop_event regularly
                filepath = self.queue.get(block=True, timeout=1.0)
            except queue.Empty:
                continue

            # Check for termination sentinel
            if filepath is None:
                self.queue.task_done()
                break

            try:
                self._process_file(filepath)
            except Exception as e:
                logger.exception(f"Unhandled exception while processing file '{filepath}': {e}")
            finally:
                self.queue.task_done()

    def _process_file(self, filepath: Path):
        """Plays the audio file and ensures its deletion afterwards."""
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}. Skipping playback.")
            return

        logger.info(f"Starting playback: {filepath.name}")
        
        # 1. Play the audio using mpv
        try:
            # --no-video disables any video window
            # --quiet minimizes console output
            cmd = [self.mpv_path, "--no-video", "--quiet", str(filepath)]
            logger.debug(f"Running command: {' '.join(cmd)}")
            
            # Execute synchronously to avoid overlapping playback
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            
            if result.returncode == 0:
                logger.info(f"Playback finished successfully: {filepath.name}")
            else:
                logger.error(
                    f"mpv exited with code {result.returncode} for '{filepath.name}'. "
                    f"stderr: {result.stderr.strip()}"
                )
        except FileNotFoundError:
            logger.critical(
                f"Failed to execute '{self.mpv_path}'. "
                "Please verify that mpv is installed and added to the PATH."
            )
        except Exception as e:
            logger.error(f"Error executing playback for '{filepath.name}': {e}")

        # 2. Delete the file from disk (even if playback failed)
        try:
            filepath.unlink(missing_ok=True)
            logger.info(f"Deleted file from disk: {filepath.name}")
        except Exception as e:
            logger.error(f"Failed to delete file '{filepath}': {e}")

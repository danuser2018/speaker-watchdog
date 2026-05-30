import time
import queue
import logging
from pathlib import Path
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

class AudioFolderHandler(FileSystemEventHandler):
    """
    Reactive filesystem event handler that monitors file creation and rename/move events.
    Filters for '.wav' files and verifies file stability before queuing them.
    """
    def __init__(self, audio_queue: queue.Queue, stability_timeout: float = 5.0):
        super().__init__()
        self.queue = audio_queue
        self.stability_timeout = stability_timeout

    def on_created(self, event):
        """Triggered when a file or directory is created in the watched folder."""
        if event.is_directory:
            return
        
        filepath = Path(event.src_path).resolve()
        logger.debug(f"File creation detected: {filepath}")
        self._process_detected_file(filepath)

    def on_moved(self, event):
        """Triggered when a file or directory is renamed or moved within the watched folder."""
        if event.is_directory:
            return
        
        filepath = Path(event.dest_path).resolve()
        logger.debug(f"File move/rename detected: {filepath}")
        self._process_detected_file(filepath)

    def _process_detected_file(self, filepath: Path):
        """Filters, stabilizes, and enqueues the detected file path."""
        # 1. Filter by .wav extension (case-insensitive)
        if filepath.suffix.lower() != ".wav":
            logger.debug(f"Ignoring non-WAV file: {filepath.name}")
            return

        logger.info(f"New WAV file detected: {filepath.name}. Stabilizing...")

        # 2. Wait for the file to be fully written and closed by the writer
        if self._wait_for_file_ready(filepath):
            logger.info(f"File stable and ready. Adding to playback queue: {filepath.name}")
            self.queue.put(filepath)
        else:
            logger.warning(
                f"File '{filepath.name}' did not stabilize or become readable "
                f"within {self.stability_timeout} seconds. Skipping."
            )

    def _wait_for_file_ready(self, filepath: Path) -> bool:
        """
        Waits for the file size to stabilize over short intervals and ensures the file is
        readable (fully written). This prevents playing incomplete or locked files.
        """
        start_time = time.time()
        last_size = -1

        while time.time() - start_time < self.stability_timeout:
            if not filepath.exists():
                logger.debug(f"File disappeared during stabilization: {filepath.name}")
                return False

            try:
                current_size = filepath.stat().st_size
                
                # Check if size has stabilized and is greater than 0
                if current_size == last_size and current_size > 0:
                    # Attempt an exclusive check: try opening the file for reading
                    with open(filepath, 'rb'):
                        pass
                    return True
                
                last_size = current_size
            except (OSError, PermissionError) as e:
                # File might be locked or permission denied temporarily while being written
                logger.debug(f"Temporary file access error for {filepath.name}: {e}")
                pass

            time.sleep(0.1)

        return False

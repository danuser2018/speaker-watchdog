import sys
import time
import signal
import logging
from pathlib import Path

# Add the 'src' directory to the Python path to support all execution formats
src_dir = Path(__file__).resolve().parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Import watchdog observer
from watchdog.observers import Observer

# Import local modules
from config import Config
from player import MpvPlayer
from watcher import AudioFolderHandler

def main():
    # 1. Load configuration
    try:
        config = Config()
    except Exception as e:
        # Standard fallback format if config fails to load or directory cannot be created
        logging.basicConfig(level=logging.ERROR)
        logging.critical(f"Failed to load service configuration: {e}")
        sys.exit(1)

    # 2. Configure system-wide logging
    # Outputs directly to sys.stdout so systemd journald captures it seamlessly
    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger("speaker-watchdog")
    logger.info("Initializing speaker-watchdog service...")
    logger.info(f"Loaded Configuration: {config}")

    # 3. Initialize and Start the mpv Player
    player = MpvPlayer(mpv_path=config.mpv_path)
    try:
        player.start()
    except Exception as e:
        logger.critical(f"Failed to start mpv player: {e}")
        sys.exit(1)

    # 4. Initialize and Start Filesystem Watcher Observer
    handler = AudioFolderHandler(player=player)
    observer = Observer()
    observer.schedule(handler, path=str(config.watch_dir), recursive=False)
    
    try:
        observer.start()
        logger.info(f"Filesystem observer started on directory: {config.watch_dir}")
    except Exception as e:
        logger.critical(f"Failed to start watchdog observer on '{config.watch_dir}': {e}")
        player.stop()
        sys.exit(1)

    # 5. Graceful Shutdown Signal Handlers
    running = True

    def signal_handler(signum, frame):
        nonlocal running
        sig_name = signal.Signals(signum).name
        logger.info(f"Received signal {sig_name} ({signum}). Initiating graceful shutdown...")
        running = False

    # Register systemd standard termination signals
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Service is up and running. Waiting for events...")

    # 6. Main Loop Keep-Alive
    try:
        while running:
            time.sleep(0.2)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt detected. Initiating graceful shutdown...")
    finally:
        # 7. Clean Resource Cleanup
        logger.info("Stopping filesystem observer...")
        observer.stop()
        observer.join()
        logger.info("Filesystem observer stopped.")

        logger.info("Stopping mpv player...")
        player.stop()
        logger.info("mpv player stopped.")

        logger.info("Service shutdown procedure completed successfully. Exiting.")

if __name__ == "__main__":
    main()

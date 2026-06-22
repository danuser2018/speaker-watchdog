import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Set up logging for configuration loading phase
logger = logging.getLogger(__name__)

class Config:
    """
    Configuration class to load, validate, and store application settings
    from environment variables and local .env files.
    """
    def __init__(self):
        # Load dotenv file if present in the current working directory or parent
        load_dotenv()

        # 1. Watch directory configuration
        watch_dir_env = os.getenv("WATCHDOG_DIR")
        if not watch_dir_env:
            # Fallback to a default directory in the workspace for testing
            default_path = Path(__file__).resolve().parent.parent / "alerts"
            logger.warning(
                f"WATCHDOG_DIR env var is not set. Falling back to default: {default_path}"
            )
            self.watch_dir = default_path
        else:
            self.watch_dir = Path(watch_dir_env).resolve()

        # Ensure the watch directory exists
        try:
            self.watch_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Monitoring folder successfully initialized: {self.watch_dir}")
        except Exception as e:
            logger.critical(
                f"Failed to create or access watch directory '{self.watch_dir}': {e}"
            )
            raise RuntimeError(f"Cannot access watch directory: {e}") from e

        # 2. Log level configuration
        log_level_env = os.getenv("LOG_LEVEL", "INFO").upper()
        # Map string log level to standard logging constants
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        self.log_level = level_map.get(log_level_env, logging.INFO)

        # 3. MPV executable path
        self.mpv_path = os.getenv("MPV_PATH", "mpv")

        # 4. MPV IPC socket path
        # Best practice for systemd --user services: use XDG_RUNTIME_DIR
        # (/run/user/<uid>) which is guaranteed to be accessible to all child
        # processes of the service. Fallback to /tmp for non-systemd environments.
        xdg_runtime = os.getenv("XDG_RUNTIME_DIR", "")
        default_socket = (
            str(Path(xdg_runtime) / "speaker-watchdog.sock")
            if xdg_runtime
            else "/tmp/speaker-watchdog.sock"
        )
        self.mpv_socket_path = os.getenv("MPV_SOCKET_PATH", default_socket)

    def __repr__(self):
        return (
            f"Config(watch_dir={self.watch_dir}, "
            f"log_level={logging.getLevelName(self.log_level)}, "
            f"mpv_path='{self.mpv_path}', "
            f"mpv_socket_path='{self.mpv_socket_path}')"
        )

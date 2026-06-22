import json
import socket
import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from src.player import MpvDaemonPlayer


class TestMpvDaemonPlayerPlay(unittest.TestCase):
    """Tests for the play() public method."""

    def setUp(self):
        self.player = MpvDaemonPlayer(mpv_path="mpv", socket_path="/tmp/test-watchdog.sock")

    @patch("src.player.MpvDaemonPlayer._delete_file")
    @patch("src.player.MpvDaemonPlayer._send_loadfile")
    @patch("src.player.Path.exists")
    def test_play_sends_ipc_command_and_deletes_file(
        self, mock_exists, mock_send, mock_delete
    ):
        """Tests that play() sends IPC command and deletes the file on success."""
        mock_exists.return_value = True
        mock_send.return_value = True
        test_file = Path("/watched/folder/alert.wav")

        self.player.play(test_file)

        mock_send.assert_called_once_with(test_file)
        mock_delete.assert_called_once_with(test_file)

    @patch("src.player.MpvDaemonPlayer._delete_file")
    @patch("src.player.MpvDaemonPlayer._send_loadfile")
    @patch("src.player.Path.exists")
    def test_play_file_not_exists_skips_everything(
        self, mock_exists, mock_send, mock_delete
    ):
        """Tests that play() skips IPC and deletion when the file does not exist."""
        mock_exists.return_value = False
        test_file = Path("/watched/folder/missing.wav")

        self.player.play(test_file)

        mock_send.assert_not_called()
        mock_delete.assert_not_called()

    @patch("src.player.MpvDaemonPlayer._delete_file")
    @patch("src.player.MpvDaemonPlayer._send_loadfile")
    @patch("src.player.Path.exists")
    def test_play_retries_after_failed_send(
        self, mock_exists, mock_send, mock_delete
    ):
        """
        Tests that play() retries _send_loadfile with retry=True when the first
        attempt fails (e.g., socket was temporarily unavailable).
        """
        mock_exists.return_value = True
        # First call fails, second call (retry) succeeds
        mock_send.side_effect = [False, True]
        test_file = Path("/watched/folder/alert.wav")

        self.player.play(test_file)

        self.assertEqual(mock_send.call_count, 2)
        mock_send.assert_any_call(test_file)
        mock_send.assert_any_call(test_file, retry=True)
        # File must still be deleted even after a retry
        mock_delete.assert_called_once_with(test_file)

    @patch("src.player.MpvDaemonPlayer._delete_file")
    @patch("src.player.MpvDaemonPlayer._send_loadfile")
    @patch("src.player.Path.exists")
    def test_play_deletes_file_even_when_ipc_fails(
        self, mock_exists, mock_send, mock_delete
    ):
        """
        Tests that the file is always deleted even if both IPC attempts fail,
        to avoid leaving stale files in the watched directory.
        """
        mock_exists.return_value = True
        mock_send.return_value = False
        test_file = Path("/watched/folder/alert.wav")

        self.player.play(test_file)

        mock_delete.assert_called_once_with(test_file)


class TestMpvDaemonPlayerSendLoadfile(unittest.TestCase):
    """Tests for the _send_loadfile() internal method."""

    def setUp(self):
        self.player = MpvDaemonPlayer(mpv_path="mpv", socket_path="/tmp/test-watchdog.sock")

    @patch("src.player.socket.socket")
    def test_send_loadfile_sends_correct_json(self, mock_socket_cls):
        """Tests that _send_loadfile sends the correct JSON command over the socket."""
        mock_sock = MagicMock()
        mock_socket_cls.return_value.__enter__.return_value = mock_sock
        test_file = Path("/watched/folder/alert.wav")

        result = self.player._send_loadfile(test_file)

        self.assertTrue(result)
        expected_payload = (
            json.dumps({"command": ["loadfile", str(test_file), "replace"]}) + "\n"
        ).encode("utf-8")
        mock_sock.sendall.assert_called_once_with(expected_payload)

    @patch("src.player.MpvDaemonPlayer._restart_daemon")
    @patch("src.player.socket.socket")
    def test_send_loadfile_socket_missing_triggers_restart(
        self, mock_socket_cls, mock_restart
    ):
        """Tests that a missing socket file triggers a daemon restart."""
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = FileNotFoundError("No such file")
        mock_socket_cls.return_value.__enter__.return_value = mock_sock
        test_file = Path("/watched/folder/alert.wav")

        result = self.player._send_loadfile(test_file)

        self.assertFalse(result)
        mock_restart.assert_called_once()

    @patch("src.player.MpvDaemonPlayer._restart_daemon")
    @patch("src.player.socket.socket")
    def test_send_loadfile_connection_refused_triggers_restart(
        self, mock_socket_cls, mock_restart
    ):
        """Tests that a refused connection triggers a daemon restart."""
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = ConnectionRefusedError("Connection refused")
        mock_socket_cls.return_value.__enter__.return_value = mock_sock
        test_file = Path("/watched/folder/alert.wav")

        result = self.player._send_loadfile(test_file)

        self.assertFalse(result)
        mock_restart.assert_called_once()

    @patch("src.player.MpvDaemonPlayer._restart_daemon")
    @patch("src.player.socket.socket")
    def test_send_loadfile_socket_missing_on_retry_does_not_restart(
        self, mock_socket_cls, mock_restart
    ):
        """
        Tests that a missing socket on a retry attempt gives up without restarting
        the daemon again, avoiding an infinite restart loop.
        """
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = FileNotFoundError("No such file")
        mock_socket_cls.return_value.__enter__.return_value = mock_sock
        test_file = Path("/watched/folder/alert.wav")

        result = self.player._send_loadfile(test_file, retry=True)

        self.assertFalse(result)
        mock_restart.assert_not_called()

    @patch("src.player.MpvDaemonPlayer._restart_daemon")
    @patch("src.player.socket.socket")
    def test_send_loadfile_retry_does_not_restart_again(
        self, mock_socket_cls, mock_restart
    ):
        """
        Tests that on a retry attempt that also fails with a connection error,
        the daemon is NOT restarted again (giving up gracefully).
        """
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = ConnectionRefusedError("Connection refused")
        mock_socket_cls.return_value.__enter__.return_value = mock_sock
        test_file = Path("/watched/folder/alert.wav")

        result = self.player._send_loadfile(test_file, retry=True)

        self.assertFalse(result)
        mock_restart.assert_not_called()


class TestMpvDaemonPlayerLifecycle(unittest.TestCase):
    """Tests for daemon start/stop lifecycle."""

    def setUp(self):
        self.player = MpvDaemonPlayer(mpv_path="mpv", socket_path="/tmp/test-watchdog.sock")

    @patch("src.player.MpvDaemonPlayer._ensure_daemon_running")
    def test_start_calls_ensure_daemon_running(self, mock_ensure):
        """Tests that start() delegates to _ensure_daemon_running."""
        self.player.start()
        mock_ensure.assert_called_once()

    @patch("src.player.MpvDaemonPlayer._terminate_daemon")
    def test_stop_calls_terminate_daemon(self, mock_terminate):
        """Tests that stop() delegates to _terminate_daemon."""
        self.player.stop()
        mock_terminate.assert_called_once()

    @patch("src.player.MpvDaemonPlayer._start_daemon")
    @patch("src.player.MpvDaemonPlayer._is_socket_responsive")
    def test_ensure_daemon_starts_if_socket_not_responsive(
        self, mock_responsive, mock_start
    ):
        """Tests that _ensure_daemon_running starts a new daemon if socket is unresponsive."""
        mock_responsive.return_value = False

        self.player._ensure_daemon_running()

        mock_start.assert_called_once()

    @patch("src.player.MpvDaemonPlayer._start_daemon")
    @patch("src.player.MpvDaemonPlayer._is_socket_responsive")
    def test_ensure_daemon_reuses_existing_if_responsive(
        self, mock_responsive, mock_start
    ):
        """Tests that _ensure_daemon_running reuses an existing responsive daemon."""
        mock_responsive.return_value = True

        self.player._ensure_daemon_running()

        mock_start.assert_not_called()

    @patch("src.player.MpvDaemonPlayer._wait_for_socket")
    @patch("src.player.subprocess.Popen")
    def test_start_daemon_launches_correct_command(self, mock_popen, mock_wait):
        """Tests that _start_daemon launches mpv with the expected arguments."""
        mock_process = MagicMock()
        mock_process.pid = 42
        mock_process.poll.return_value = None  # process is still alive
        # Provide an iterable stderr so the logging thread terminates cleanly.
        mock_process.stderr.readline.return_value = b""
        mock_popen.return_value = mock_process

        self.player._start_daemon()

        mock_popen.assert_called_once_with(
            [
                "mpv",
                "--idle=yes",
                "--no-video",
                "--quiet",
                f"--input-ipc-server={self.player.socket_path}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

    @patch("src.player.MpvDaemonPlayer._wait_for_socket")
    @patch("src.player.subprocess.Popen")
    def test_start_daemon_raises_if_process_exits_early(self, mock_popen, mock_wait):
        """Tests that _start_daemon raises RuntimeError if mpv exits before the socket is ready."""
        mock_process = MagicMock()
        mock_process.pid = 42
        mock_process.returncode = 1
        mock_process.poll.return_value = 1  # process already dead
        mock_process.stderr.readline.return_value = b""
        mock_popen.return_value = mock_process

        with self.assertRaises(RuntimeError):
            self.player._start_daemon()

        self.assertIsNone(self.player._process)

    def test_terminate_daemon_sends_sigterm(self):
        """Tests that _terminate_daemon calls terminate() and wait() on the process."""
        mock_process = MagicMock()
        self.player._process = mock_process

        with patch("src.player.MpvDaemonPlayer._remove_stale_socket"):
            self.player._terminate_daemon()

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()
        self.assertIsNone(self.player._process)

    def test_terminate_daemon_kills_on_timeout(self):
        """Tests that _terminate_daemon sends SIGKILL if terminate() times out."""
        mock_process = MagicMock()
        # First call to wait(timeout=5.0) raises TimeoutExpired; second call after kill() returns normally.
        mock_process.wait.side_effect = [subprocess.TimeoutExpired(cmd="mpv", timeout=5), None]
        self.player._process = mock_process

        with patch("src.player.MpvDaemonPlayer._remove_stale_socket"):
            self.player._terminate_daemon()

        mock_process.kill.assert_called_once()
        self.assertIsNone(self.player._process)


if __name__ == "__main__":
    unittest.main()

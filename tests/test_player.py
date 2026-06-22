import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.player import MpvPlayer


class TestMpvPlayerPlay(unittest.TestCase):
    """Tests for the play() public method."""

    def setUp(self):
        self.player = MpvPlayer(mpv_path="mpv")

    @patch("src.player.threading.Thread")
    @patch("src.player.MpvPlayer._start_playback")
    @patch("src.player.MpvPlayer._terminate_current")
    @patch("src.player.Path.exists")
    def test_play_terminates_current_starts_new_and_spawns_waiter_thread(
        self, mock_exists, mock_terminate, mock_start, mock_thread_cls
    ):
        """Tests that play() terminates current, starts mpv and spawns a waiter thread."""
        mock_exists.return_value = True
        mock_start.return_value = MagicMock()
        test_file = Path("/watched/folder/alert.wav")

        self.player.play(test_file)

        mock_terminate.assert_called_once()
        mock_start.assert_called_once_with(test_file)
        mock_thread_cls.assert_called_once()
        mock_thread_cls.return_value.start.assert_called_once()

    @patch("src.player.MpvPlayer._start_playback")
    @patch("src.player.Path.exists")
    def test_play_file_not_exists_skips_everything(self, mock_exists, mock_start):
        """Tests that play() does nothing when the file does not exist."""
        mock_exists.return_value = False
        self.player.play(Path("/watched/folder/missing.wav"))
        mock_start.assert_not_called()

    @patch("src.player.threading.Thread")
    @patch("src.player.MpvPlayer._start_playback")
    @patch("src.player.MpvPlayer._terminate_current")
    @patch("src.player.Path.exists")
    def test_play_no_thread_if_mpv_not_found(
        self, mock_exists, mock_terminate, mock_start, mock_thread_cls
    ):
        """Tests that no waiter thread is created if mpv could not be started."""
        mock_exists.return_value = True
        mock_start.return_value = None  # FileNotFoundError inside _start_playback
        self.player.play(Path("/watched/folder/alert.wav"))
        mock_thread_cls.assert_not_called()


class TestMpvPlayerWaitAndDelete(unittest.TestCase):
    """Tests for the _wait_and_delete() method (deferred file deletion)."""

    def setUp(self):
        self.player = MpvPlayer(mpv_path="mpv")

    def test_waits_for_process_then_deletes(self):
        """Tests that _wait_and_delete blocks on process.wait() then deletes the file."""
        mock_process = MagicMock()
        test_file = Path("/watched/folder/alert.wav")

        with patch.object(self.player, "_delete_file") as mock_delete:
            self.player._wait_and_delete(mock_process, test_file)

        mock_process.wait.assert_called_once()
        mock_delete.assert_called_once_with(test_file)

    def test_deletes_even_if_wait_raises(self):
        """Tests that the file is always deleted even if process.wait() raises."""
        mock_process = MagicMock()
        mock_process.wait.side_effect = Exception("unexpected error")
        test_file = Path("/watched/folder/alert.wav")

        with patch.object(self.player, "_delete_file") as mock_delete:
            self.player._wait_and_delete(mock_process, test_file)

        mock_delete.assert_called_once_with(test_file)


class TestMpvPlayerStartPlayback(unittest.TestCase):
    """Tests for the _start_playback() internal method."""

    def setUp(self):
        self.player = MpvPlayer(mpv_path="mpv")

    @patch("src.player.subprocess.Popen")
    def test_spawns_correct_command(self, mock_popen):
        """Tests that _start_playback launches mpv with the expected arguments."""
        mock_process = MagicMock()
        mock_process.pid = 42
        mock_popen.return_value = mock_process
        test_file = Path("/watched/folder/alert.wav")

        result = self.player._start_playback(test_file)

        mock_popen.assert_called_once_with(
            ["mpv", "--no-video", "--quiet", str(test_file)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.assertEqual(result, mock_process)

    @patch("src.player.subprocess.Popen")
    def test_returns_none_when_mpv_not_found(self, mock_popen):
        """Tests that _start_playback returns None when mpv is not installed."""
        mock_popen.side_effect = FileNotFoundError("mpv not found")
        result = self.player._start_playback(Path("/watched/folder/alert.wav"))
        self.assertIsNone(result)


class TestMpvPlayerTerminateCurrent(unittest.TestCase):
    """Tests for the _terminate_current() internal method."""

    def setUp(self):
        self.player = MpvPlayer(mpv_path="mpv")

    def test_no_process_is_noop(self):
        """Tests that _terminate_current does nothing when no process is running."""
        self.player._current = None
        self.player._terminate_current()  # Must not raise

    def test_already_finished_clears_reference(self):
        """Tests that a naturally finished process just clears the reference."""
        mock_process = MagicMock()
        mock_process.poll.return_value = 0
        self.player._current = mock_process

        self.player._terminate_current()

        mock_process.terminate.assert_not_called()
        self.assertIsNone(self.player._current)

    def test_sends_sigterm_to_running_process(self):
        """Tests that a running process receives SIGTERM."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        self.player._current = mock_process

        self.player._terminate_current()

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()
        self.assertIsNone(self.player._current)

    def test_sends_sigkill_on_timeout(self):
        """Tests that SIGKILL is sent if terminate() times out."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="mpv", timeout=2),
            None,
        ]
        self.player._current = mock_process

        self.player._terminate_current()

        mock_process.kill.assert_called_once()
        self.assertIsNone(self.player._current)


class TestMpvPlayerLifecycle(unittest.TestCase):
    """Tests for start() and stop() lifecycle methods."""

    def setUp(self):
        self.player = MpvPlayer(mpv_path="mpv")

    def test_start_is_noop(self):
        """Tests that start() completes without errors."""
        self.player.start()
        self.assertIsNone(self.player._current)

    @patch("src.player.MpvPlayer._terminate_current")
    def test_stop_terminates_current(self, mock_terminate):
        """Tests that stop() calls _terminate_current."""
        self.player.stop()
        mock_terminate.assert_called_once()


if __name__ == "__main__":
    unittest.main()

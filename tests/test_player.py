import queue
import subprocess
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.player import AudioPlayerWorker

class TestAudioPlayerWorker(unittest.TestCase):
    def setUp(self):
        self.audio_queue = queue.Queue()
        self.worker = AudioPlayerWorker(audio_queue=self.audio_queue, mpv_path="mpv")

    def tearDown(self):
        # Ensure thread stops after each test to prevent resource leaks
        self.worker.stop()

    @patch("src.player.subprocess.run")
    @patch("src.player.Path.exists")
    @patch("src.player.Path.unlink")
    def test_process_file_success(self, mock_unlink, mock_exists, mock_run):
        """Tests that a file is played and then unlinked on successful playback."""
        # Arrange
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)
        test_file = Path("/dummy/path/sound.wav")

        # Act
        self.worker._process_file(test_file)

        # Assert
        mock_exists.assert_called_once()
        mock_run.assert_called_once_with(
            ["mpv", "--no-video", "--quiet", str(test_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        mock_unlink.assert_called_once_with(missing_ok=True)

    @patch("src.player.Path.exists")
    @patch("src.player.subprocess.run")
    @patch("src.player.Path.unlink")
    def test_process_file_not_exist(self, mock_unlink, mock_run, mock_exists):
        """Tests that playback and unlinking are skipped if the file does not exist."""
        # Arrange
        mock_exists.return_value = False
        test_file = Path("/dummy/path/nonexistent.wav")

        # Act
        self.worker._process_file(test_file)

        # Assert
        mock_exists.assert_called_once()
        mock_run.assert_not_called()
        mock_unlink.assert_not_called()

    @patch("src.player.subprocess.run")
    @patch("src.player.Path.exists")
    @patch("src.player.Path.unlink")
    def test_process_file_playback_fails(self, mock_unlink, mock_exists, mock_run):
        """Tests that the file is still deleted even if mpv returns a non-zero exit code."""
        # Arrange
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=1, stderr="Failed to parse header")
        test_file = Path("/dummy/path/corrupt.wav")

        # Act
        self.worker._process_file(test_file)

        # Assert
        mock_exists.assert_called_once()
        mock_run.assert_called_once()
        mock_unlink.assert_called_once_with(missing_ok=True)

    @patch("src.player.subprocess.run")
    @patch("src.player.Path.exists")
    @patch("src.player.Path.unlink")
    def test_process_file_mpv_missing(self, mock_unlink, mock_exists, mock_run):
        """Tests that the file is still deleted even if the mpv command is not found on the system."""
        # Arrange
        mock_exists.return_value = True
        mock_run.side_effect = FileNotFoundError("mpv not found")
        test_file = Path("/dummy/path/alert.wav")

        # Act
        self.worker._process_file(test_file)

        # Assert
        mock_exists.assert_called_once()
        mock_run.assert_called_once()
        mock_unlink.assert_called_once_with(missing_ok=True)

if __name__ == "__main__":
    unittest.main()

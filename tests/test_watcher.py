import queue
import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from watchdog.events import FileCreatedEvent, FileMovedEvent

from src.watcher import AudioFolderHandler

class TestAudioFolderHandler(unittest.TestCase):
    def setUp(self):
        self.audio_queue = queue.Queue()
        # Set a short timeout for tests
        self.handler = AudioFolderHandler(audio_queue=self.audio_queue, stability_timeout=1.0)

    @patch("src.watcher.AudioFolderHandler._wait_for_file_ready")
    def test_on_created_wav_file(self, mock_ready):
        """Tests that a valid .wav file creation triggers queuing after stabilizing."""
        # Arrange
        mock_ready.return_value = True
        test_path = "/watched/folder/alert.wav"
        event = FileCreatedEvent(test_path)
        expected_resolved_path = Path(test_path).resolve()

        # Act
        self.handler.on_created(event)

        # Assert
        mock_ready.assert_called_once_with(expected_resolved_path)
        self.assertEqual(self.audio_queue.qsize(), 1)
        self.assertEqual(self.audio_queue.get(), expected_resolved_path)

    @patch("src.watcher.AudioFolderHandler._wait_for_file_ready")
    def test_on_created_non_wav_file(self, mock_ready):
        """Tests that non-wav files (like .txt) are ignored and not queued."""
        # Arrange
        event = FileCreatedEvent("/watched/folder/document.txt")

        # Act
        self.handler.on_created(event)

        # Assert
        mock_ready.assert_not_called()
        self.assertEqual(self.audio_queue.qsize(), 0)

    @patch("src.watcher.AudioFolderHandler._wait_for_file_ready")
    def test_on_moved_wav_file(self, mock_ready):
        """Tests that moving/renaming a WAV file into the folder triggers queuing."""
        # Arrange
        mock_ready.return_value = True
        dest_path = "/watched/folder/new_alert.WAV"
        event = FileMovedEvent("/outside/temp.wav", dest_path)
        expected_resolved_path = Path(dest_path).resolve()

        # Act
        self.handler.on_moved(event)

        # Assert
        mock_ready.assert_called_once_with(expected_resolved_path)
        self.assertEqual(self.audio_queue.qsize(), 1)
        self.assertEqual(self.audio_queue.get(), expected_resolved_path)

    @patch("src.watcher.time.sleep")
    @patch("src.watcher.Path.exists")
    @patch("src.watcher.Path.stat")
    @patch("builtins.open", new_callable=mock_open)
    def test_wait_for_file_ready_success(self, mock_file, mock_stat, mock_exists, mock_sleep):
        """Tests that _wait_for_file_ready succeeds when size stabilizes and file is readable."""
        # Arrange
        mock_exists.return_value = True
        
        # Mock size to be stable (e.g. 1024 bytes on consecutive checks)
        mock_stat_obj = MagicMock()
        mock_stat_obj.st_size = 1024
        mock_stat.return_value = mock_stat_obj

        test_file = Path("/watched/folder/stable.wav")

        # Act
        result = self.handler._wait_for_file_ready(test_file)

        # Assert
        self.assertTrue(result)
        mock_exists.assert_called()
        mock_stat.assert_called()
        mock_file.assert_called_once_with(test_file, 'rb')

    @patch("src.watcher.time.time")
    @patch("src.watcher.Path.exists")
    def test_wait_for_file_ready_timeout(self, mock_exists, mock_time):
        """Tests that _wait_for_file_ready fails if the size never stabilizes or is 0."""
        # Arrange
        mock_exists.return_value = True
        
        # Mock time to advance 2 seconds on the next call, exceeding the 1.0 second timeout limit
        mock_time.side_effect = [1000.0, 1002.0]

        test_file = Path("/watched/folder/growing.wav")

        # Act
        result = self.handler._wait_for_file_ready(test_file)

        # Assert
        self.assertFalse(result)

if __name__ == "__main__":
    unittest.main()

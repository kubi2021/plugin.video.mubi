import unittest
from unittest.mock import MagicMock, patch
import os
import xbmcaddon # Access the mock from conftest (sys.modules)

from plugin_video_mubi.resources.lib.library import Library

class TestConcurrency(unittest.TestCase):
    
    def setUp(self):
        # Reset common mocks if needed
        xbmcaddon.Addon.reset_mock()

    @patch('plugin_video_mubi.resources.lib.library.xbmc')
    @patch('plugin_video_mubi.resources.lib.library.xbmcgui')
    @patch('concurrent.futures.as_completed')
    @patch('concurrent.futures.ThreadPoolExecutor')
    @patch('os.cpu_count')
    def test_auto_concurrency_4_cores(self, mock_cpu, mock_executor, mock_as_completed, mock_gui, mock_xbmc):
        """Test Auto (0) with 4 cores -> 20 threads."""
        # Arrange
        mock_cpu.return_value = 4
        # Configure the shared mock directly
        xbmcaddon.Addon.return_value.getSettingInt.return_value = 0
        mock_as_completed.return_value = [] 
        
        library = Library()
        library.films = [MagicMock(), MagicMock()] 
        
        library.filter_films_by_genre = MagicMock()
        library.prepare_files_for_film = MagicMock()
        library.remove_obsolete_files = MagicMock()
        library.is_film_valid = MagicMock(return_value=True)

        # Act
        library.sync_locally("plugin://url", MagicMock())

        # Assert
        # 4 cores * 5 = 20 threads
        mock_executor.assert_called_with(max_workers=20)
        
    @patch('plugin_video_mubi.resources.lib.library.xbmc')
    @patch('plugin_video_mubi.resources.lib.library.xbmcgui')
    @patch('concurrent.futures.as_completed')
    @patch('concurrent.futures.ThreadPoolExecutor')
    @patch('os.cpu_count')
    def test_auto_concurrency_1_core(self, mock_cpu, mock_executor, mock_as_completed, mock_gui, mock_xbmc):
        """Test Auto (0) with 1 core -> 5 threads."""
        # Arrange
        mock_cpu.return_value = 1
        xbmcaddon.Addon.return_value.getSettingInt.return_value = 0
        mock_as_completed.return_value = []
        
        library = Library()
        library.films = [MagicMock()] 
        library.filter_films_by_genre = MagicMock()
        library.remove_obsolete_files = MagicMock()
        library.is_film_valid = MagicMock(return_value=True)

        # Act
        library.sync_locally("plugin://url", MagicMock())

        # Assert
        # 1 core * 5 = 5 threads
        mock_executor.assert_called_with(max_workers=5)

    @patch('plugin_video_mubi.resources.lib.library.xbmc')
    @patch('plugin_video_mubi.resources.lib.library.xbmcgui')
    @patch('concurrent.futures.as_completed')
    @patch('concurrent.futures.ThreadPoolExecutor')
    @patch('os.cpu_count')
    def test_auto_concurrency_high_core_clamped(self, mock_cpu, mock_executor, mock_as_completed, mock_gui, mock_xbmc):
        """Test Auto (0) with 8 cores -> clamped to 20 threads."""
        # Arrange
        mock_cpu.return_value = 8
        xbmcaddon.Addon.return_value.getSettingInt.return_value = 0
        mock_as_completed.return_value = []
        
        library = Library()
        library.films = [MagicMock()] 
        library.filter_films_by_genre = MagicMock()
        library.remove_obsolete_files = MagicMock()
        library.is_film_valid = MagicMock(return_value=True)

        # Act
        library.sync_locally("plugin://url", MagicMock())

        # Assert
        # 8 * 5 = 40, but clamped to 20
        mock_executor.assert_called_with(max_workers=20)
        
    @patch('plugin_video_mubi.resources.lib.library.xbmc')
    @patch('plugin_video_mubi.resources.lib.library.xbmcgui')
    @patch('concurrent.futures.as_completed')
    @patch('concurrent.futures.ThreadPoolExecutor')
    def test_manual_concurrency(self, mock_executor, mock_as_completed, mock_gui, mock_xbmc):
        """Test Manual setting -> Exact val."""
        # Arrange
        xbmcaddon.Addon.return_value.getSettingInt.return_value = 8
        mock_as_completed.return_value = []
        
        library = Library()
        library.films = [MagicMock()] 
        library.filter_films_by_genre = MagicMock()
        library.remove_obsolete_files = MagicMock()
        library.is_film_valid = MagicMock(return_value=True)

        # Act
        library.sync_locally("plugin://url", MagicMock())

        # Assert
        mock_executor.assert_called_with(max_workers=8)

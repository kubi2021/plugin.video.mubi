
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from plugin_video_mubi.resources.lib.library import Library
import os
import concurrent.futures
import xbmcaddon

class TestConcurrency:
    
    @patch('plugin_video_mubi.resources.lib.library.os.cpu_count')
    @patch('concurrent.futures.ThreadPoolExecutor')
    @patch('concurrent.futures.as_completed')
    @patch('plugin_video_mubi.resources.lib.library.xbmcgui.DialogProgress')
    @patch('plugin_video_mubi.resources.lib.library.xbmc')
    def test_sync_auto_concurrency_90_percent(self, mock_xbmc, mock_dialog, mock_as_completed, mock_executor, mock_cpu_count):
        """Test that Auto setting (0) uses 90% of available CPU threads."""
        
        # Mock as_completed to return immediately (empty list of completed futures)
        mock_as_completed.return_value = []
        
        # CPU count = 10 -> 90% = 9
        mock_cpu_count.return_value = 10
        
        # Mock settings: sync_concurrency = 0 (Auto)
        with patch('plugin_video_mubi.resources.lib.library.xbmcaddon.Addon') as mock_addon_cls:
            mock_addon_instance = mock_addon_cls.return_value
            mock_addon_instance.getSettingInt.return_value = 0
            mock_addon_instance.getSettingBool.return_value = False 
            
            library = Library()
            with patch.object(Library, 'remove_obsolete_files'):
                library.films = [MagicMock()] 
                with patch.object(Library, 'is_film_valid', return_value=True):
                     library.sync_locally("plugin://url", Path("/tmp"))
            
            # Verify ThreadPoolExecutor was initialized with 9 workers
            mock_executor.assert_called_with(max_workers=9)
        
    @patch('plugin_video_mubi.resources.lib.library.os.cpu_count')
    @patch('concurrent.futures.ThreadPoolExecutor')
    @patch('concurrent.futures.as_completed')
    @patch('plugin_video_mubi.resources.lib.library.xbmcgui.DialogProgress')
    @patch('plugin_video_mubi.resources.lib.library.xbmc')
    def test_sync_auto_concurrency_single_core(self, mock_xbmc, mock_dialog, mock_as_completed, mock_executor, mock_cpu_count):
        """Test that Auto setting on single core uses 1 thread (min 1)."""

        mock_as_completed.return_value = []
        # CPU count = 1 -> 90% = 0.9 -> int is 0 -> max(1, 0) = 1
        mock_cpu_count.return_value = 1
        
        with patch('plugin_video_mubi.resources.lib.library.xbmcaddon.Addon') as mock_addon_cls:
            mock_addon_instance = mock_addon_cls.return_value
            mock_addon_instance.getSettingInt.return_value = 0
            mock_addon_instance.getSettingBool.return_value = False
            
            library = Library()
            with patch.object(Library, 'remove_obsolete_files'):
                library.films = [MagicMock()]
                with patch.object(Library, 'is_film_valid', return_value=True):
                    library.sync_locally("plugin://url", Path("/tmp"))
                
            mock_executor.assert_called_with(max_workers=1)

    @patch('concurrent.futures.ThreadPoolExecutor')
    @patch('concurrent.futures.as_completed')
    @patch('plugin_video_mubi.resources.lib.library.xbmcgui.DialogProgress')
    @patch('plugin_video_mubi.resources.lib.library.xbmc')
    def test_sync_manual_concurrency(self, mock_xbmc, mock_dialog, mock_as_completed, mock_executor):
        """Test that manual setting uses specified number of threads."""
        
        mock_as_completed.return_value = []
        
        with patch('plugin_video_mubi.resources.lib.library.xbmcaddon.Addon') as mock_addon_cls:
            mock_addon_instance = mock_addon_cls.return_value
            # Manual setting = 4
            mock_addon_instance.getSettingInt.return_value = 4
            mock_addon_instance.getSettingBool.return_value = False
            
            library = Library()
            with patch.object(Library, 'remove_obsolete_files'):
                library.films = [MagicMock()]
                with patch.object(Library, 'is_film_valid', return_value=True):
                     library.sync_locally("plugin://url", Path("/tmp"))
            
            mock_executor.assert_called_with(max_workers=4)

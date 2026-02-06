import pytest
from unittest.mock import MagicMock, patch, call
from plugin_video_mubi.resources.lib.navigation_handler import NavigationHandler

class MockPlugin:
    def __init__(self):
        self.settings = {}
    
    def getSettingBool(self, key):
        return self.settings.get(key, False)
        
    def getAddonInfo(self, key):
        return "/tmp/profile"

@patch('plugin_video_mubi.resources.lib.navigation_handler.xbmc')
@patch('plugin_video_mubi.resources.lib.navigation_handler.LibraryMonitor')
@patch('xbmcgui.Dialog')
@patch('xbmcplugin.setPluginCategory')
@patch('xbmcplugin.setContent')
@patch('xbmcplugin.endOfDirectory')
@patch('time.sleep')
def test_wait_for_library_idle_immediate(mock_sleep, mock_end, mock_content, mock_cat, mock_diag, mock_monitor, mock_xbmc):
    # Setup
    handle = 1
    base_url = "plugin://test"
    mubi = MagicMock()
    session = MagicMock()

    # Configure xbmc to be not aborted and not busy
    mock_xbmc.abortRequested = False
    mock_xbmc.getCondVisibility.return_value = False 
    
    handler = NavigationHandler(handle, base_url, mubi, session)
    
    # Act
    handler.wait_for_library_idle(timeout=5)
    
    # Assert
    assert mock_xbmc.getCondVisibility.called
    # Should not sleep if immediately idle
    assert not mock_sleep.called

@patch('plugin_video_mubi.resources.lib.navigation_handler.xbmc')
@patch('plugin_video_mubi.resources.lib.navigation_handler.LibraryMonitor')
@patch('xbmcgui.Dialog')
@patch('xbmcplugin.setPluginCategory')
@patch('xbmcplugin.setContent')
@patch('xbmcplugin.endOfDirectory')
@patch('time.sleep')
def test_wait_for_library_idle_waits(mock_sleep, mock_end, mock_content, mock_cat, mock_diag, mock_monitor, mock_xbmc):
    # Setup
    handle = 1
    base_url = "plugin://test"
    mubi = MagicMock()
    session = MagicMock()
    
    handler = NavigationHandler(handle, base_url, mubi, session)
    
    # Configure xbmc
    mock_xbmc.abortRequested = False
    
    # Mock library as busy then idle
    # Sequence: Scanning (True), Cleaning (False) -> Wait -> Scanning (False), Cleaning (False) -> Done
    # The loop checks IsScanningVideo then IsCleaning.
    # Iteration 1: getCondVisibility('Library.IsScanningVideo') -> True (Busy) -> Sleep
    # Iteration 2: getCondVisibility('Library.IsScanningVideo') -> False, getCondVisibility('Library.IsCleaning') -> False (Idle) -> Return
    
    # Side effect for getCondVisibility
    # Iteration 1: Scanning=True, Cleaning=False (Consumed 2 values) -> Sleep
    # Iteration 2: Scanning=False, Cleaning=False (Consumed 2 values) -> Return
    mock_xbmc.getCondVisibility.side_effect = [True, False, False, False]
    
    # Act
    handler.wait_for_library_idle(timeout=5)
    
    # Assert
    assert mock_sleep.called
    assert mock_xbmc.getCondVisibility.call_count >= 3

@patch('plugin_video_mubi.resources.lib.navigation_handler.xbmc')
@patch('plugin_video_mubi.resources.lib.navigation_handler.LibraryMonitor')
@patch('xbmcgui.Dialog')
@patch('xbmcplugin.setPluginCategory')
@patch('xbmcplugin.setContent')
@patch('xbmcplugin.endOfDirectory')
@patch('time.sleep')
def test_wait_for_library_idle_timeout(mock_sleep, mock_end, mock_content, mock_cat, mock_diag, mock_monitor, mock_xbmc):
    # Setup
    handle = 1
    base_url = "plugin://test"
    mubi = MagicMock()
    session = MagicMock()
    
    handler = NavigationHandler(handle, base_url, mubi, session)
    
    # Configure xbmc
    mock_xbmc.abortRequested = False
    # Always busy
    mock_xbmc.getCondVisibility.return_value = True
    
    # Act
    # Use a small timeout to ensure loop logic works, relying on mocked time if possible, 
    # but here relying on loop count limitation or we need to patch time.time
    with patch('time.time') as mock_time:
        # iteration 1: start_time = 0
        # iteration 2: time.time() = 0 -> diff 0 < 2 -> continue
        # iteration 3: time.time() = 3 -> diff 3 > 2 -> break
        mock_time.side_effect = [0, 0, 3] 
        handler.wait_for_library_idle(timeout=2)
    
    # Assert
    assert mock_sleep.called
    # Should log warning
    args, _ = mock_xbmc.log.call_args
    assert "timeout" in args[0].lower() or "proceeding" in args[0].lower()

@patch('plugin_video_mubi.resources.lib.navigation_handler.xbmc')
@patch('plugin_video_mubi.resources.lib.navigation_handler.LibraryMonitor')
def test_clean_kodi_library_calls_wait(mock_monitor, mock_xbmc):
    # Setup
    handle = 1
    base_url = "plugin://test"
    mubi = MagicMock()
    session = MagicMock()
    handler = NavigationHandler(handle, base_url, mubi, session)
    
    # Mock wait_for_library_idle
    handler.wait_for_library_idle = MagicMock()
    
    monitor_instance = mock_monitor.return_value
    monitor_instance.clean_finished = True 
    
    # Act
    handler.clean_kodi_library(monitor_instance)
    
    # Assert
    handler.wait_for_library_idle.assert_called_once()
    mock_xbmc.executebuiltin.assert_called_with('CleanLibrary(video)')

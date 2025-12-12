
import pytest
import xbmc
from unittest.mock import MagicMock, patch
from plugin_video_mubi.resources.lib.navigation_handler import NavigationHandler

class MockPlugin:
    def __init__(self):
        self.settings = {}
    
    def getSettingBool(self, key):
        return self.settings.get(key, False)
        
    def getAddonInfo(self, key):
        return "/tmp/profile"

@patch('plugin_video_mubi.resources.lib.navigation_handler.LibraryMonitor')
@patch('xbmc.log')
@patch('xbmcgui.Dialog')
@patch('xbmcgui.DialogProgress')
@patch('xbmcplugin.setPluginCategory')
@patch('xbmcplugin.setContent')
@patch('xbmcplugin.endOfDirectory')
def test_sync_auto_clean_setting_true(mock_end, mock_content, mock_cat, mock_prog, mock_diag, mock_log, mock_monitor):
    # Setup
    handle = 1
    base_url = "plugin://test"
    mubi = MagicMock()
    session = MagicMock()
    
    handler = NavigationHandler(handle, base_url, mubi, session)
    handler.plugin = MockPlugin()
    handler.plugin.settings['auto_clean_library'] = True
    
    # Mock clean_kodi_library to verifying calling
    handler.clean_kodi_library = MagicMock()
    handler.update_kodi_library = MagicMock()
    
    # Mock mubi.get_all_films to return empty library
    mock_lib = MagicMock()
    mock_lib.films = []
    mubi.get_all_films.return_value = mock_lib
    
    # Mock get_provider to return valid provider
    with patch('plugin_video_mubi.resources.lib.external_metadata.MetadataProviderFactory.get_provider') as mock_prov:
        mock_prov.return_value = MagicMock()
        mock_prov.return_value.test_connection.return_value = True
        
        # Configure DialogProgress mock to not be canceled
        mock_prog_instance = mock_prog.return_value
        mock_prog_instance.iscanceled.return_value = False

        # Act
        handler.sync_films(["US"])

        # Assert
        handler.clean_kodi_library.assert_called_once()
        handler.update_kodi_library.assert_called_once()

@patch('plugin_video_mubi.resources.lib.navigation_handler.LibraryMonitor')
@patch('xbmc.log')
@patch('xbmcgui.Dialog')
@patch('xbmcgui.DialogProgress')
@patch('xbmcplugin.setPluginCategory')
@patch('xbmcplugin.setContent')
@patch('xbmcplugin.endOfDirectory')
def test_sync_auto_clean_setting_false(mock_end, mock_content, mock_cat, mock_prog, mock_diag, mock_log, mock_monitor):
    # Setup
    handle = 1
    base_url = "plugin://test"
    mubi = MagicMock()
    session = MagicMock()
    
    handler = NavigationHandler(handle, base_url, mubi, session)
    handler.plugin = MockPlugin()
    handler.plugin.settings['auto_clean_library'] = False # DISABLED
    
    # Mock clean_kodi_library to verifying calling
    handler.clean_kodi_library = MagicMock()
    handler.update_kodi_library = MagicMock()
    
    # Mock mubi.get_all_films to return empty library
    mock_lib = MagicMock()
    mock_lib.films = []
    mubi.get_all_films.return_value = mock_lib
    
    # Mock get_provider to return valid provider
    with patch('plugin_video_mubi.resources.lib.external_metadata.MetadataProviderFactory.get_provider') as mock_prov:
        mock_prov.return_value = MagicMock()
        mock_prov.return_value.test_connection.return_value = True
        
        # Configure DialogProgress mock to not be canceled
        mock_prog_instance = mock_prog.return_value
        mock_prog_instance.iscanceled.return_value = False
        
        # Act
        handler.sync_films(["US"])

        # Assert
        handler.clean_kodi_library.assert_not_called()
        handler.update_kodi_library.assert_called_once()

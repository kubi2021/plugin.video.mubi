from unittest.mock import Mock, patch
import pytest
from plugin_video_mubi.resources.lib.navigation_handler import NavigationHandler

class TestSyncValidation:
    
    @pytest.fixture
    def navigation_handler(self):
        plugin = Mock()
        base_url = "plugin://plugin.video.mubi"
        mubi = Mock()
        session = Mock()
        return NavigationHandler(plugin, base_url, mubi, session)

    @patch('plugin_video_mubi.resources.lib.external_metadata.MetadataProviderFactory')
    @patch('plugin_video_mubi.resources.lib.navigation_handler.xbmcgui.Dialog')
    @patch('plugin_video_mubi.resources.lib.navigation_handler.xbmc.log')
    def test_sync_aborted_no_keys(self, mock_log, mock_dialog_cls, mock_factory, navigation_handler):
        """Test sync aborts if no provider is configured."""
        mock_factory.get_provider.return_value = None
        mock_dialog = mock_dialog_cls.return_value
        # Simulate user cancelling the "Go to Settings" dialog (returns False/0)
        mock_dialog.yesno.return_value = False
        
        # Ensure lock is released even on return, 
        # but first we need to make sure sync_in_progress is False initially
        NavigationHandler._sync_in_progress = False
        
        # We need to ensure the lock logic doesn't block the test itself
        # The code under test uses 'with NavigationHandler._sync_lock'
        # which is fine in a single threaded test
        
        navigation_handler.sync_films(countries=['US'])
        
        # Should show yesno dialog
        mock_dialog.yesno.assert_called_once()
        # Should NOT log start sync
        assert not any("Starting film sync" in str(call) for call in mock_log.call_args_list)

    @patch('plugin_video_mubi.resources.lib.external_metadata.MetadataProviderFactory')
    @patch('plugin_video_mubi.resources.lib.navigation_handler.xbmcgui.Dialog')
    @patch('plugin_video_mubi.resources.lib.navigation_handler.xbmc.log')
    def test_sync_aborted_invalid_tmdb_key(self, mock_log, mock_dialog_cls, mock_factory, navigation_handler):
        """Test sync aborts if TMDB key is invalid."""
        mock_provider = Mock()
        mock_provider.provider_name = "TMDB"
        mock_provider.test_connection.return_value = False
        mock_factory.get_provider.return_value = mock_provider
        
        # Reset any previous calls to Dialog (from factory checks if any)
        mock_dialog_cls.reset_mock()
        navigation_handler.plugin.reset_mock()
        
        NavigationHandler._sync_in_progress = False
        navigation_handler.sync_films(countries=['US'])
        
        # Verify provider connection was tested
        mock_provider.test_connection.assert_called_once()
        
        # Verify notifications
        # Since multiple notifications happen, we check calls
        mock_instance = mock_dialog_cls.return_value
        
        # Check that we got the error notification
        # Allow checking just the message part or using ANY for other args
        from unittest.mock import ANY
        mock_instance.notification.assert_any_call(
            "MUBI", 
            "Invalid API Key for TMDB. Sync aborted.", 
            ANY, # xbmcgui.NOTIFICATION_ERROR
            5000
        )
        
        assert NavigationHandler._sync_in_progress is False

    @patch('plugin_video_mubi.resources.lib.external_metadata.MetadataProviderFactory')
    @patch('plugin_video_mubi.resources.lib.navigation_handler.xbmcgui.Dialog')
    @patch('plugin_video_mubi.resources.lib.navigation_handler.xbmc.log')
    def test_sync_aborted_invalid_omdb_key(self, mock_log, mock_dialog_cls, mock_factory, navigation_handler):
        """Test sync aborts if OMDB key is invalid (when it's the active provider)."""
        mock_provider = Mock()
        mock_provider.provider_name = "OMDB"
        mock_provider.test_connection.return_value = False
        mock_factory.get_provider.return_value = mock_provider
        
        mock_dialog_cls.reset_mock()
        
        NavigationHandler._sync_in_progress = False
        navigation_handler.sync_films(countries=['US'])
        
        mock_instance = mock_dialog_cls.return_value
        from unittest.mock import ANY
        mock_instance.notification.assert_any_call(
            "MUBI", 
            "Invalid API Key for OMDB. Sync aborted.", 
            ANY,
            5000
        )
        assert NavigationHandler._sync_in_progress is False

    @patch('plugin_video_mubi.resources.lib.external_metadata.MetadataProviderFactory')
    @patch('plugin_video_mubi.resources.lib.navigation_handler.xbmcgui.Dialog')
    @patch('plugin_video_mubi.resources.lib.navigation_handler.xbmc.log')
    def test_sync_proceeds_valid_key(self, mock_log, mock_dialog_cls, mock_factory, navigation_handler):
        """Test sync proceeds if key is valid."""
        mock_provider = Mock()
        mock_provider.provider_name = "TMDB"
        mock_provider.test_connection.return_value = True
        mock_factory.get_provider.return_value = mock_provider
        
        mock_mubi = navigation_handler.mubi # get Mock from fixture
        mock_mubi.get_all_films.return_value = Mock(films=[])
        
        NavigationHandler._sync_in_progress = False
        
        with patch('plugin_video_mubi.resources.lib.navigation_handler.LibraryMonitor'), \
             patch('plugin_video_mubi.resources.lib.navigation_handler.xbmcvfs.translatePath', return_value="/tmp"):
             
             navigation_handler.sync_films(countries=['US'])
             
        # Verify connection tested
        mock_provider.test_connection.assert_called_once()
        
        # Verify we proceeded to log start
        assert any("Starting sync" in str(call) for call in mock_log.call_args_list)
        
        assert NavigationHandler._sync_in_progress is False

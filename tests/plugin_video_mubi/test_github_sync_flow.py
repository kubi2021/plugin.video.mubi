from unittest.mock import Mock, patch, MagicMock, call
import pytest
from plugin_video_mubi.resources.lib.navigation_handler import NavigationHandler
from plugin_video_mubi.resources.lib.library import Library
from plugin_video_mubi.resources.lib.film import Film

class TestGithubSyncFlow:
    
    @pytest.fixture
    def navigation_handler(self):
        plugin = Mock()
        plugin.getSettingInt.return_value = 5 # concurrency
        base_url = "plugin://plugin.video.mubi"
        mubi = Mock()
        session = Mock()
        handler = NavigationHandler(plugin, base_url, mubi, session)
        return handler

    @patch('plugin_video_mubi.resources.lib.external_metadata.MetadataProviderFactory')
    @patch('plugin_video_mubi.resources.lib.navigation_handler.xbmcgui.Dialog')
    @patch('plugin_video_mubi.resources.lib.navigation_handler.xbmc.log')
    def test_github_sync_skips_provider_check(self, mock_log, mock_dialog_cls, mock_factory, navigation_handler):
        """Test sync_from_github does NOT check for metadata providers."""
        
        # Setup: Provider check would normally fail or return None
        # Use MagicMock to track calls
        mock_factory.get_provider = MagicMock(return_value=None)
        
        # Mock fetch process to return empty library so we don't crash
        mock_mubi = navigation_handler.mubi 
        mock_mubi.get_all_films.return_value = Library()
        
        NavigationHandler._sync_in_progress = False
        
        # Act
        navigation_handler.sync_from_github()
        
        # Assert
        # Should NOT have called get_provider even once
        mock_factory.get_provider.assert_not_called()
        
        # Should have proceeded to start sync ("Starting sync: Syncing (Worldwide)...")
        assert any("Starting sync: Syncing (Worldwide)..." in str(call) for call in mock_log.call_args_list)

    @patch('plugin_video_mubi.resources.lib.film.MetadataProviderFactory')
    def test_create_nfo_skips_external_metadata(self, mock_factory):
        """Test create_nfo_file skips external metadata lookup when flag is True."""
        
        from pathlib import Path
        
        # Setup
        film = Film(
            mubi_id="123",
            title="Test Film",
            artwork="http://example.com/img.jpg",
            web_url="http://example.com",
            metadata=Mock(
                title="Test Film", 
                originaltitle="Test Film", 
                year="2022",
                rating=8.0,
                votes=100,
                plot="Plot", 
                plotoutline="Outline",
                duration=100,
                mpaa={'US': "PG"},
                trailer="http://trailer",
                image="http://img.jpg",
                genre=[],
                director=[],
                country=[],
                audio_languages=[],
                subtitle_languages=[],
                dateadded="2022-01-01",
                content_warnings=[],
                premiered=None,
                tagline=None,
                media_features=[]
            )
        )
        # Mock download_all_artwork to avoid network calls
        film._download_all_artwork = Mock(return_value={})
        
        # Mock provider calls
        mock_provider = Mock()
        mock_factory.get_provider.return_value = mock_provider
        
        # Act
        with patch('builtins.open', new_callable=MagicMock), \
             patch('plugin_video_mubi.resources.lib.film.Path.exists', return_value=True):
             
            film.create_nfo_file(Path("/tmp"), "plugin://url", skip_external_metadata=True)
            
        # Assert
        # Should NOT have called get_provider
        mock_factory.get_provider.assert_not_called()

    @patch('plugin_video_mubi.resources.lib.film.MetadataProviderFactory')
    def test_create_nfo_fetches_external_metadata_by_default(self, mock_factory):
        """Test create_nfo_file fetches external metadata when flag is False (default)."""
        
        from pathlib import Path

        # Setup
        film = Film(
            mubi_id="1234",
            title="Test Film 2",
            artwork="http://example.com/img.jpg",
            web_url="http://example.com",
            metadata=Mock(
                title="Test Film 2", 
                originaltitle="Test Film", 
                year="2022",
                rating=8.0,
                votes=100,
                plot="Plot", 
                plotoutline="Outline",
                duration=100,
                mpaa={'US': 'PG'},
                trailer="http://trailer",
                image="http://img.jpg",
                genre=[],
                director=[],
                country=[],
                audio_languages=[],
                subtitle_languages=[],
                dateadded="2022-01-01",
                content_warnings=[],
                premiered=None,
                tagline=None,
                media_features=[]
            )
        )
        film._download_all_artwork = Mock(return_value={})
        
        mock_provider = Mock()
        mock_provider.get_imdb_id.return_value = Mock(success=True, imdb_id="tt123", tmdb_id="456")
        mock_factory.get_provider.return_value = mock_provider
        
        # Act
        with patch('builtins.open', new_callable=MagicMock), \
             patch('plugin_video_mubi.resources.lib.film.Path.exists', return_value=True):
             
            film.create_nfo_file(Path("/tmp"), "plugin://url", skip_external_metadata=False)
            
        # Assert
        # Should HAVE called get_provider
        mock_factory.get_provider.assert_called()
        mock_provider.get_imdb_id.assert_called_once()

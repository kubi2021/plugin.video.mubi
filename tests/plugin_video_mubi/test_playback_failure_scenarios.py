"""
Test suite for Playback Failure Scenarios in NavigationHandler.
Focuses on coherent error messages and edge cases.
"""
import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import datetime
import requests
import os
import shutil
from pathlib import Path
from plugin_video_mubi.resources.lib.navigation_handler import NavigationHandler
import dateutil.parser # Import to ensure it is available (mocked or real)

# Optional: freezegun for deterministic time-based tests
try:
    from freezegun import freeze_time
    HAS_FREEZEGUN = True
except ImportError:
    # Fallback: no-op decorator if freezegun not installed
    def freeze_time(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    HAS_FREEZEGUN = False

@pytest.fixture
def mock_mubi():
    mubi = Mock()
    mubi.get_categories.return_value = []
    # Default behavior for select_best_stream to avoid NoneType errors in happy paths
    mubi.select_best_stream.return_value = "http://stream.url"
    # Default return value for get_secure_stream_info (empty dict means success but no specific data)
    mubi.get_secure_stream_info.return_value = {}
    return mubi

@pytest.fixture
def mock_session():
    session = Mock()
    session.is_logged_in = True
    session.token = "test-token"
    session.user_id = "test-user"
    return session

def parse_iso_date(date_str):
    """Helper for date parsing side effect"""
    if not date_str: return None
    # Handle Z suffix manually if python version < 3.11 fully handling it (though 3.11 does)
    return datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))

class TestPlaybackFailureScenarios:
    """Tests for play_mubi_video failure modes and error messaging."""

    @pytest.fixture
    def navigation_handler(self, mock_mubi, mock_session):
        # We need to ensure the mocked addon data path exists so iterdir() doesn't crash
        mock_path = '/tmp/mock_kodi'
        os.makedirs(mock_path, exist_ok=True)
        
        with patch('xbmcaddon.Addon') as mock_addon_cls, patch('xbmc.log'), patch('xbmcvfs.translatePath', return_value=mock_path):
            mock_addon_instance = Mock()
            mock_addon_instance.getSetting.side_effect = lambda key: {'client_country': 'US'}.get(key, '')
            mock_addon_cls.return_value = mock_addon_instance
            handler = NavigationHandler(1, "plugin://test", mock_mubi, mock_session)
            yield handler

    @patch('xbmc.log')
    @patch('xbmcvfs.translatePath')
    def test_play_mubi_video_expired_film(self, mock_translate_path, mock_log, navigation_handler, tmp_path):
        """Test that expired film shows availability warning with play-anyway option."""
        import dateutil.parser
        dateutil.parser.parse.side_effect = parse_iso_date
        
        mock_translate_path.return_value = str(tmp_path)
        film_id = "expired_123"
        
        # Set client_country to CH so it matches the NFO country
        navigation_handler.plugin.getSetting.side_effect = lambda key: {'client_country': 'CH'}.get(key, '')
        
        # Create expired NFO
        film_folder = tmp_path / "Expired Film (2020)"
        film_folder.mkdir(parents=True, exist_ok=True)
        (film_folder / "Expired Film (2020).strm").write_text(f"plugin://plugin.video.mubi/?action=play_mubi_video&film_id={film_id}")
        
        past_date = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=365)).isoformat()
        nfo_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<movie>
    <title>Expired Film</title>
    <mubi_availability>
        <country code="CH">
            <name>Switzerland</name>
            <availability>live</availability>
            <expires_at>{past_date}</expires_at>
        </country>
    </mubi_availability>
</movie>"""
        (film_folder / "Expired Film (2020).nfo").write_text(nfo_content)

        with patch('xbmcgui.Dialog') as mock_dialog, \
             patch('xbmcplugin.setResolvedUrl'):
            mock_dialog_instance = Mock()
            mock_dialog_instance.yesno.return_value = False  # User cancels
            mock_dialog.return_value = mock_dialog_instance

            navigation_handler.play_mubi_video(film_id=film_id, web_url="https://mubi.com/films/expired")

            # Should show yesno with availability status warning
            mock_dialog_instance.yesno.assert_called_once()
            args = mock_dialog_instance.yesno.call_args[0]
            assert "MUBI" in args[0]
            # Stream info should NOT be called since user cancelled
            navigation_handler.mubi.get_secure_stream_info.assert_not_called() 

    @patch('dateutil.parser.parse', side_effect=parse_iso_date)
    @patch('xbmc.log')
    @patch('xbmcvfs.translatePath')
    def test_play_mubi_video_future_film(self, mock_translate_path, mock_log, mock_parse, navigation_handler, tmp_path):
        """Test that future/upcoming film shows availability warning with play-anyway option."""
        mock_translate_path.return_value = str(tmp_path)
        film_id = "future_456"
        
        # Set client_country to CH so it matches the NFO country
        navigation_handler.plugin.getSetting.side_effect = lambda key: {'client_country': 'CH'}.get(key, '')
        
        film_folder = tmp_path / "Future Film (2025)"
        film_folder.mkdir(parents=True, exist_ok=True)
        (film_folder / "Future Film (2025).strm").write_text(f"plugin://plugin.video.mubi/?action=play_mubi_video&film_id={film_id}")
        
        future_date = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)).isoformat()
        nfo_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<movie>
    <title>Future Film</title>
    <mubi_availability>
        <country code="CH">
            <name>Switzerland</name>
            <availability>upcoming</availability>
            <available_at>{future_date}</available_at>
        </country>
    </mubi_availability>
</movie>"""
        (film_folder / "Future Film (2025).nfo").write_text(nfo_content)

        with patch('xbmcgui.Dialog') as mock_dialog, \
             patch('xbmcplugin.setResolvedUrl'):
            mock_dialog_instance = Mock()
            mock_dialog_instance.yesno.return_value = False  # User cancels
            mock_dialog.return_value = mock_dialog_instance

            navigation_handler.play_mubi_video(film_id=film_id, web_url="https://mubi.com/films/future")

            # Should show yesno with "upcoming" status warning
            mock_dialog_instance.yesno.assert_called_once()
            args = mock_dialog_instance.yesno.call_args[0]
            assert "Availability" in args[0] or "MUBI" in args[0]
            # Stream info should NOT be called since user cancelled
            navigation_handler.mubi.get_secure_stream_info.assert_not_called()

    def test_play_mubi_video_geo_restriction_api_response(self, navigation_handler):
        """Test coherent error message when API returns explicit geo-restriction."""
        navigation_handler.mubi.get_secure_stream_info.return_value = {
            'error': "Film not available in your country. Use a VPN to France."
        }
        
        with patch('xbmcgui.Dialog') as mock_dialog, \
             patch('xbmcplugin.setResolvedUrl') as mock_resolved:
            mock_dialog_instance = Mock()
            mock_dialog.return_value = mock_dialog_instance

            navigation_handler.play_mubi_video(film_id="geo_block", web_url="https://mubi.com/uhoh")

            # Now uses notification for API errors (not ok dialog)
            mock_dialog_instance.notification.assert_called()
            args = mock_dialog_instance.notification.call_args[0]
            assert "Use a VPN to France" in args[1]
            mock_resolved.assert_called_with(navigation_handler.handle, False, unittest.mock.ANY)

    def test_play_mubi_video_api_error_response(self, navigation_handler):
        """Test coherent generic API error message."""
        navigation_handler.mubi.get_secure_stream_info.return_value = {
            'error': "Service temporarily unavailable"
        }

        with patch('xbmcgui.Dialog') as mock_dialog:
            mock_dialog_instance = Mock()
            mock_dialog.return_value = mock_dialog_instance

            # We simplified error handling to NOT raise Exception for handled errors, just show notification
            # But the code says raises Exception("Error in stream info")
            # And expects to catch and suppress "An unexpected error occurred".
            # So try/except block in test is useful just in case we didn't mock the raise away (we didn't).
            try:
                navigation_handler.play_mubi_video(film_id="api_error", web_url="https://mubi.com/error")
            except Exception:
                pass

            mock_dialog_instance.notification.assert_called()
            args = mock_dialog_instance.notification.call_args[0]
            assert "Service temporarily unavailable" in args[1]

    def test_play_mubi_video_network_exception_coherent_msg(self, navigation_handler):
        """Test coherent error message for network exceptions."""
        # Use requests.exceptions.ConnectionError (aliased in conftest)
        navigation_handler.mubi.get_secure_stream_info.side_effect = requests.exceptions.ConnectionError("Connection aborted")

        with patch('xbmcgui.Dialog') as mock_dialog:
            mock_dialog_instance = Mock()
            mock_dialog.return_value = mock_dialog_instance

            navigation_handler.play_mubi_video(film_id="net_error", web_url="https://mubi.com/net_error")

            mock_dialog_instance.notification.assert_called()
            args = mock_dialog_instance.notification.call_args[0]
            assert "Network Error" in args[1]


class TestTrailerFailureScenarios:
    """Tests for play_trailer failure modes."""

    @pytest.fixture
    def navigation_handler(self, mock_mubi, mock_session):
        mock_path = '/tmp/mock_kodi'
        os.makedirs(mock_path, exist_ok=True)
        with patch('xbmcaddon.Addon'), patch('xbmc.log'), patch('xbmcvfs.translatePath', return_value=mock_path):
            return NavigationHandler(1, "plugin://test", mock_mubi, mock_session)

    def test_play_trailer_head_request_exception(self, navigation_handler):
        """Test coherent error when trailer validation fails via Network Error."""
        trailer_url = "http://example.com/trailer.mp4"
        
        # Use requests.exceptions.ConnectionError
        with patch('requests.head', side_effect=requests.exceptions.ConnectionError("Timeout")):
            with patch('xbmcgui.Dialog') as mock_dialog, \
                 patch('xbmcplugin.setResolvedUrl') as mock_resolved:
                
                mock_dialog_instance = Mock()
                mock_dialog.return_value = mock_dialog_instance

                navigation_handler.play_trailer(trailer_url)

                mock_dialog_instance.notification.assert_called_once()
                args = mock_dialog_instance.notification.call_args[0]
                assert "Trailer unavailable" in args[1]

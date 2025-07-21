"""
Test suite for Playback module following QA guidelines.

Dependencies:
pip install pytest pytest-mock

Framework: pytest with mocker fixture for isolation
Structure: All tests follow Arrange-Act-Assert pattern
Coverage: Happy path, edge cases, and error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import base64
import json
from plugin_video_mubi.resources.lib.playback import generate_drm_license_key, generate_drm_config, play_with_inputstream_adaptive


class TestPlayback:
    """Test cases for the playback module."""

    def test_generate_drm_license_key(self):
        """Test DRM license key generation."""
        token = "test-session-token"
        user_id = "test-user-123"
        
        license_key = generate_drm_license_key(token, user_id)
        
        # Verify the license key format
        assert license_key.startswith("https://lic.drmtoday.com/license-proxy-widevine/cenc/")
        assert "dt-custom-data=" in license_key
        assert "User-Agent=" in license_key
        assert "Referer=" in license_key
        assert "Origin=" in license_key
        assert license_key.endswith("|R{SSM}|JBlicense")
        
        # Verify the custom data is properly encoded
        parts = license_key.split("|")
        assert len(parts) == 4
        
        # Extract and decode the custom data
        params_part = parts[1]
        dt_custom_data = None
        for param in params_part.split("&"):
            if param.startswith("dt-custom-data="):
                dt_custom_data = param.split("=", 1)[1]
                break

        assert dt_custom_data is not None

        # Decode and verify the custom data (URL decode first, then base64)
        from urllib.parse import unquote
        url_decoded = unquote(dt_custom_data)
        decoded_data = base64.b64decode(url_decoded).decode()
        custom_data = json.loads(decoded_data)

        assert custom_data["userId"] == user_id
        assert custom_data["sessionId"] == token
        assert custom_data["merchant"] == "mubi"

    def test_generate_drm_config(self):
        """Test DRM configuration generation for Kodi 22+."""
        token = "test-session-token"
        user_id = "test-user-123"

        drm_config = generate_drm_config(token, user_id)

        # Verify the structure
        assert "com.widevine.alpha" in drm_config
        widevine_config = drm_config["com.widevine.alpha"]
        assert "license" in widevine_config

        license_config = widevine_config["license"]
        assert license_config["server_url"] == "https://lic.drmtoday.com/license-proxy-widevine/cenc/"
        assert "dt-custom-data=" in license_config["req_headers"]
        assert license_config["unwrapper"] == "json,base64"
        assert license_config["unwrapper_params"]["path_data"] == "license"

    def test_generate_drm_license_key_empty_values(self):
        """Test DRM license key generation with empty values."""
        license_key = generate_drm_license_key("", "")
        
        # Should still generate a valid license key structure
        assert license_key.startswith("https://lic.drmtoday.com/license-proxy-widevine/cenc/")
        assert license_key.endswith("|R{SSM}|JBlicense")

    def test_generate_drm_license_key_special_characters(self):
        """Test DRM license key generation with special characters."""
        token = "token-with-special-chars!@#$%"
        user_id = "user-with-special-chars!@#$%"
        
        license_key = generate_drm_license_key(token, user_id)
        
        # Should handle special characters without errors
        assert license_key.startswith("https://lic.drmtoday.com/license-proxy-widevine/cenc/")
        assert license_key.endswith("|R{SSM}|JBlicense")

    @patch('inputstreamhelper.Helper')
    @patch('xbmcgui.ListItem')
    @patch('xbmcplugin.setResolvedUrl')
    @patch('xbmc.log')
    def test_play_with_inputstream_adaptive_mpd_success(self, mock_log, mock_set_resolved,
                                                      mock_list_item, mock_helper):
        """Test successful playback with MPD stream."""
        # Setup mocks
        mock_helper_instance = Mock()
        mock_helper_instance.check_inputstream.return_value = True
        mock_helper_instance.inputstream_addon = "inputstream.adaptive"
        mock_helper.return_value = mock_helper_instance
        
        mock_list_item_instance = Mock()
        mock_list_item.return_value = mock_list_item_instance
        
        # Test data
        handle = 123
        stream_url = "https://example.com/stream.mpd"
        license_key = "test-license-key"
        subtitles = [{"url": "https://example.com/sub1.srt"}]
        
        play_with_inputstream_adaptive(handle, stream_url, license_key, subtitles)
        
        # Verify helper was created with correct parameters
        mock_helper.assert_called_with("mpd", drm="com.widevine.alpha")
        
        # Verify ListItem was configured correctly
        mock_list_item.assert_called_with(path=stream_url)
        mock_list_item_instance.setMimeType.assert_called_with('application/dash+xml')
        mock_list_item_instance.setContentLookup.assert_called_with(False)
        mock_list_item_instance.setProperty.assert_any_call('inputstream', 'inputstream.adaptive')
        mock_list_item_instance.setProperty.assert_any_call('IsPlayable', 'true')
        mock_list_item_instance.setProperty.assert_any_call('inputstream.adaptive.license_type', 'com.widevine.alpha')
        mock_list_item_instance.setProperty.assert_any_call('inputstream.adaptive.license_key', license_key)
        
        # Verify subtitles were set
        mock_list_item_instance.setSubtitles.assert_called_with(["https://example.com/sub1.srt"])
        
        # Verify playback was initiated
        mock_set_resolved.assert_called_with(handle, True, listitem=mock_list_item_instance)
        
        mock_log.assert_called()

    @patch('inputstreamhelper.Helper')
    @patch('xbmcgui.ListItem')
    @patch('xbmcplugin.setResolvedUrl')
    @patch('xbmc.log')
    def test_play_with_inputstream_adaptive_hls_success(self, mock_log, mock_set_resolved,
                                                      mock_list_item, mock_helper):
        """Test successful playback with HLS stream."""
        # Setup mocks
        mock_helper_instance = Mock()
        mock_helper_instance.check_inputstream.return_value = True
        mock_helper_instance.inputstream_addon = "inputstream.adaptive"
        mock_helper.return_value = mock_helper_instance
        
        mock_list_item_instance = Mock()
        mock_list_item.return_value = mock_list_item_instance
        
        # Test data
        handle = 123
        stream_url = "https://example.com/stream.m3u8"
        license_key = "test-license-key"
        subtitles = []
        
        play_with_inputstream_adaptive(handle, stream_url, license_key, subtitles)
        
        # Verify helper was created with HLS protocol
        mock_helper.assert_called_with("hls", drm="com.widevine.alpha")
        
        # Verify MIME type for HLS
        mock_list_item_instance.setMimeType.assert_called_with('application/vnd.apple.mpegurl')
        
        mock_log.assert_called()

    @patch('xbmc.getInfoLabel')
    @patch('inputstreamhelper.Helper')
    @patch('xbmcgui.ListItem')
    @patch('xbmcplugin.setResolvedUrl')
    @patch('xbmc.log')
    def test_play_with_inputstream_adaptive_kodi_21_legacy_drm(self, mock_log, mock_set_resolved,
                                                             mock_list_item, mock_helper, mock_get_info):
        """Test playback with Kodi 21 uses legacy DRM configuration."""
        # Setup mocks
        mock_get_info.return_value = "21.0.0"  # Kodi 21
        mock_helper_instance = Mock()
        mock_helper_instance.check_inputstream.return_value = True
        mock_helper_instance.inputstream_addon = "inputstream.adaptive"
        mock_helper.return_value = mock_helper_instance

        mock_list_item_instance = Mock()
        mock_list_item.return_value = mock_list_item_instance

        # Test data
        handle = 123
        stream_url = "https://example.com/stream.mpd"
        license_key = "test-license-key"
        subtitles = []
        token = "test-token"
        user_id = "test-user-id"

        play_with_inputstream_adaptive(handle, stream_url, license_key, subtitles, token, user_id)

        # Verify legacy DRM properties were set
        mock_list_item_instance.setProperty.assert_any_call('inputstream.adaptive.license_type', 'com.widevine.alpha')
        mock_list_item_instance.setProperty.assert_any_call('inputstream.adaptive.license_key', license_key)

        # Verify new DRM property was NOT set
        drm_calls = [call for call in mock_list_item_instance.setProperty.call_args_list
                    if 'inputstream.adaptive.drm' in str(call)]
        assert len(drm_calls) == 0

    @patch('xbmc.getInfoLabel')
    @patch('inputstreamhelper.Helper')
    @patch('xbmcgui.ListItem')
    @patch('xbmcplugin.setResolvedUrl')
    @patch('xbmc.log')
    def test_play_with_inputstream_adaptive_kodi_22_new_drm(self, mock_log, mock_set_resolved,
                                                          mock_list_item, mock_helper, mock_get_info):
        """Test playback with Kodi 22+ uses new DRM configuration."""
        # Setup mocks
        mock_get_info.return_value = "22.0.0"  # Kodi 22
        mock_helper_instance = Mock()
        mock_helper_instance.check_inputstream.return_value = True
        mock_helper_instance.inputstream_addon = "inputstream.adaptive"
        mock_helper.return_value = mock_helper_instance

        mock_list_item_instance = Mock()
        mock_list_item.return_value = mock_list_item_instance

        # Test data
        handle = 123
        stream_url = "https://example.com/stream.mpd"
        license_key = "test-license-key"
        subtitles = []
        token = "test-token"
        user_id = "test-user-id"

        play_with_inputstream_adaptive(handle, stream_url, license_key, subtitles, token, user_id)

        # Verify new DRM property was set with JSON config
        drm_calls = [call for call in mock_list_item_instance.setProperty.call_args_list
                    if 'inputstream.adaptive.drm' in str(call)]
        assert len(drm_calls) == 1

        # Verify legacy DRM properties were NOT set
        license_type_calls = [call for call in mock_list_item_instance.setProperty.call_args_list
                             if 'inputstream.adaptive.license_type' in str(call)]
        license_key_calls = [call for call in mock_list_item_instance.setProperty.call_args_list
                            if 'inputstream.adaptive.license_key' in str(call)]
        assert len(license_type_calls) == 0
        assert len(license_key_calls) == 0

    @patch('xbmc.getInfoLabel')
    @patch('inputstreamhelper.Helper')
    @patch('xbmcgui.ListItem')
    @patch('xbmcplugin.setResolvedUrl')
    @patch('xbmc.log')
    def test_play_with_inputstream_adaptive_kodi_22_fallback_to_legacy(self, mock_log, mock_set_resolved,
                                                                     mock_list_item, mock_helper, mock_get_info):
        """Test playback with Kodi 22+ falls back to legacy when token/user_id missing."""
        # Setup mocks
        mock_get_info.return_value = "22.0.0"  # Kodi 22
        mock_helper_instance = Mock()
        mock_helper_instance.check_inputstream.return_value = True
        mock_helper_instance.inputstream_addon = "inputstream.adaptive"
        mock_helper.return_value = mock_helper_instance

        mock_list_item_instance = Mock()
        mock_list_item.return_value = mock_list_item_instance

        # Test data - no token/user_id provided
        handle = 123
        stream_url = "https://example.com/stream.mpd"
        license_key = "test-license-key"
        subtitles = []

        play_with_inputstream_adaptive(handle, stream_url, license_key, subtitles)

        # Verify fallback to legacy DRM properties
        mock_list_item_instance.setProperty.assert_any_call('inputstream.adaptive.license_type', 'com.widevine.alpha')
        mock_list_item_instance.setProperty.assert_any_call('inputstream.adaptive.license_key', license_key)

        # Verify warning was logged
        warning_calls = [call for call in mock_log.call_args_list
                        if 'falling back to legacy DRM' in str(call)]
        assert len(warning_calls) > 0

    @patch('inputstreamhelper.Helper')
    @patch('xbmc.Player')
    @patch('xbmcgui.ListItem')
    @patch('xbmc.log')
    def test_play_with_inputstream_adaptive_handle_minus_one(self, mock_log, mock_list_item,
                                                           mock_player, mock_helper):
        """Test playback with handle -1 (uses xbmc.Player)."""
        # Setup mocks
        mock_helper_instance = Mock()
        mock_helper_instance.check_inputstream.return_value = True
        mock_helper_instance.inputstream_addon = "inputstream.adaptive"
        mock_helper.return_value = mock_helper_instance
        
        mock_list_item_instance = Mock()
        mock_list_item.return_value = mock_list_item_instance
        
        mock_player_instance = Mock()
        mock_player.return_value = mock_player_instance
        
        # Test data
        handle = -1
        stream_url = "https://example.com/stream.mpd"
        license_key = "test-license-key"
        subtitles = []
        
        play_with_inputstream_adaptive(handle, stream_url, license_key, subtitles)
        
        # Verify xbmc.Player was used instead of setResolvedUrl
        mock_player_instance.play.assert_called_with(item=mock_list_item_instance)
        
        mock_log.assert_called()

    @patch('inputstreamhelper.Helper')
    @patch('xbmcgui.Dialog')
    @patch('xbmc.log')
    def test_play_with_inputstream_adaptive_unsupported_format(self, mock_log, mock_dialog, mock_helper):
        """Test playback with unsupported stream format."""
        handle = 123
        stream_url = "https://example.com/stream.avi"  # Unsupported format
        license_key = "test-license-key"
        subtitles = []
        
        mock_dialog_instance = Mock()
        mock_dialog.return_value = mock_dialog_instance
        
        play_with_inputstream_adaptive(handle, stream_url, license_key, subtitles)
        
        # Should show error notification
        mock_dialog_instance.notification.assert_called()
        notification_args = mock_dialog_instance.notification.call_args[0]
        assert "MUBI" in notification_args[0]
        assert "Error:" in notification_args[1]
        
        mock_log.assert_called()

    @patch('inputstreamhelper.Helper')
    @patch('xbmcgui.Dialog')
    @patch('xbmc.log')
    def test_play_with_inputstream_adaptive_inputstream_not_supported(self, mock_log, mock_dialog, mock_helper):
        """Test playback when InputStream Adaptive is not supported."""
        # Setup mocks
        mock_helper_instance = Mock()
        mock_helper_instance.check_inputstream.return_value = False  # Not supported
        mock_helper.return_value = mock_helper_instance
        
        mock_dialog_instance = Mock()
        mock_dialog.return_value = mock_dialog_instance
        
        handle = 123
        stream_url = "https://example.com/stream.mpd"
        license_key = "test-license-key"
        subtitles = []
        
        play_with_inputstream_adaptive(handle, stream_url, license_key, subtitles)
        
        # Should show error notification
        mock_dialog_instance.notification.assert_called()
        notification_args = mock_dialog_instance.notification.call_args[0]
        assert "MUBI" in notification_args[0]
        assert "Unable to play DRM-protected content" in notification_args[1]
        
        mock_log.assert_called()

    @patch('inputstreamhelper.Helper')
    @patch('xbmcgui.Dialog')
    @patch('xbmc.log')
    def test_play_with_inputstream_adaptive_exception(self, mock_log, mock_dialog, mock_helper):
        """Test playback handles exceptions gracefully."""
        # Setup mocks to raise exception
        mock_helper.side_effect = Exception("Helper initialization error")
        
        mock_dialog_instance = Mock()
        mock_dialog.return_value = mock_dialog_instance
        
        handle = 123
        stream_url = "https://example.com/stream.mpd"
        license_key = "test-license-key"
        subtitles = []
        
        play_with_inputstream_adaptive(handle, stream_url, license_key, subtitles)
        
        # Should show error notification
        mock_dialog_instance.notification.assert_called()
        notification_args = mock_dialog_instance.notification.call_args[0]
        assert "MUBI" in notification_args[0]
        assert "Unable to play DRM-protected content" in notification_args[1]
        
        mock_log.assert_called()

    @patch('inputstreamhelper.Helper')
    @patch('xbmcgui.ListItem')
    @patch('xbmcplugin.setResolvedUrl')
    def test_play_with_inputstream_adaptive_multiple_subtitles(self, mock_set_resolved,
                                                             mock_list_item, mock_helper):
        """Test playback with multiple subtitle tracks."""
        # Setup mocks
        mock_helper_instance = Mock()
        mock_helper_instance.check_inputstream.return_value = True
        mock_helper_instance.inputstream_addon = "inputstream.adaptive"
        mock_helper.return_value = mock_helper_instance
        
        mock_list_item_instance = Mock()
        mock_list_item.return_value = mock_list_item_instance
        
        # Test data with multiple subtitles
        handle = 123
        stream_url = "https://example.com/stream.mpd"
        license_key = "test-license-key"
        subtitles = [
            {"url": "https://example.com/sub_en.srt"},
            {"url": "https://example.com/sub_fr.srt"},
            {"url": "https://example.com/sub_es.srt"}
        ]
        
        play_with_inputstream_adaptive(handle, stream_url, license_key, subtitles)
        
        # Verify all subtitle URLs were set
        expected_subtitle_urls = [
            "https://example.com/sub_en.srt",
            "https://example.com/sub_fr.srt",
            "https://example.com/sub_es.srt"
        ]
        mock_list_item_instance.setSubtitles.assert_called_with(expected_subtitle_urls)

    @patch('inputstreamhelper.Helper')
    @patch('xbmcgui.ListItem')
    @patch('xbmcplugin.setResolvedUrl')
    def test_play_with_inputstream_adaptive_headers_configuration(self, mock_set_resolved,
                                                                mock_list_item, mock_helper):
        """Test that stream headers are configured correctly."""
        # Setup mocks
        mock_helper_instance = Mock()
        mock_helper_instance.check_inputstream.return_value = True
        mock_helper_instance.inputstream_addon = "inputstream.adaptive"
        mock_helper.return_value = mock_helper_instance
        
        mock_list_item_instance = Mock()
        mock_list_item.return_value = mock_list_item_instance
        
        handle = 123
        stream_url = "https://example.com/stream.mpd"
        license_key = "test-license-key"
        subtitles = []
        
        play_with_inputstream_adaptive(handle, stream_url, license_key, subtitles)
        
        # Verify headers were set
        header_calls = [call for call in mock_list_item_instance.setProperty.call_args_list
                       if 'headers' in str(call)]
        
        assert len(header_calls) >= 2  # Should set both stream_headers and manifest_headers
        
        # Check that headers contain expected values
        for call in header_calls:
            if 'stream_headers' in str(call) or 'manifest_headers' in str(call):
                headers_value = call[0][1]
                assert 'User-Agent=' in headers_value
                assert 'Referer=' in headers_value
                assert 'Origin=' in headers_value

    def test_drm_license_key_url_encoding(self):
        """Test that DRM license key properly encodes URL parameters."""
        token = "token with spaces & special chars"
        user_id = "user@example.com"
        
        license_key = generate_drm_license_key(token, user_id)
        
        # The license key should be properly URL encoded
        assert " " not in license_key.split("|")[1]  # Headers part should not contain raw spaces
        assert "&" in license_key  # Should contain URL-encoded parameters

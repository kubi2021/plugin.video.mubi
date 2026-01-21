import pytest
from unittest.mock import Mock, patch
from plugin_video_mubi.resources.lib.playback import play_with_inputstream_adaptive
import xbmcgui

@patch('inputstreamhelper.Helper')
@patch('xbmcgui.ListItem')
@patch('xbmcplugin.setResolvedUrl')
@patch('xbmc.log')
def test_play_with_query_params(mock_log, mock_set_resolved, mock_list_item, mock_helper):
    """
    Test that play_with_inputstream_adaptive can handle URLs with query parameters.
    This test reproduces the issue where URLs ending with '?...' fail the endswith('.mpd') check.
    """
    # Setup mocks
    mock_helper_instance = Mock()
    mock_helper_instance.check_inputstream.return_value = True
    mock_helper_instance.inputstream_addon = "inputstream.adaptive"
    mock_helper.return_value = mock_helper_instance
    
    mock_list_item_instance = Mock()
    mock_list_item.return_value = mock_list_item_instance
    
    # Test data with query params
    handle = 123
    stream_url = "https://example.com/stream.mpd?allowed_languages=eng,fra"
    license_key = "test-license-key"
    subtitles = []
    
    # This should succeed if the fix is implemented, but currently it will raise ValueError
    # or be caught and logged as error depending on implementation
    
    play_with_inputstream_adaptive(handle, stream_url, license_key, subtitles)
    
    # Verify helper was created with correct parameters (mpd)
    # If the code fails to detect mpd, it propagates ValueError or catches it.
    # In the current implementation, it catches ValueError and logs it, checks notification.
    # But wait, looking at playback.py:
    # except ValueError as ve:
    #     xbmc.log(f"Error with stream format: {ve}", xbmc.LOGERROR)
    
    # So the function returns performing no playback.
    # We can assert that mock_helper was NOT called with "mpd" if it failed,
    # OR assert that it WAS called if it succeeded.
    
    mock_helper.assert_called_with("mpd", drm="com.widevine.alpha")

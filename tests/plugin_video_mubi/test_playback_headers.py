import pytest
from unittest.mock import Mock, patch, MagicMock
from plugin_video_mubi.resources.lib.playback import play_with_inputstream_adaptive

@patch('plugin_video_mubi.resources.lib.playback.MPDPatcher')
@patch('plugin_video_mubi.resources.lib.playback.LocalServer')
@patch('inputstreamhelper.Helper')
@patch('xbmcgui.ListItem')
@patch('xbmcplugin.setResolvedUrl')
@patch('xbmc.log')
@patch('xbmc.getInfoLabel')
def test_headers_passed_with_mpd_patching(mock_getInfoLabel, mock_log, mock_setResolvedUrl, mock_ListItem, mock_Helper, mock_LocalServer, mock_MPDPatcher):
    """
    Verify that stream_headers are passed to inputstream.adaptive even when MPD patching is active (LocalServer used).
    This prevents the regression where headers were cleared for local playback.
    """
    # Setup Mocks
    mock_helper_instance = Mock()
    mock_helper_instance.check_inputstream.return_value = True
    mock_Helper.return_value = mock_helper_instance

    mock_list_item_instance = MagicMock()
    mock_ListItem.return_value = mock_list_item_instance

    # Mock MPD Patcher to return a patched path, triggering the LocalServer logic
    mock_patcher_instance = Mock()
    mock_patcher_instance.patch.return_value = "special://temp/patched.mpd"
    mock_MPDPatcher.return_value = mock_patcher_instance

    # Mock Local Server
    mock_server_instance = Mock()
    mock_server_instance.get_url.return_value = "http://127.0.0.1:12345/patched.mpd"
    mock_LocalServer.get_instance.return_value = mock_server_instance

    # Mock Kodi Version
    mock_getInfoLabel.return_value = "20.0"

    # Inputs
    handle = 1
    stream_url = "https://mubi.com/film.mpd"
    license_key = "key"
    subtitles = []

    # Execute
    play_with_inputstream_adaptive(handle, stream_url, license_key, subtitles)

    # Verification
    # 1. Verify LocalServer was used (proven by headers check + logic flow)
    mock_server_instance.get_url.assert_called()
    
    # 2. Verify Headers were NOT empty
    properties_set = {}
    for call in mock_list_item_instance.setProperty.call_args_list:
        key, value = call[0]
        properties_set[key] = value

    assert 'inputstream.adaptive.stream_headers' in properties_set, "stream_headers property was missing"
    headers_val = properties_set['inputstream.adaptive.stream_headers']
    
    assert "User-Agent=" in headers_val, "User-Agent header missing"
    assert "Referer=" in headers_val, "Referer header missing"
    assert headers_val != "", "Headers string should not be empty"

    # Verify manifest headers as well
    assert 'inputstream.adaptive.manifest_headers' in properties_set
    assert properties_set['inputstream.adaptive.manifest_headers'] == headers_val

@patch('plugin_video_mubi.resources.lib.playback.MPDPatcher')
@patch('inputstreamhelper.Helper')
@patch('xbmcgui.ListItem')
@patch('xbmcplugin.setResolvedUrl')
@patch('xbmc.log')
@patch('xbmc.getInfoLabel')
def test_headers_passed_hls_no_patching(mock_getInfoLabel, mock_log, mock_setResolvedUrl, mock_ListItem, mock_Helper, mock_MPDPatcher):
    """
    Verify that headers are passed correctly for HLS streams (which don't use patching).
    """
    mock_helper_instance = Mock()
    mock_helper_instance.check_inputstream.return_value = True
    mock_Helper.return_value = mock_helper_instance

    mock_list_item_instance = MagicMock()
    mock_ListItem.return_value = mock_list_item_instance

    mock_getInfoLabel.return_value = "20.0"

    handle = 1
    stream_url = "https://mubi.com/film.m3u8"
    license_key = "key"
    subtitles = []

    play_with_inputstream_adaptive(handle, stream_url, license_key, subtitles)

    mock_MPDPatcher.assert_not_called()

    properties_set = {}
    for call in mock_list_item_instance.setProperty.call_args_list:
        key, value = call[0]
        properties_set[key] = value

    assert 'inputstream.adaptive.stream_headers' in properties_set
    headers_val = properties_set['inputstream.adaptive.stream_headers']
    assert "User-Agent=" in headers_val
    assert headers_val != ""

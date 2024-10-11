import xbmcgui
import xbmcplugin
import inputstreamhelper

def play_with_inputstream_adaptive(handle, stream_url: str, license_key: str):
    """
    Plays a video using InputStream Adaptive (ISA) with DRM protection.

    :param handle: Kodi plugin handle
    :param stream_url: The secure stream URL
    :param license_key: DRM license key for Widevine content
    """
    try:
        protocol = "mpd"  # Assuming the protocol is MPEG-DASH
        drm_type = "com.widevine.alpha"  # Widevine DRM

        is_helper = inputstreamhelper.Helper(protocol, drm=drm_type)

        if is_helper.check_inputstream():
            play_item = xbmcgui.ListItem(path=stream_url)
            play_item.setMimeType('application/xml+dash')
            play_item.setContentLookup(False)
            play_item.setProperty('inputstream', is_helper.inputstream_addon)
            play_item.setProperty("IsPlayable", "true")
            play_item.setProperty('inputstream.adaptive.manifest_type', protocol)
            play_item.setProperty('inputstream.adaptive.license_type', drm_type)
            play_item.setProperty('inputstream.adaptive.license_key', license_key)

            xbmcplugin.setResolvedUrl(handle, True, listitem=play_item)
        else:
            raise Exception("InputStream Adaptive is not supported or enabled")

    except Exception as e:
        xbmc.log(f"Error initializing InputStream Adaptive: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("MUBI", "Error: Unable to play DRM-protected content.", xbmcgui.NOTIFICATION_ERROR)

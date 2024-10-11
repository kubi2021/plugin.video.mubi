import xbmcgui
import xbmcplugin
import inputstreamhelper
import base64
import json
from urllib.parse import urlencode
import xbmc

def generate_drm_license_key(token, user_id):
    """
    Generates a Widevine DRM license key URL with the required headers and session info.

    :param token: The session token for the Mubi user.
    :param user_id: The Mubi user ID.
    :return: A formatted DRM license key URL.
    """
    drm_license_url = "https://lic.drmtoday.com/license-proxy-widevine/cenc/"
    dcd = json.dumps({"userId": user_id, "sessionId": token, "merchant": "mubi"})
    dcd_enc = base64.b64encode(dcd.encode()).decode()

    drm_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
        'dt-custom-data': dcd_enc,
        'Referer': 'https://mubi.com/',
        'Origin': 'https://mubi.com',
        'Content-Type': ''
    }

    # Build the full DRM license key URL using the headers
    license_key = f"{drm_license_url}|{urlencode(drm_headers)}|R{{SSM}}|JBlicense"
    return license_key


def play_with_inputstream_adaptive(handle, stream_url: str, license_key: str):
    """
    Plays a video using InputStream Adaptive (ISA) with DRM protection.

    :param handle: Kodi plugin handle
    :param stream_url: The secure stream URL
    :param license_key: DRM license key for Widevine content
    """
    try:
        # Determine the streaming protocol from the URL
        if stream_url.endswith('.mpd'):
            protocol = "mpd"  # MPEG-DASH
            mime_type = 'application/dash+xml'
        elif stream_url.endswith('.m3u8'):
            protocol = "hls"  # HLS
            mime_type = 'application/vnd.apple.mpegurl'
        else:
            raise ValueError(f"Unsupported stream format in URL: {stream_url}")

        drm_type = "com.widevine.alpha"  # Widevine DRM

        # Log the protocol and stream details for debugging
        xbmc.log(f"Selected protocol: {protocol}, MIME type: {mime_type}, Stream URL: {stream_url}", xbmc.LOGDEBUG)

        is_helper = inputstreamhelper.Helper(protocol, drm=drm_type)

        # Set the headers that will be used for the license and manifest
        stream_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
            'Referer': 'https://mubi.com/',
            'Origin': 'https://mubi.com'
        }

        headers_str = "&".join([f"{k}={v}" for k, v in stream_headers.items()])

        if is_helper.check_inputstream():
            play_item = xbmcgui.ListItem(path=stream_url)
            play_item.setMimeType(mime_type)
            play_item.setContentLookup(False)
            play_item.setProperty('inputstream', is_helper.inputstream_addon)
            play_item.setProperty("IsPlayable", "true")
            play_item.setProperty('inputstream.adaptive.license_type', drm_type)
            play_item.setProperty('inputstream.adaptive.license_key', license_key)
            play_item.setProperty('inputstream.adaptive.stream_headers', headers_str)
            play_item.setProperty('inputstream.adaptive.manifest_headers', headers_str)

            # Log the license key and playback initialization
            xbmc.log(f"Setting DRM license key: {license_key}", xbmc.LOGDEBUG)

            # Resolve and start playback
            xbmcplugin.setResolvedUrl(handle, True, listitem=play_item)
        else:
            raise Exception("InputStream Adaptive is not supported or enabled")

    except ValueError as ve:
        xbmc.log(f"Error with stream format: {ve}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("MUBI", f"Error: {ve}", xbmcgui.NOTIFICATION_ERROR)
    except Exception as e:
        xbmc.log(f"Error initializing InputStream Adaptive: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("MUBI", "Error: Unable to play DRM-protected content.", xbmcgui.NOTIFICATION_ERROR)

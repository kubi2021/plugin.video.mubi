import xbmcgui
import xbmcplugin
import inputstreamhelper
import base64
import json
from urllib.parse import urlencode
import xbmc
import pathlib
from .mpd_patcher import MPDPatcher
from .local_server import LocalServer

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


def generate_drm_config(token, user_id):
    """
    Generates a DRM configuration object for Kodi 22+ (ISA v22.1.5+).

    :param token: The session token for the Mubi user.
    :param user_id: The Mubi user ID.
    :return: A dictionary containing the DRM configuration for the new format.
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

    drm_config = {
        "com.widevine.alpha": {
            "license": {
                "server_url": drm_license_url,
                "req_headers": urlencode(drm_headers),
                "unwrapper": "json,base64",
                "unwrapper_params": {"path_data": "license"},
            }
        }
    }

    return drm_config


def play_with_inputstream_adaptive(handle, stream_url: str, license_key: str, subtitles: list,
                                   token: str = None, user_id: str = None):
    """
    Plays a video using InputStream Adaptive (ISA) with DRM protection and subtitles.
    Supports both legacy (Kodi < 22) and new (Kodi >= 22) DRM configuration formats.

    :param handle: Kodi plugin handle
    :param stream_url: The secure stream URL
    :param license_key: DRM license key for Widevine content (legacy format)
    :param subtitles: List of subtitle tracks
    :param token: Session token for new DRM format (optional)
    :param user_id: User ID for new DRM format (optional)
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
        xbmc.log(f"Selected protocol: {protocol}, MIME type: {mime_type}, Stream URL: {stream_url}",
                 xbmc.LOGDEBUG)

        is_helper = inputstreamhelper.Helper(protocol, drm=drm_type)

        # Set the headers that will be used for the license and manifest
        stream_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
            'Referer': 'https://mubi.com/',
            'Origin': 'https://mubi.com'
        }

        headers_str = "&".join([f"{k}={v}" for k, v in stream_headers.items()])

        xbmc.log(f"MUBI Playback: Protocol={protocol}, URL={stream_url}", xbmc.LOGINFO)

        # MPD Patching logic for Kodi audio channel detection
        if protocol == "mpd":
            try:
                patcher = MPDPatcher()
                # We need to pass headers for the download
                patched_path = patcher.patch(stream_url, stream_headers)
                
                if patched_path:
                    # Use Local HTTP Server to serve the patched manifest
                    # This bypasses inputstream.adaptive's issues with local files on some platforms
                    server = LocalServer.get_instance()
                    local_url = server.get_url(patched_path)
                    
                    xbmc.log(f"Using patched manifest via local server: {local_url} (file: {patched_path})", xbmc.LOGINFO)
                    stream_url = local_url
                    
                    # For the manifest request (localhost), we don't want headers
                    headers_str = "" 
                    # Note: Segments will still be fetched from remote (absolute BaseURL), 
                    # avoiding the need for headers here usually working because of cookie/session persistence or URL tokens?
                    # Actually, we might need headers for segments if they are not in the URL.
                    # But we can't easily pass headers for segments but NOT for manifest in ISA current config if using 'stream_headers'.
                    # However, Mubi usually uses URL-based tokens (cf generate_drm_license_key) or cookies.
                    # Wait, stream_headers in ISA applies to EVERYTHING. 
                    # If we set it to empty, segments might fail if they need headers.
                    # BUT, if we keep it, ISA uses it for the manifest request to localhost, failing because of Host header mismatch or similar?
                    # Actually, simple python http server ignores headers mostly.
                    # Let's try EMPTY headers first. If segments fail, we have a different problem.
            except Exception as e:
                xbmc.log(f"MPD Patching failed, falling back to original URL: {e}", xbmc.LOGWARNING)

        if is_helper.check_inputstream():
            play_item = xbmcgui.ListItem(path=stream_url)
            play_item.setMimeType(mime_type)
            play_item.setContentLookup(False)
            play_item.setProperty('inputstream', is_helper.inputstream_addon)
            play_item.setProperty("IsPlayable", "true")
            play_item.setProperty('inputstream.adaptive.stream_headers', headers_str)
            play_item.setProperty('inputstream.adaptive.manifest_headers', headers_str)
            play_item.setProperty('inputstream.adaptive.manifest_type', protocol)

            # Kodi version detection for DRM configuration
            kodi_version = xbmc.getInfoLabel('System.BuildVersion')
            kodi_major_version = int(kodi_version.split('.')[0])

            xbmc.log(f"Detected Kodi version: {kodi_version}, major version: {kodi_major_version}",
                     xbmc.LOGDEBUG)

            if kodi_major_version < 22:
                # Legacy DRM configuration for Kodi < 22
                xbmc.log("Using legacy DRM configuration for Kodi < 22", xbmc.LOGDEBUG)
                play_item.setProperty('inputstream.adaptive.license_type', drm_type)
                play_item.setProperty('inputstream.adaptive.license_key', license_key)
            else:
                # New DRM configuration for Kodi >= 22 (ISA v22.1.5+)
                xbmc.log("Using new DRM configuration for Kodi >= 22", xbmc.LOGDEBUG)
                if token and user_id:
                    drm_config = generate_drm_config(token, user_id)
                    play_item.setProperty('inputstream.adaptive.drm', json.dumps(drm_config))
                else:
                    # Fallback to legacy if token/user_id not provided
                    xbmc.log("Token/user_id not provided, falling back to legacy DRM", xbmc.LOGWARNING)
                    play_item.setProperty('inputstream.adaptive.license_type', drm_type)
                    play_item.setProperty('inputstream.adaptive.license_key', license_key)

            # Add subtitles to the ListItem
            subtitle_urls = [subtitle['url'] for subtitle in subtitles]
            play_item.setSubtitles(subtitle_urls)
            xbmc.log(f"Subtitles added: {subtitle_urls}", xbmc.LOGDEBUG)

            # Start playback
            if handle != -1:
                # When handle is valid, use setResolvedUrl
                xbmcplugin.setResolvedUrl(handle, True, listitem=play_item)
            else:
                # When handle is -1, use xbmc.Player().play()
                xbmc.log("Handle is -1, using xbmc.Player().play()", xbmc.LOGDEBUG)
                xbmc.Player().play(item=play_item)

        else:
            raise Exception("InputStream Adaptive is not supported or enabled")

    except ValueError as ve:
        xbmc.log(f"Error with stream format: {ve}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("MUBI", f"Error: {ve}", xbmcgui.NOTIFICATION_ERROR)
    except Exception as e:
        xbmc.log(f"Error initializing InputStream Adaptive: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("MUBI", "Error: Unable to play DRM-protected content.", xbmcgui.NOTIFICATION_ERROR)


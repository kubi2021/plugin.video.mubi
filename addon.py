from __future__ import absolute_import, division, unicode_literals
import sys
from resources.lib.mubi import Mubi
import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmc
from urllib.parse import urlencode, parse_qsl

# In order to load the movie in the external browser
import webbrowser

# In order to manipulate files and folders
import os


# DRM = 'widevine'
# PROTOCOL = 'mpd'

# DRM Licenses are issued by: https://lic.drmtoday.com/license-proxy-widevine/cenc/
# The header data has to contain the field dt-custom-data
# This field includes a base64-encoded string with the following data: {"userId":[userId],"sessionId":"[sessionToken]","merchant":"mubi"}
# The user id and session token can be obtained with the login
LICENSE_URL = 'https://downloads.castlabs.com/r/register/'

## update header according to mobile app packets
LICENSE_URL_HEADERS = (
    # 'User-Agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.123 Safari/537.36&'
    'CL-SDK-VERSION=4.2.34&'
    'CL-PLAYBACK-TYPE=live&'
    'CL-CONTENT-TYPE=dash&'
    'CL-PLUGINS=plugin_downloader&'
    'CL-DRM=drmtoday&'
    'CL-DRM-CDM=wv&'
    'CL-DRM-SEC-LEVEL=L3&'
    'CL-DRM-OFFLINE=false&'
    'Accept-Encoding=gzip&'
    'Connection=keep-alive&'
    'Host=downloads.castlabs.com&'
    'CL-DEVICE-ID=6af36914d0ca3a53&'
    'CL-DEVICE-BRAND=unknown&'
    'CL-DEVICE-MODEL=Android SDK built for x86&'
    'CL-OS-FAMILY=Android&'
    'CL-OS-VERSION=23&'
    'User-Agent=Dalvik/2.1.0 (Linux; U; Android 6.0; Android SDK built for x86 Build/MASTER)'
    # 'Content-Type=application/json;charset=utf-8'
)

# LICENSE_URL = 'https://lic.drmtoday.com/license-proxy-widevine/cenc/'

## update header according to mobile app packets
# LICENSE_URL_HEADERS = (
#     # 'User-Agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.123 Safari/537.36&'
#     'Accept=*/*&'
#     'Accept-Encoding=gzip, deflate, br&'
#     'Accept-Language=en-US,en;q=0.9,fr;q=0.8,de;q=0.7,es;q=0.6,pt;q=0.5&'
#     'Cache-Control=no-cache&'
#     'Connection=keep-alive&'
#     'Content-Length=4023&'
#     'DNT=1&'
#     'Host=lic.drmtoday.com&'
#     'Origin=https://mubi.com&'
#     'Pragma=no-cache&'
#     'Referer=https://mubi.com/&'
#     'sec-ch-ua= "Chromium";v="94", "Google Chrome";v="94", ";Not A Brand";v="99"&'
#     'sec-ch-ua-mobile=?0&'
#     'sec-ch-ua-platform="macOS"&'
#     'Sec-Fetch-Dest=empty&'
#     'Sec-Fetch-Mode=cors&'
#     'Sec-Fetch-Site=cross-site&'
#     'User-Agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36'
#     # 'Content-Type=application/json;charset=utf-8'
# )

#plugin = (PLUGIN_NAME, PLUGIN_ID, __file__)
plugin = xbmcaddon.Addon()

# xbmc.translatePath is deprecated and might be removed in future kodi versions. Please use xbmcvfs.translatePath instead.
plugin_userdata_path = xbmc.translatePath( plugin.getAddonInfo('profile') )

if not plugin.getSetting("username") or not plugin.getSetting("password"):
    plugin.openSettings()

mubi = Mubi(plugin.getSetting("username"), plugin.getSetting("password"))

# Get the plugin url in plugin:// notation.
_URL = sys.argv[0]
# Get the plugin handle as an integer number.
_HANDLE = int(sys.argv[1])

# Static categories
# VIDEOS = {'Film of the day': []}


def get_url(**kwargs):
    """
    Create a URL for calling the plugin recursively from the given set of keyword arguments.

    :param kwargs: "argument=value" pairs
    :return: plugin call URL
    :rtype: str
    """
    return '{}?{}'.format(_URL, urlencode(kwargs))

# def get_categories():
#     """
#     Get the list of video categories.
#
#     Here you can insert some parsing code that retrieves
#     the list of video categories (e.g. 'Movies', 'TV-shows', 'Documentaries' etc.)
#     from some site or API.
#
#     .. note:: Consider using `generator functions <https://wiki.python.org/moin/Generators>`_
#         instead of returning lists.
#
#     :return: The list of video categories
#     :rtype: types.GeneratorType
#     """
#     return VIDEOS.keys()


# def get_videos(category):
#     """
#     Get the list of videofiles/streams.
#
#     Here you can insert some parsing code that retrieves
#     the list of video streams in the given category from some site or API.
#
#     .. note:: Consider using `generators functions <https://wiki.python.org/moin/Generators>`_
#         instead of returning lists.
#
#     :param category: Category name
#     :type category: str
#     :return: the list of videos in the category
#     :rtype: list
#     """
#     return VIDEOS[category]


def list_categories():
    """
    Create the list of video categories in the Kodi interface.
    """
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(_HANDLE, 'My Video Collection')
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(_HANDLE, 'videos')
    # Get video categories
    # categories = get_categories()
    categories = mubi.get_film_groups()
    # Iterate through categories
    for item in categories:
        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=item['title'])

        list_item.setInfo('video', {'title': item['title'],
                                    'mediatype': 'video'})

        # Create a URL for a plugin recursive call.
        # Example: plugin://plugin.video.example/?action=listing&category=Animals
        url = get_url(action='listing', category=item['id'])

        # is_folder = True means that this item opens a sub-list of lower level items.
        is_folder = True
        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_HANDLE)


def list_videos(category):
    """
    Create the list of playable videos in the Kodi interface.

    :param category: Category name
    :type category: str
    """
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    # xbmcplugin.setPluginCategory(_HANDLE, category['title'])
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(_HANDLE, 'videos')
    # Get the list of videos in the category.

    films = mubi.now_showing(category)

    # Iterate through videos.
    for film in films:
        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=film.title)

        # Set additional info for the list item.
        # 'mediatype' is needed for skin to display info for this ListItem correctly.
        # fill the info according to the doc: https://codedocs.xyz/AlwinEsch/kodi/group__python__xbmcgui__listitem.html#ga0b71166869bda87ad744942888fb5f14
        list_item.setInfo('video', {'title': film.title,
                                    'originaltitle': film.metadata.originaltitle,
                                    'genre': film.metadata.genre,
                                    # 'country': str(film.metadata.country),
                                    # 'year': film.metadata.year,
                                    # 'rating': film.metadata.rating,
                                    # 'director': str(film.metadata.director),
                                    # 'plot': film.metadata.plot,
                                    # 'plotoutline': film.metadata.plotoutline,
                                    # 'duration': film.metadata.duration,
                                    # 'trailer': film.metadata.trailer,
                                    # 'dateadded': film.metadata.dateadded,
                                    'mediatype': 'video'})

        # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list item.
        # Here we use the same image for all items for simplicity's sake.
        # In a real-life plugin you need to set each image accordingly.
        list_item.setArt({
            'thumb': film.metadata.image,
            'poster': film.metadata.image,
            'banner': film.metadata.image,
            'fanart': film.metadata.image,
            'landscape': film.metadata.image,
            'icon': film.metadata.image
            })

        # Set 'IsPlayable' property to 'true'.
        # This is mandatory for playable items!
        # list_item.setProperty('IsPlayable', 'true')

        # Create a URL for a plugin recursive call.
        # url = get_url(action='play', identifier=film.mubi_id)
        url = get_url(action='play_ext', web_url=film.web_url)

        # Add the list item to a virtual Kodi folder.
        # is_folder = False means that this item won't open any sub-list.
        is_folder = False

        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)

        ## Create the strm files in special://userdata/addon_data/plugin.video.mubi
        file_name = film.title + ' (' + str(film.metadata.year) + ')'
        path = plugin_userdata_path + '/' + file_name
        try:
            os.mkdir(path)
        except OSError as error:
            xbmc.log("Error while creating the library: %s" % error, 2)

        f = open(path+'/'+file_name+'.strm', "w")
        f.write(url)
        f.close()

    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_NONE)

    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_HANDLE)


# Function to play video within Mubi. Currently not working because of DRMs
# def play_video(identifier):
#     """
#     Play a video by the provided path.
#
#     :param path: Fully-qualified video URL
#     :type path: str
#     """
#     # Create a playable item with a path to play.
#     # play_item = xbmcgui.ListItem(path=path)
#     # Pass the item to the Kodi player.
#     # xbmcplugin.setResolvedUrl(_HANDLE, True, listitem=play_item)
#
#     mubi_resolved_info = mubi.get_play_url(identifier)
#     mubi_film = xbmcgui.ListItem(path=mubi_resolved_info['url'])
#
#     if mubi_resolved_info['is_mpd']:
#
#         mubi_film.setProperty('inputstream', 'inputstream.adaptive')
#         mubi_film.setProperty('inputstream.adaptive.manifest_type', 'mpd')
#
#         if mubi_resolved_info['drm_header'] is not None:
#             xbmc.log('DRM Header: %s' %mubi_resolved_info['drm_header'].decode(), 2)
#             xbmc.log('LICENSE_URL_HEADERS: %s' % LICENSE_URL_HEADERS, 2)
#             mubi_film.setProperty('inputstream.adaptive.license_type', "com.widevine.alpha")
#             mubi_film.setProperty('inputstream.adaptive.license_key', LICENSE_URL + '|' + LICENSE_URL_HEADERS + '&CL-KEY=' + mubi_resolved_info['drm_header'].decode() + '&CL-USER-ID='+ str(mubi_resolved_info['userId']) +'&CL-SESSION-ID='+ str(mubi_resolved_info['token']) + '&CL-ASSET-ID='+ str(mubi_resolved_info['drm_asset_id']) +'|R{SSM}|JBlicense')
#             # mubi_film.setProperty('inputstream.adaptive.license_key', LICENSE_URL + '|' + LICENSE_URL_HEADERS + '&dt-custom-data=' + mubi_resolved_info['drm_header'].decode() + '|R{SSM}|JBlicense')
#             # mubi_film.setProperty('inputstream.adaptive.license_key', LICENSE_URL + '|' + LICENSE_URL_HEADERS + '&dt-custom-data=' + mubi_resolved_info['drm_header'] + '|R{SSM}|JBlicense')
#             mubi_film.setMimeType('application/dash+xml')
#             mubi_film.setContentLookup(False)
#     return xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, listitem=mubi_film)


def play_video_ext(web_url):
    """
    Play a video by the provided path.

    :param path: Fully-qualified video URL
    :type path: str
    """
    # Create a playable item with a path to play.
    # play_item = xbmcgui.ListItem(path=path)
    # Pass the item to the Kodi player.
    # xbmcplugin.setResolvedUrl(_HANDLE, True, listitem=play_item)

    # mubi_resolved_info = mubi.get_play_url(identifier)
    # mubi_film = xbmcgui.ListItem(path=mubi_resolved_info['url'])

    webbrowser.open_new_tab(web_url)



def router(paramstring):
    """
    Router function that calls other functions
    depending on the provided paramstring

    :param paramstring: URL encoded plugin paramstring
    :type paramstring: str
    """
    # Parse a URL-encoded paramstring to the dictionary of
    # {<parameter>: <value>} elements
    params = dict(parse_qsl(paramstring))
    # Check the parameters passed to the plugin
    if params:
        if params['action'] == 'listing':
            # Display the list of videos in a provided category.
            list_videos(params['category'])
        elif params['action'] == 'play':
            # Play a video from a provided URL.
            play_video(params['identifier'])
        elif params['action'] == 'play_ext':
            # Play a video from a provided URL.
            play_video_ext(params['web_url'])
        else:
            # If the provided paramstring does not contain a supported action
            # we raise an exception. This helps to catch coding errors,
            # e.g. typos in action names.
            raise ValueError('Invalid paramstring: {}!'.format(paramstring))
    else:
        # If the plugin is called from Kodi UI without any parameters,
        # display the list of video categories
        list_categories()


if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])
